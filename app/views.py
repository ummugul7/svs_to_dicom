import os
from flask import render_template, Flask, request, redirect, url_for, jsonify
from dotenv import load_dotenv
from src.services import process_svs_folder, get_slide_details_from_db
from src.database import db_session, init_db
from src.model import Slide, AppConfig
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_admin.menu import MenuLink
from flask_admin import AdminIndexView, expose

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", os.urandom(24))
init_db(app)


class MyAdminIndexView(AdminIndexView):
    @expose("/")
    def index(self):
        slide_count = db_session.query(Slide).count()
        return self.render("admin/my_index.html", slide_count=slide_count)


admin = Admin(app, name="administration panels ", index_view=MyAdminIndexView())
admin.add_view(ModelView(Slide, db_session))
admin.add_view(ModelView(AppConfig, db_session))
admin.add_link(MenuLink(name="file upload", category="", url="/upload"))


@app.route("/upload", methods=["GET"])
def upload_page():
    return render_template("upload.html", result=None)


@app.route("/upload", methods=["POST"])
def upload_submit():
    files = request.files.getlist("svs_files")

    if not files or all(f.filename == "" for f in files):
        return redirect(url_for("upload_page"))

    result = process_svs_folder(files)
    db_session.commit()

    return render_template("upload.html", result=result)


@app.route("/slide-details/<path:filename>", methods=["GET"])
def get_slide_details(filename):
    details = get_slide_details_from_db(filename)

    if not details:
        return jsonify({"detail": "Slide not found"}), 404

    return jsonify(details)
