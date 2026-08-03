import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, scoped_session, sessionmaker

# .env dosyasındaki değişkenleri Python ortamına yüklemek için
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")  # dburli

# burası stabil bir sytax sqlalchem kullanıyrsan bu tanımı yapılıyor
engine = create_engine(DATABASE_URL)  # dbye bağlanacak yer
db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
# db sorguları yapabilmek için tanımlıyoruz
Base = declarative_base()
Base.metadata.create_all(bind=engine)
Base.query = db_session.query_property()  # modeller üzerinden Slide.query.filter(...) gibi kısayol için


def init_db(app):
    """Flask app'e bağlanır, her isteğin sonunda session'ı otomatik temizler."""

    @app.teardown_appcontext
    def remove_session(exception=None):
        db_session.remove()
