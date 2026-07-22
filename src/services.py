# The standard Python os module, along with shutil, is exactly what interacts with your computer's hard drive or SSD to manage these files.
import os
import shutil
import uuid
import zipfile  #DICOM dosyasını zipe getirmek için
import openslide
from sqlalchemy.exc import IntegrityError
from wsidicomizer import WsiDicomizer
import hashlib
from sqlalchemy.orm import Session
from src.model import Slide

DATA_FOLDER = "data"

def slide_folder(slide_id: str) -> str:
    return os.path.join(DATA_FOLDER, slide_id)

def svs_path_get(slide_id: str) -> str:
    folder = slide_folder(slide_id)
    if not os.path.isdir(folder):
        raise FileNotFoundError(f"'{slide_id}' slide not found.")
    for file in os.listdir(folder):
        if file.endswith(".svs"):
            return os.path.join(folder, file)
    raise FileNotFoundError(f"'{slide_id}' slide not found ")


def save_uploaded_file(file_name: str, file_object) -> str:
    slide_id = uuid.uuid4().hex
    folder = slide_folder(slide_id)
    os.makedirs(folder, exist_ok=True) #localde kalsör oluşturmak için

    svs_path = os.path.join(folder, file_name)
    with open(svs_path, "wb") as buffer:
        shutil.copyfileobj(file_object, buffer)
    return slide_id


#seçilen metadataları döndüren endpoit
def get_metadata(slide_id: str) -> dict:
    svs_path = svs_path_get(slide_id)
    slide = openslide.OpenSlide(svs_path)
    try:
        width, height = slide.dimensions
        return {
            "slide_id": slide_id,
            "file_name": os.path.basename(svs_path),
            "original_resolution": f"{width} x {height}",
            "total_level_count": slide.level_count,
            "features": {
                key: value
                for key, value in slide.properties.items()
                if any(
                    k in key
                    for k in ["magnification", "vendor", "mpp", "objective"]
                )
            },
        }
    finally:
        slide.close()


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


def create_tile(
    slide_id: str,
    level: int = 0,
    x: int = 5000,
    y: int = 8000,
    w: int = 256,
    h: int = 256,
) -> str:

    svs_path = svs_path_get(slide_id)
    folder = slide_folder(slide_id)
    slide = openslide.OpenSlide(svs_path)
    try:
        tile = slide.read_region((x, y), level, (w, h))
        tile_rgb = tile.convert("RGB")
        tile_path = os.path.join(folder, f"tile_{level}_{x}_{y}_{w}x{h}.png")
        tile_rgb.save(tile_path)
        return tile_path
    finally:
        slide.close()


def background_dicom_and_zip_process(slide_id: str):
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


        #ilerleyen zamanlarda bizden zipli bir dosya istenmezse bunu sileriz
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(output_folder):
                for file in files:
                    file_path = os.path.join(root, file)
                    zipf.write(file_path, os.path.relpath(file_path, output_folder))
        #burda zip yaptıktan sonra fazlalı olmasın diye dosyayı siliyoruz
        if os.path.exists(output_folder):
            shutil.rmtree(output_folder)

        print(f"[Background] Processing complete for '{slide_id}'. ZIP ready.")
    except Exception as e:
        print(f"[Background] Error processing '{slide_id}': {str(e)}")



def zip_path_get(slide_id: str) -> str:
    return os.path.join(slide_folder(slide_id), "dicom_output.zip")


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
def add_slide(slide_id: str, db:Session) -> Slide:
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
    return new_slide  # burada yeni nesneyi döndürüyor da gerek olmayabilir


#hash değerinin mevcut olup olmadığını kontol ediyoruz
def check_slide_exists(db: Session, quickhash: str) -> Slide | None:
    return db.query(Slide).filter(Slide.quickhash == quickhash).first()


def process_svs_folder(
    files: list[UploadFile],
    db: Session
) -> dict:
    results = {"added": [], "duplicates": [], "skipped": []}

    for upload_file in files:
        file_name = os.path.basename(upload_file.filename)

        if not file_name.lower().endswith(".svs"):
            results["skipped"].append({
                "file_name": file_name,
                "reason": "Not an .svs file, skipped.",
            })
            continue

        slide_id = save_uploaded_file(file_name, upload_file.file)

        try:
            metadata_hash = generate_metadata_hash(slide_id)
        except Exception as e:
            shutil.rmtree(slide_folder(slide_id), ignore_errors=True)
            results["skipped"].append({
                "file_name": file_name,
                "reason": f"Could not open/read the file: {str(e)}",
            })
            continue

        existing = check_slide_exists(db, metadata_hash)
        if existing:
            shutil.rmtree(slide_folder(slide_id), ignore_errors=True)
            results["duplicates"].append({
                "file_name": file_name,
                "error": "This slide already exists in the system (same metadata found under a different name).",
                "existing_filename": existing.filename,
            })
            continue

        try:
            add_slide(slide_id, db)
        except IntegrityError:
            db.rollback()
            shutil.rmtree(slide_folder(slide_id), ignore_errors=True)
            results["duplicates"].append({
                "file_name": file_name,
                "error": "This slide was already added by a concurrent request.",
            })
            continue
        background_dicom_and_zip_process(slide_id)

        results["added"].append({
            "slide_id": slide_id,
            "file_name": file_name,
            "message": "New slide added, DICOM conversion started in the background.",
        })

    return results