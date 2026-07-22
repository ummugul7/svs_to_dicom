import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# .env dosyasındaki değişkenleri Python ortamına yüklemek için
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL") #buradaki dbdeğerini belki dockerda ayağa kaldırarak yaparım

#burası stabil bir sytax sqlalchem kullanıyrsan bu tanımı yapackasın
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine) #db sorguları yapabilmek için tanımlıyoruz
Base = declarative_base()
Base.metadata.create_all(bind=engine)

def get_db():

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

