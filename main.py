import uvicorn
from fastapi import FastAPI
from src.api import router as api_router
from src.services import dicom_executor
from src.database import engine, Base
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

Base.metadata.create_all(bind=engine)
@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    dicom_executor.shutdown(wait=False)

app = FastAPI(title="WSI & DICOM server", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# src/routes.py'da yazdığımız tüm endpointleri uygulamaya dahil etmek için
#başka bir dosyada daha endpointlerimiz olsaydı onu da mainde birleştirmemiz gerekirdi.
app.include_router(api_router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)


