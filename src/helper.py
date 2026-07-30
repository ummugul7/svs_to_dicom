import hashlib
import os
import shutil
import uuid
from contextlib import contextmanager

import openslide
from sqlalchemy import select
from sqlalchemy.orm import Session  # noqa: TC002

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
    raise FileNotFoundError(f"No .svs file found in '{slide_id}' directory.")


def save_uploaded_file(file_name: str, file_object) -> str:
    slide_id = uuid.uuid4().hex
    folder = slide_folder(slide_id)
    os.makedirs(folder, exist_ok=True)  # localde kalsör oluşturmak için

    svs_path = os.path.join(folder, file_name)
    with open(svs_path, "wb") as buffer:
        shutil.copyfileobj(file_object, buffer)
    return slide_id


@contextmanager
def open_slide_safe(svs_path: str):
    slide = openslide.OpenSlide(svs_path)
    try:
        yield slide
    finally:
        slide.close()


def generate_metadata_hash(slide_id: str) -> str:
    svs_path = svs_path_get(slide_id)

    with open_slide_safe(svs_path) as slide:
        file_size = os.path.getsize(svs_path)
        width, height = slide.dimensions
        level_count = slide.level_count
        raw_metadata_string = f"{width}x{height}|{level_count}|{file_size}"
        return hashlib.sha256(raw_metadata_string.encode("utf-8")).hexdigest()


def create_thumbnail(slide_id: str, size=(500, 500)) -> str:
    svs_path = svs_path_get(slide_id)
    file_name = os.path.basename(svs_path)
    folder = slide_folder(slide_id)

    with open_slide_safe(svs_path) as slide:
        thumbnail = slide.get_thumbnail(size)
        thumbnail_path = os.path.join(folder, f"{file_name}_thumbnail.png")
        thumbnail.save(thumbnail_path)
        return thumbnail_path


# hash değerinin mevcut olup olmadığını kontol ediyoruz
def check_slide_exists(db: Session, quickhash: str) -> Slide | None:
    stmt = select(Slide).where(Slide.quickhash == quickhash)
    return db.execute(stmt).scalar_one_or_none()
