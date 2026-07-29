import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session # noqa: TC002

from src.database import get_db
from src.services import process_svs_folder

router = APIRouter()  # mainde api oluşturmadığımız ve birden fazla alanda api kullanacağımız zaman kullanılır

@router.post("/upload-folder")
def upload_folder(
    files: list[UploadFile] = File(...), # noqa: B008
    db: Session = Depends(get_db), # noqa: B008
):
    if not files:
        raise HTTPException(status_code=400, detail="file was not sent.")
    try:
        results = process_svs_folder(files, db)
        return JSONResponse(content=results)
    except Exception as e:
        logging.error(f"API Error in upload_folder: {e!s}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e
