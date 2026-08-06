# The standard Python os module, along with shutil, is exactly what interacts with your computer's hard drive or SSD to manage these files.
import concurrent.futures
import logging
import os
import shutil
from dotenv import load_dotenv
from sqlalchemy.exc import SQLAlchemyError
from wsidicomizer import WsiDicomizer
from src.model import Slide

from src.helper import (
    check_slide_exists,
    generate_metadata_hash,
    save_uploaded_file,
    svs_path_get,
    dicom_folder_get,
    delete_svs_folder,
    read_slide,
    add_slide_db,
)

load_dotenv()
MAX_THREADS = int(os.getenv("MAX_THREADS"))
dicom_executor = concurrent.futures.ThreadPoolExecutor(max_workers=MAX_THREADS)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename=os.getenv("LOG_FILE_NAME"),
    filemode="a",
)


log = logging.getLogger("werkzeug")
log.setLevel(logging.ERROR)


def dicom_process(file_name: str, metadata_hash: str, root_folder: str = "DATA_FOLDER"):
    """Converts an uploaded SVS file to DICOM format and cleans up the original file.

    This function retrieves the paths for the source SVS file and the target DICOM folder
    using the provided file name. It performs the conversion using WsiDicomizer, verifies
    the successful creation of DICOM files, and deletes the original SVS file to save storage
    space. Any errors encountered during the process are logged.

    Args:
        file_name (str): The name of the SVS file to be processed.
    """
    try:
        svs_path = svs_path_get(file_name, root_folder)
        output_folder = dicom_folder_get(file_name)

        if os.path.exists(output_folder):
            shutil.rmtree(output_folder)

        WsiDicomizer.convert(filepath=svs_path, output_path=output_folder)

        if not os.path.exists(output_folder) or len(os.listdir(output_folder)) == 0:
            raise Exception("DICOM files could not be created.")

        try:
            delete_svs_folder(file_name, root_folder)
            if root_folder == "DATA_FOLDER":
                logging.info(f" Original SVS file deleted to save space: '{file_name}'.")

        except Exception as ex:  # noqa: BLE001
            logging.warning(f" Error deleting original file '{file_name}': {ex!s}")

        add_db(file_name, metadata_hash, root_folder)

    except Exception as e:  # noqa: BLE001
        logging.error(f" Error processing '{file_name}': {e!s}")


def add_db(file_name: str, quickhash: str, root_folder: str = "DATA_FOLDER") -> bool:
    slide = read_slide(file_name, quickhash, root_folder)
    success = add_slide_db(slide)
    if success:
        logging.info(f"Added new slide. '{file_name}'.")
    else:
        logging.warning(f"Integrity error saving '{file_name}' to DB.")
    return success


def process_svs_folder(files):
    """Handles uploaded files from the web interface, saving them locally before processing.

    This function acts as an intermediary for web-based (Flask) file uploads. It iterates over
    the uploaded file streams, validates their extensions, and saves the valid SVS files to the
    designated local data folder. Once saved, it delegates the actual processing (hash checking
    and DICOM conversion) to the core `process_local_files` method.

    Args:
        files (list): A list of uploaded file objects (e.g., from a Flask request).

    Returns:
        dict: A dictionary containing the combined results of the operation, including files
            that were added, duplicates that were found, and files that were skipped.
    """
    results = {"added": [], "duplicates": [], "skipped": []}
    saved_file_names = []
    for upload_file in files:
        file_name = os.path.basename(upload_file.filename)
        if not file_name.lower().endswith(".svs"):
            logging.warning(f"Skipped '{file_name}': Not an .svs file, skipped")
            results["skipped"].append({"file_name": file_name})
            continue

        saved_name = save_uploaded_file(file_name, upload_file.stream)
        saved_file_names.append(saved_name)

    if saved_file_names:
        core_results = process_files(saved_file_names)

        # Çekirdek metottan dönen sonuçları Flask sonuçlarıyla birleştiriyoruz
        results["added"].extend(core_results["added"])
        results["duplicates"].extend(core_results["duplicates"])
    return results


def process_files(file_names: list, root_folder: str = "DATA_FOLDER") -> dict:
    """Processes a list of local SVS filenames, avoiding duplicates and triggering DICOM conversion.

    This core function acts as the central processor for SVS files already present in the local
    data folder. It generates a metadata hash for each file to verify uniqueness against the database.
    Unique files are queued for asynchronous DICOM conversion and registered in the database,
    while duplicates and invalid files are skipped and cleaned up.

    Args:
        file_names (list of str): A list containing the filenames of the SVS files to be processed
            (e.g., ['sample1.svs', 'sample2.svs']).

    Returns:
        dict: A dictionary containing the results of the folder processing with the following keys:
            - "added" (list): A list of dictionaries for files successfully added and queued for processing.
            - "duplicates" (list): A list of dictionaries for files skipped due to existing duplicates.
            - "skipped" (list): A list of dictionaries for files skipped due to invalid formats or read errors.
    """

    results = {"added": [], "duplicates": [], "skipped": []}
    for file_name in file_names:
        try:
            metadata_hash = generate_metadata_hash(file_name, root_folder)
        except (SQLAlchemyError, OSError, ValueError) as e:
            delete_svs_folder(file_name, root_folder)
            logging.error(f"Error reading '{file_name}': could not open/read the file '{e}'")
            results["skipped"].append({"file_name": file_name})
            continue

        existing = check_slide_exists(metadata_hash)
        if existing:
            delete_svs_folder(file_name, root_folder)
            logging.info(f"Duplicate file '{file_name}'. Same hash as '{existing.filename}'.")
            results["duplicates"].append({"file_name": file_name, "match_name": existing.filename})
            continue
        try:
            dicom_executor.submit(dicom_process, file_name, metadata_hash, root_folder)
            results["added"].append({"file_name": file_name})
        except Exception as e:  # noqa: BLE001
            logging.error(f"Unexpected error processing '{file_name}': {e}")
    logging.info(
        f"Core processing summary -> Added: {len(results['added'])}, Duplicates: {len(results['duplicates'])}, Skipped: {len(results['skipped'])}"
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
