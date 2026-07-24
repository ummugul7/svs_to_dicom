# The standard Python os module, along with shutil, is exactly what interacts with your computer's hard drive or SSD to manage these files.
import os
import shutil
import uuid
import zipfile  #DICOM dosyasını zipe getirmek için
import openslide
from fastapi import UploadFile
from sqlalchemy.exc import IntegrityError
from wsidicomizer import WsiDicomizer
import hashlib
from sqlalchemy.orm import Session
from src.model import Slide
from dotenv import load_dotenv
import concurrent.futures
import logging

DATA_FOLDER = "data"
load_dotenv()
MAX_THREADS = int(os.getenv("MAX_THREADS"))
dicom_executor = concurrent.futures.ThreadPoolExecutor(max_workers=MAX_THREADS)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename= os.getenv("LOG_FILE_NAME"),
    filemode='a'
)

def slide_folder(slide_id: str) -> str:
    return os.path.join(DATA_FOLDER, slide_id)

def svs_path_get(slide_id: str) -> str:
    folder = slide_folder(slide_id)
    if not os.path.isdir(folder):
        raise FileNotFoundError(f"'{slide_id}' slide not found.")
    for file in os.listdir(folder):
        if file.endswith(".svs"):
            return os.path.join(folder, file)


def save_uploaded_file(file_name: str, file_object) -> str:
    slide_id = uuid.uuid4().hex
    folder = slide_folder(slide_id)
    os.makedirs(folder, exist_ok=True) #localde kalsör oluşturmak için

    svs_path = os.path.join(folder, file_name)
    logging.info(f"[Background] Saving '{file_name}' to '{svs_path}'")
    with open(svs_path, "wb") as buffer:
        shutil.copyfileobj(file_object, buffer)
    return slide_id


#tüm metadataları listeler
def get_properties(slide_id: str) -> dict:
    svs_path = svs_path_get(slide_id)
    slide = openslide.OpenSlide(svs_path)
    try:
        return dict(slide.properties)
    finally:
        slide.close()

def create_thumbnail(slide_id: str, size=(500, 500)) -> str:
    svs_path = svs_path_get(slide_id)
    folder = slide_folder(slide_id)
    slide = openslide.OpenSlide(svs_path)
    try:
        thumbnail = slide.get_thumbnail(size)
        thumbnail_path = os.path.join(folder, "thumbnail.png")
        thumbnail.save(thumbnail_path)
        return thumbnail_path
    finally:
        slide.close()

def dicom_and_zip_process(slide_id: str):
    folder = slide_folder(slide_id)
    try:
        svs_path = svs_path_get(slide_id)
        output_folder = os.path.join(folder, "dicom_output")
        zip_path = os.path.join(folder, "dicom_output.zip")
        create_thumbnail(slide_id, size=(500, 500))

        if os.path.exists(output_folder):
            shutil.rmtree(output_folder)
        if os.path.exists(zip_path):
            os.remove(zip_path)

        WsiDicomizer.convert(filepath=svs_path, output_path=output_folder)

        if not os.path.exists(output_folder) or len(os.listdir(output_folder)) == 0:
            raise Exception("Dönüşüm hatası: DICOM dosyaları oluşturulamadı.")

        # ZIP İşlemi bunu kullanıcya web üzeirnden indirilebilr bir şekilde iletmek için yaptm
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(output_folder):
                for file in files:
                    file_path = os.path.join(root, file)
                    zipf.write(file_path, os.path.relpath(file_path, output_folder))
                    
        # ZIP yaptıktan sonra fazlalık DICOM klasörünü sil
        if os.path.exists(output_folder):
            shutil.rmtree(output_folder)

        from src.database import SessionLocal
        db = SessionLocal()
        try:
            add_slide(slide_id, db)
            #dbye veri kaydedildikten ve dönüşüm işelmi bittikten sonra svs dosyası silindi
            if os.path.exists(svs_path):
                os.remove(svs_path)
                logging.info(f"[Background] Original SVS file deleted to save space: '{slide_id}'.")
                
            logging.info(f"[Background] Processing complete and saved to DB for '{slide_id}'. ZIP ready.")
        except IntegrityError:
            db.rollback()
            logging.warning(f"[Background] Integrity error saving '{slide_id}' to DB. Concurrent upload?")
        finally:
            db.close()

    except Exception as e:
        logging.error(f"[Background] Error processing '{slide_id}': {str(e)}")



