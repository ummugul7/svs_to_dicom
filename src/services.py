# The standard Python os module, along with shutil, is exactly what interacts with your computer's hard drive or SSD to manage these files.
import os
import shutil
from fastapi import UploadFile
from sqlalchemy.exc import IntegrityError
from wsidicomizer import WsiDicomizer
from sqlalchemy.orm import Session
from src.model import Slide
from dotenv import load_dotenv
import concurrent.futures
import logging

from src.helper import (
    slide_folder,
    svs_path_get,
    generate_metadata_hash,
    create_thumbnail,
    check_slide_exists,
    save_uploaded_file,
    open_slide_safe
)

load_dotenv()
MAX_THREADS = int(os.getenv("MAX_THREADS"))
dicom_executor = concurrent.futures.ThreadPoolExecutor(max_workers=MAX_THREADS)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename= os.getenv("LOG_FILE_NAME"),
    filemode='a'
)

def dicom_process(slide_id: str):
    folder = slide_folder(slide_id)
    try:
        svs_path = svs_path_get(slide_id)
        file_name = os.path.basename(svs_path)
        output_folder = os.path.join(folder, f"{file_name}_dicom")
        create_thumbnail(slide_id, size=(500, 500))

        if os.path.exists(output_folder):
            shutil.rmtree(output_folder)

        WsiDicomizer.convert(filepath=svs_path, output_path=output_folder)

        if not os.path.exists(output_folder) or len(os.listdir(output_folder)) == 0:
            raise Exception("DICOM files could not be created.")

        from src.database import SessionLocal
        db = SessionLocal()
        try:
            add_db(slide_id, db)
            #dbye veri kaydedildikten ve dönüşüm işelmi bittikten sonra svs dosyası silindi
            if os.path.exists(svs_path):
                os.remove(svs_path)
                logging.info(f"[Background] Original SVS file deleted to save space: '{slide_id}'.")

        except IntegrityError:
            db.rollback()
            logging.warning(f"[Background] Integrity error saving '{slide_id}' to DB. Concurrent upload?")
        finally:
            db.close()

    except Exception as e:
        logging.error(f"[Background] Error processing '{slide_id}': {str(e)}")



def add_db(slide_id: str, db:Session):
    svs_path = svs_path_get(slide_id)
    file_name = os.path.basename(svs_path)

    with open_slide_safe(svs_path) as slide:
        new_slide = Slide(
            quickhash=generate_metadata_hash(slide_id),
            filename=file_name,
            properties=slide.properties,
        )
        db.add(new_slide)
        db.commit()
        db.refresh(new_slide)
        logging.info(f"[Background] Added new slide. '{file_name}'.'")




def process_svs_folder( files: list[UploadFile],db: Session) :
    results = {"added": [], "duplicates": [], "skipped": []}

    for upload_file in files:
        file_name = os.path.basename(upload_file.filename)

        if not file_name.lower().endswith(".svs"):
            logging.warning(f"Skipped '{file_name}': Not an .svs file, skipped")
            results["skipped"].append({
                "file_name": file_name,
                "reason": "Not an .svs file, skipped",
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

        dicom_executor.submit(dicom_process, slide_id)

        results["added"].append({
            "slide_id": slide_id,
            "file_name": file_name,
            "message": "New slide accepted, DICOM conversion started in the background.",
        })

    logging.info(f"Folder scan summary -> Added: {len(results['added'])}, Duplicates: {len(results['duplicates'])}, Skipped: {len(results['skipped'])}")
    return results