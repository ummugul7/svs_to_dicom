import atexit

from app.views import app
from src.database import Base, engine
from src.services import dicom_executor

# dbde tabloları olup olamdığını kontorl eder yoksa oluşturur.
Base.metadata.create_all(bind=engine)


# kullandığımız threadların sistem kapanması durumunda serbest bırakılmasını sağlar.
def shutdown_executor():
    dicom_executor.shutdown(wait=False)


atexit.register(shutdown_executor)

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=True)
