import os
from fastapi import  APIRouter, BackgroundTasks,  UploadFile,File, HTTPException,Query
from fastapi.responses import JSONResponse, FileResponse

from src.services import (
    save_uploaded_file,
    get_metadata,
    get_properties,
    create_thumbnail,
    create_tile,
    background_dicom_and_zip_process,
    zip_path_get,
)

router = APIRouter() #mainde api oluşturmadığımız ve birden fazla alanda api kullanacağımız zaman kullanılır

#bu methodda yüklediğin dosyadan slide_id dönüyor sonraki tüm istekleri bu id ile gerçekleştiriyorsun
# Swaggerda bunu ekleyerek method endpoint isteği atıyorsun react ile UI yaparsak onu da her istekte gömeriz
@router.post("/upload")
async def upload_wsi(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    if not file.filename.endswith(".svs"):
        raise HTTPException(status_code=400, detail="Please upload only the .svs file.")

    try:
        slide_id = save_uploaded_file(file.filename, file.file)
        background_tasks.add_task(background_dicom_and_zip_process, slide_id)
        return JSONResponse(content={
            "slide_id": slide_id,
            "message": "file loaded. DICOM translate started."
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metadata")
#buradaki query urlden geleceke demek
#bkz istek şu şekilde gidiyor http://127.0.0.1:8000/metadata?slide_id=b4af99169bba4ef7bb9ec7c09477ebcc
def metadata_endpoint(slide_id: str = Query(..., )):
    try:
        return JSONResponse(content=get_metadata(slide_id))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail="The slide source file was not found. It may have been auto-deleted after DICOM conversion. Please load  the file again.."
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/properties")
def properties_endpoint(slide_id: str = Query(...)):
    try:
        return JSONResponse(content=get_properties(slide_id))
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail="The slide source file was not found. It may have been auto-deleted after DICOM conversion. Please load  the file again..",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/thumbnail")
def thumbnail_endpoint(slide_id: str = Query(...)):
    try:
        thumbnail_path = create_thumbnail(slide_id)
        return FileResponse(thumbnail_path, media_type="image/png")
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail="The slide source file was not found. It may have been auto-deleted after DICOM conversion. Please load  the file again..",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/download-thumbnail")
def download_thumbnail_endpoint(slide_id: str = Query(...)):
    try:
        thumbnail_path = create_thumbnail(slide_id)
        return FileResponse(
            path=thumbnail_path,
            media_type="image/png",
            filename=f"{slide_id}_thumbnail.png"
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tile")
def tile_endpoint( #default değerler tanımlanıyor
    slide_id: str = Query(...),
    level: int = 0,
    x: int = 5000,
    y: int = 8000,
    w: int = 256,
    h: int = 256,
):
    try:
        tile_path = create_tile(slide_id, level, x, y, w, h)
        return FileResponse(tile_path, media_type="image/png")
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail="The slide source file was not found. It may have been auto-deleted after DICOM conversion. Please load  the file again..",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/download-dicom-zip")
def download_dicom_zip(slide_id: str = Query(...)):
    zip_path = zip_path_get(slide_id)
    if not os.path.exists(zip_path):
        raise HTTPException(
            status_code=404,
            detail="ZIP file is not ready or process is still going."
        )
    return FileResponse(
        path=zip_path,
        media_type="application/x-zip-compressed",
        filename=f"{slide_id}_dicom_output.zip"
    )