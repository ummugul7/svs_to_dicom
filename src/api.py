from fastapi import  APIRouter, UploadFile,File, HTTPException,Depends
from fastapi.responses import JSONResponse, FileResponse
from sqlalchemy.orm import Session
from typing import List
import logging
from src.database import get_db
from src.services import process_svs_folder

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






