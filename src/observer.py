import os
import time
import shutil
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from src.config import get_config_value
from src.services import process_files

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename=os.getenv("LOG_FILE_NAME"),
    filemode="a",
)


def handle_new_svs_file(new_svs_file):
    file_name = os.path.basename(new_svs_file)
    data_folder = get_config_value("DATA_FOLDER")

    os.makedirs(data_folder, exist_ok=True)
    target_filepath = os.path.join(data_folder, file_name)

    if new_svs_file != target_filepath:
        shutil.copy2(new_svs_file, target_filepath)

    logging.info(f"'{file_name}' işleme alınıyor...")
    process_files([file_name])


class SvsFolderHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory and event.src_path.lower().endswith(".svs"):
            logging.info(f"\n[YENİ DOSYA YAKALANDI] -> {event.src_path}")
            time.sleep(3)
            handle_new_svs_file(event.src_path)


def start_observer():
    watch_folder = get_config_value("WATCH_FOLDER")
    if not watch_folder:
        logging.error("Exception: WATCH_FOLDER is missing in the config file.")
        return

    os.makedirs(watch_folder, exist_ok=True)

    observer = Observer()
    event_handler = SvsFolderHandler()
    observer.schedule(event_handler, watch_folder, recursive=False)
    observer.start()

    logging.info(f"Observer is now watching the '{watch_folder}' folder.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        logging.info("Observer is stopped.")
    observer.join()


if __name__ == "__main__":
    start_observer()
