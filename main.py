import atexit

from app.views import app
from src.database import Base, engine
from src.services import dicom_executor

Base.metadata.create_all(bind=engine)


def shutdown_executor():
    dicom_executor.shutdown(wait=False)


# Register the shutdown hook to clean up threads when Flask exits
atexit.register(shutdown_executor)

if __name__ == "__main__":
    # Start the Flask development server on port 8000 (port 5000 is often blocked by macOS AirPlay)
    app.run(host="127.0.0.1", port=8000, debug=True)
