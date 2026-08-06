import hashlib
import os
import shutil
from contextlib import contextmanager

import openslide
from psycopg2 import IntegrityError
from sqlalchemy import select

from src.database import db_session
from src.model import Slide

from src.config import get_config_value


def svs_path_get(file_name: str, root_folder: str = "DATA_FOLDER") -> str:
    data_folder = get_config_value(root_folder)
    svs_path = os.path.join(data_folder, file_name)
    if not os.path.isfile(svs_path):
        raise FileNotFoundError(f"'{file_name}' not found in data folder.")
    return svs_path


def dicom_folder_get(file_name: str) -> str:
    base_name = os.path.splitext(file_name)[0]
    data_folder = get_config_value("DATA_FOLDER")

    os.makedirs(data_folder, exist_ok=True)
    return os.path.join(data_folder, f"{base_name}_dicom")


# yüklenen svs dosyasını kaydediyoruz
def save_uploaded_file(file_name: str, file_object) -> str:
    data_folder = get_config_value("DATA_FOLDER")
    os.makedirs(data_folder, exist_ok=True)
    svs_path = os.path.join(data_folder, file_name)
    with open(svs_path, "wb") as buffer:
        shutil.copyfileobj(file_object, buffer)
    return file_name


@contextmanager
def open_slide_safe(svs_path: str):
    slide = openslide.OpenSlide(svs_path)
    try:
        yield slide
    finally:
        slide.close()


def generate_metadata_hash(file_name: str, root_folder: str = "DATA_FOLDER") -> str:
    svs_path = svs_path_get(file_name, root_folder)

    with open_slide_safe(svs_path) as slide:
        file_size = os.path.getsize(svs_path)
        width, height = slide.dimensions
        level_count = slide.level_count
        raw_metadata_string = f"{width}x{height}|{level_count}|{file_size}"
        return hashlib.sha256(raw_metadata_string.encode("utf-8")).hexdigest()


# hash değerinin mevcut olup olmadığını kontol ediyoruz
def check_slide_exists(quickhash: str) -> Slide | None:
    stmt = select(Slide).where(Slide.quickhash == quickhash)
    return db_session.execute(stmt).scalar_one_or_none()


def delete_svs_folder(file_name: str, root_folder: str = "DATA_FOLDER") -> None:
    if root_folder != "DATA_FOLDER":
        return

    folder_path = get_config_value(root_folder)
    svs_path = os.path.join(folder_path, file_name)
    if os.path.exists(svs_path):
        os.remove(svs_path)


def read_slide(file_name: str, quickhash: str, root_folder: str = "DATA_FOLDER") -> Slide:
    svs_path = svs_path_get(file_name, root_folder)
    with open_slide_safe(svs_path) as slide:
        return Slide(quickhash=quickhash, filename=file_name, properties=dict(slide.properties))


def add_slide_db(new_slide: Slide):
    try:
        db_session.add(new_slide)
        db_session.commit()
        return True
    except IntegrityError:
        db_session.rollback()
        return False
