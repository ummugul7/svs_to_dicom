import os
from src.database import db_session
from src.model import AppConfig


# bu methodu generic yapma sebebimiz bakşa bir değişkeni de config olarak kullanmak istersek diye.
def get_config_value(key: str, default: str = None) -> str:
    config_entry = db_session.query(AppConfig).filter(AppConfig.key == key).first()

    if config_entry and config_entry.value:
        return config_entry.value

    return os.getenv(key, default)