def zip_path_get(slide_id: str) -> str:
    return os.path.join(slide_folder(slide_id), "dicom_output.zip")

def all_folder_get() -> str:
    # Eğer data klasörü hiç oluşmamışsa (daha önce dosya yüklenmediyse) oluştur
    if not os.path.exists(DATA_FOLDER):
        os.makedirs(DATA_FOLDER, exist_ok=True)

    global_zip_path = os.path.join(DATA_FOLDER, "all_dicom_outputs.zip")
    
    # Mevcut tüm ID klasörlerini gez ve içlerindeki zip dosyalarını topla
    with zipfile.ZipFile(global_zip_path, "w", zipfile.ZIP_DEFLATED) as global_zip:
        for slide_id in os.listdir(DATA_FOLDER):
            folder_path = os.path.join(DATA_FOLDER, slide_id)
            if os.path.isdir(folder_path):
                slide_zip = os.path.join(folder_path, "dicom_output.zip")
                if os.path.exists(slide_zip):
                    global_zip.write(slide_zip, f"{slide_id}_dicom_output.zip")
                    
    return global_zip_path

# bu method her dosyaya ait hash değeri döndürüyor
def generate_metadata_hash(slide_id: str) -> str:
    svs_path = svs_path_get(slide_id)
    slide = openslide.OpenSlide(svs_path)
    try: #benzersizlik ihtimali artısın diye metadata ekledik içerik arttırılabilir
        file_size = os.path.getsize(svs_path)
        width, height = slide.dimensions
        level_count = slide.level_count
        raw_metadata_string = f"{width}x{height}|{level_count}|{file_size}"

        metadata_hash = hashlib.sha256(raw_metadata_string.encode("utf-8")).hexdigest()
        return metadata_hash
    finally:
        slide.close()


#DB ye veri ekleme methodu
def add_slide(slide_id: str, db:Session) :
    svs_path = svs_path_get(slide_id)
    filename = os.path.basename(svs_path)
    slide = openslide.OpenSlide(svs_path)
    try:
        raw_properties = dict(slide.properties)
    finally:
        slide.close()

    new_slide = Slide(
        quickhash=generate_metadata_hash(slide_id),
        filename=filename,
        properties=raw_properties  # JSONB kolonuna ham metadatalar yazılır
    )

    db.add(new_slide)
    db.commit()
    db.refresh(new_slide)
    logging.info(f"[Background] Added new slide. '{slide_id}'.'") 

#hash değerinin mevcut olup olmadığını kontol ediyoruz
def check_slide_exists(db: Session, quickhash: str) -> Slide | None:
    return db.query(Slide).filter(Slide.quickhash == quickhash).first()


def process_svs_folder( files: list[UploadFile],db: Session) :
    results = {"added": [], "duplicates": [], "skipped": []}

    for upload_file in files:
        file_name = os.path.basename(upload_file.filename)

        if not file_name.lower().endswith(".svs"):
            reason = "Not an .svs file, skipped."
            logging.warning(f"Skipped '{file_name}': {reason}")
            results["skipped"].append({
                "file_name": file_name,
                "reason": reason,
            })
            continue

        slide_id = save_uploaded_file(file_name, upload_file.file)

        try:
            metadata_hash = generate_metadata_hash(slide_id)
        except Exception as e:
            shutil.rmtree(slide_folder(slide_id), ignore_errors=True)
            error_msg = f"Could not open/read the file: {str(e)}"
            logging.error(f"Error reading '{file_name}': {error_msg}")
            results["skipped"].append({
                "file_name": file_name,
                "reason": error_msg,
            })
            continue

        existing = check_slide_exists(db, metadata_hash)
        if existing:
            shutil.rmtree(slide_folder(slide_id), ignore_errors=True)
            logging.info(f"Duplicate file '{file_name}'. Same hash as '{existing.filename}'.")
            results["duplicates"].append({
                "file_name": file_name,
                "error": "This slide already exists in the system (same metadata found under a different name).",
                "existing_filename": existing.filename,
            })
            continue

        # Görevi otomatik işçi havuzuna teslim ediyoruz
        dicom_executor.submit(dicom_and_zip_process, slide_id)

        results["added"].append({
            "slide_id": slide_id,
            "file_name": file_name,
            "message": "New slide accepted, DICOM conversion started in the background.",
        })

    logging.info(f"Folder scan summary -> Added: {len(results['added'])}, Duplicates: {len(results['duplicates'])}, Skipped: {len(results['skipped'])}")
    return results