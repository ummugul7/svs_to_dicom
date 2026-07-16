# The standard Python os module, along with shutil, is exactly what interacts with your computer's hard drive or SSD to manage these files.
import os
import shutil
import uuid
import zipfile  #DICOM dosyasını zipe getirmek için
import openslide
from wsidicomizer import WsiDicomizer

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

        if os.path.exists(output_folder):
            shutil.rmtree(output_folder)
        if os.path.exists(zip_path):
            os.remove(zip_path)

        WsiDicomizer.convert(filepath=svs_path, output_path=output_folder)

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

