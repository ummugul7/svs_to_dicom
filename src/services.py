# The standard Python os module, along with shutil, is exactly what interacts with your computer's hard drive or SSD to manage these files.
import concurrent.futures
import logging
import os
import shutil
from dotenv import load_dotenv
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from src.database import db_session
from wsidicomizer import WsiDicomizer

from src.helper import (
    check_slide_exists,
    generate_metadata_hash,
    open_slide_safe,
    save_uploaded_file,
    svs_path_get,
    dicom_folder_get,
    DATA_FOLDER,
)
from src.model import Slide

load_dotenv()
MAX_THREADS = int(os.getenv("MAX_THREADS"))
dicom_executor = concurrent.futures.ThreadPoolExecutor(max_workers=MAX_THREADS)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename=os.getenv("LOG_FILE_NAME"),
    filemode="a",
)


def dicom_process(file_name: str):
    try:
        svs_path = svs_path_get(file_name)
        output_folder = dicom_folder_get(file_name)

        if os.path.exists(output_folder):
            shutil.rmtree(output_folder)

        WsiDicomizer.convert(filepath=svs_path, output_path=output_folder)

        if not os.path.exists(output_folder) or len(os.listdir(output_folder)) == 0:
            raise Exception("DICOM files could not be created.")

        try:
            if os.path.exists(svs_path):
                os.remove(svs_path)
                logging.info(f" Original SVS file deleted to save space: '{file_name}'.")

        except Exception as ex:  # noqa: BLE001
            logging.warning(f" Error deleting original file '{file_name}': {ex!s}")

    except Exception as e:  # noqa: BLE001
        logging.error(f" Error processing '{file_name}': {e!s}")


def add_db(file_name: str):
    svs_path = svs_path_get(file_name)

    with open_slide_safe(svs_path) as slide:
        new_slide = Slide(
            quickhash=generate_metadata_hash(file_name),
            filename=file_name,
            properties=dict(slide.properties),
        )
        db_session.add(new_slide)
        db_session.commit()
        db_session.refresh(new_slide)
        logging.info(f" Added new slide. '{file_name}'.'")


def process_svs_folder(files):
    results = {"added": [], "duplicates": [], "skipped": []}

    for upload_file in files:
        file_name = os.path.basename(upload_file.filename)

        if not file_name.lower().endswith(".svs"):
            logging.warning(f"Skipped '{file_name}': Not an .svs file, skipped")
            results["skipped"].append({"file_name": file_name})
            continue

        file_name = save_uploaded_file(file_name, upload_file.stream)

        try:
            metadata_hash = generate_metadata_hash(file_name)
        except (SQLAlchemyError, OSError, ValueError) as e:
            svs_path = os.path.join(DATA_FOLDER, file_name)
            if os.path.exists(svs_path):
                os.remove(svs_path)

            logging.error(f"Error reading '{file_name}': could not open/read the file '{e}'")
            results["skipped"].append(
                {
                    "file_name": file_name,
                }
            )
            continue

        existing = check_slide_exists(metadata_hash)
        if existing:
            svs_path = os.path.join(DATA_FOLDER, file_name)
            if os.path.exists(svs_path):
                os.remove(svs_path)
            logging.info(f"Duplicate file '{file_name}'. Same hash as '{existing.filename}'.")
            results["duplicates"].append({"file_name": file_name, "match_name": existing.filename})
            continue

        try:
            add_db(file_name)
        except IntegrityError:
            db_session.rollback()
            logging.warning(f" Integrity error saving '{file_name}' to DB.")

        dicom_executor.submit(dicom_process, file_name)

        results["added"].append({"file_name": file_name})

    logging.info(
        f"Folder scan summary -> Added: {len(results['added'])}, Duplicates: {len(results['duplicates'])}, Skipped: {len(results['skipped'])}"
    )
    return results


def get_slide_details_from_db(file_name: str):
    slide = Slide.query.filter(Slide.filename == file_name).first()
    if not slide:
        return None
    return {
        "filename": slide.filename,
        "date": slide.created_at.strftime("%d.%m.%Y %H:%M") if slide.created_at else "unknown",
        "properties": slide.properties or {},
    }
