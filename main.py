import os
import shutil
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from src.api import router as api_router

#program kapanırken oluşan data klasörü silinmesi için
@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    data_folder = "data"
    if os.path.exists(data_folder):
        try:
            shutil.rmtree(data_folder)
            print(f"[Shutdown] Successfully deleted local '{data_folder}' directory.")
        except Exception as e:
            print(f"[Shutdown] Error deleting directory '{data_folder}': {e}")


app = FastAPI( title="WSI & DICOM server", lifespan=lifespan)

# src/routes.py'da yazdığımız tüm endpointleri uygulamaya dahil etme işi
#başka bir dosyada daha endpointlerimiz olsaydı onu da mainde birleştirmemiz gerekirdi.
app.include_router(api_router)

@app.get("/")
def home():
    return {"mesaj": "WSI Service is active. Go to /docs ."}

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)


