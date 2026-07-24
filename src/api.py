import os
from fastapi import  APIRouter, UploadFile,File, HTTPException,Depends
from fastapi.responses import JSONResponse, FileResponse
from sqlalchemy.orm import Session
from typing import List
import logging
from src.database import get_db
from src.services import process_svs_folder, all_folder_get

router = APIRouter() #mainde api oluşturmadığımız ve birden fazla alanda api kullanacağımız zaman kullanılır

@router.post("/upload-folder")
def upload_folder(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    if not files:
        raise HTTPException(status_code=400, detail="file was not sent.")
    try:
        results = process_svs_folder(files, db)
        return JSONResponse(content=results)
    except Exception as e:
        logging.error(f"API Error in upload_folder: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/download-all-dicoms")
def download_all_dicoms():
    zip_path = all_folder_get()

    if not os.path.exists(zip_path) or os.path.getsize(zip_path) < 100:
        raise HTTPException(
            status_code=404,
            detail="not found folder "
        )

    return FileResponse(
        path=zip_path,
        media_type="application/x-zip-compressed",
        filename="all_converted_dicoms.zip"
    )



