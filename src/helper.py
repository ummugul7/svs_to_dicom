import hashlib
import os
import shutil
from contextlib import contextmanager

import openslide
from sqlalchemy import select

from src.database import db_session
from src.model import Slide

DATA_FOLDER = os.getenv("DATA_FOLDER")


def svs_path_get(file_name: str) -> str:
    svs_path = os.path.join(DATA_FOLDER, file_name)
    if not os.path.isfile(svs_path):
        raise FileNotFoundError(f"'{file_name}' not found in data folder.")
    return svs_path


def dicom_folder_get(file_name: str) -> str:
    base_name = os.path.splitext(file_name)[0]
    return os.path.join(DATA_FOLDER, f"{base_name}_dicom")


def save_uploaded_file(file_name: str, file_object) -> str:
    os.makedirs(DATA_FOLDER, exist_ok=True)

    svs_path = os.path.join(DATA_FOLDER, file_name)
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


def generate_metadata_hash(file_name: str) -> str:
    svs_path = svs_path_get(file_name)

    with open_slide_safe(svs_path) as slide:
        file_size = os.path.getsize(svs_path)
        width, height = slide.dimensions
        level_count = slide.level_count
        raw_metadata_string = f"{width}x{height}|{level_count}|{file_size}"
        return hashlib.sha256(raw_metadata_string.encode("utf-8")).hexdigest()


def create_thumbnail(file_name: str, size=(500, 500)) -> str:
    svs_path = svs_path_get(file_name)

    with open_slide_safe(svs_path) as slide:
        thumbnail = slide.get_thumbnail(size)
        thumbnail_path = os.path.join(DATA_FOLDER, f"{file_name}_thumbnail.png")
        thumbnail.save(thumbnail_path)
        return thumbnail_path


# hash değerinin mevcut olup olmadığını kontol ediyoruz
def check_slide_exists(quickhash: str) -> Slide | None:
    stmt = select(Slide).where(Slide.quickhash == quickhash)
    return db_session.execute(stmt).scalar_one_or_none()
