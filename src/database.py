import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# .env dosyasındaki değişkenleri Python ortamına yüklemek için
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL") #dburli

#burası stabil bir sytax sqlalchem kullanıyrsan bu tanımı yapılıyor
engine = create_engine(DATABASE_URL) #dbye bağlanacak yer
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine) #db sorguları yapabilmek için tanımlıyoruz
Base = declarative_base()
Base.metadata.create_all(bind=engine)

#db her kullanılacağında bir bağlantı tanımlanıyor iş bitnince de kapatılıyor
def get_db():
    db = SessionLocal()
    try:
        yield db #sessionu kullan işi biitnce bana dön demek
    finally:
        db.close()

