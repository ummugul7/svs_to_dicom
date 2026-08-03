import os
from flask import render_template, Flask, request, redirect, url_for, jsonify
from dotenv import load_dotenv
from src.services import process_svs_folder, get_slide_details_from_db
from src.database import db_session, init_db

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", os.urandom(24))
init_db(app)


@app.route("/upload", methods=["GET"])
def upload_page():
    return render_template("upload.html", result=None)


@app.route("/upload", methods=["POST"])
def upload_submit():
    files = request.files.getlist("svs_files")

    if not files or all(f.filename == "" for f in files):
        return redirect(url_for("upload_page"))

    result = process_svs_folder(files, db_session)
    db_session.commit()

    return render_template("upload.html", result=result)


@app.route("/slide-details/<path:filename>", methods=["GET"])
def get_slide_details(filename):
    details = get_slide_details_from_db(filename, db_session)

    if not details:
        return jsonify({"detail": "Slide not found"}), 404

    return jsonify(details)
