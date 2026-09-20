import os
import uuid
from io import BytesIO
from flask import Flask, render_template, request, redirect, url_for
from werkzeug.utils import secure_filename
from PIL import Image
import mysql.connector
from utils.bc_ocr import extract_text


# ------------------ CONFIG ------------------
UPLOAD_FOLDER = "static/cards"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "tif", "tiff", "bmp", "gif"}

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": os.environ["DB_PASSWORD"],
    "database": "business_cards_db",    
    "autocommit": True,
}

# ------------------ APP SETUP ------------------
app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.secret_key = os.environ.get("SECRET_KEY", "dev-only")

# ------------------ HELPERS ------------------
def get_db():
    return mysql.connector.connect(**DB_CONFIG)

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def ensure_blank_image():
    """Create a white placeholder image if it doesn't exist."""
    blank_path = os.path.join(app.config["UPLOAD_FOLDER"], "blank.jpg")
    if not os.path.exists(blank_path):
        img = Image.new("RGB", (900, 600), (255, 255, 255))
        img.save(blank_path, format="JPEG", quality=90)
    return blank_path

def save_upload(file, filename_base):
    ext = file.filename.rsplit(".", 1)[1].lower()
    safe_name = f"{filename_base}.{ext}"
    save_path = os.path.join("static", "cards", safe_name)  # relative to /static
    abs_path = os.path.join(os.getcwd(), save_path)

    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    file.save(abs_path)

    return save_path  # <-- return relative path like "static/cards/abc.jpg"


# Make sure placeholder exists at startup
ensure_blank_image()


# ------------------ ROUTES ------------------

# Redirect root to start page
@app.route("/", methods=["GET"])
def root():
    return redirect(url_for("start_page"))

# Start / Landing page
@app.route("/start", methods=["GET"])
def start_page():
    return render_template("bc_start.html")

# Upload page (GET)
@app.route("/upload_page", methods=["GET"])
def upload_page():
    return render_template("bc_upload.html")

import uuid
import os
from flask import request, redirect, url_for, flash
import uuid
import os
from flask import request, redirect, url_for, flash

@app.route("/upload", methods=["POST"])
def upload_card():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    # --- generate unique card_id ---
    def generate_unique_card_id():
        while True:
            cid = str(uuid.uuid4())[:8]  # short id
            cursor.execute("SELECT 1 FROM business_cards WHERE card_id = %s LIMIT 1", (cid,))
            if not cursor.fetchone():
                return cid

    card_id = generate_unique_card_id()

    card_type  = request.form.get("card_type")  # 'front' or 'front_back'
    front_file = request.files.get("front_image")
    back_file  = request.files.get("back_image")

    upload_folder = "static/cards"
    os.makedirs(upload_folder, exist_ok=True)

    # ---- FRONT (required) ----
    if not front_file or not front_file.filename:
        # keep your preferred error handling
        return "Error: Front image required", 400

    front_filename = f"{card_id}_front.jpg"
    front_rel_path = os.path.join(upload_folder, front_filename).replace("\\", "/")
    front_abs_path = os.path.join(os.getcwd(), front_rel_path)
    front_file.save(front_abs_path)

    # OCR front (safe-guard with try/except so upload still succeeds if OCR fails)
    try:
        front_text = extract_text(front_abs_path) or ""
    except Exception as e:
        print(f"[OCR] Front failed: {e}")
        front_text = ""

    cursor.execute(
        """
        INSERT INTO business_cards (card_id, side, raw_text, image_path, created_at)
        VALUES (%s, %s, %s, %s, NOW())
        """,
        (card_id, "front", front_text, front_rel_path),
    )

    # ---- BACK ----
    if card_type == "front_back" and back_file and back_file.filename:
        # real back image
        back_filename = f"{card_id}_back.jpg"
        back_rel_path = os.path.join(upload_folder, back_filename).replace("\\", "/")
        back_abs_path = os.path.join(os.getcwd(), back_rel_path)
        back_file.save(back_abs_path)

        try:
            back_text = extract_text(back_abs_path) or ""
        except Exception as e:
            print(f"[OCR] Back failed: {e}")
            back_text = ""

        cursor.execute(
            """
            INSERT INTO business_cards (card_id, side, raw_text, image_path, created_at)
            VALUES (%s, %s, %s, %s, NOW())
            """,
            (card_id, "back", back_text, back_rel_path),
        )

    else:
        # fallback: blank back
        blank_path = os.path.join(upload_folder, "blank.jpg").replace("\\", "/")
        cursor.execute(
            """
            INSERT INTO business_cards (card_id, side, raw_text, image_path, created_at)
            VALUES (%s, %s, %s, %s, NOW())
            """,
            (card_id, "back", "", blank_path),
        )


    conn.commit()
    cursor.close()
    conn.close()

    flash("Card uploaded successfully!", "success")
    return redirect(url_for("card_detail", card_id=card_id))



# Search page (empty form view)
@app.route("/search_page", methods=["GET"])
def search_page():
    # render empty results initially
    return render_template("bc_search.html", q="", results=[])

# Search handler (supports GET ?q= and POST form 'keyword')
@app.route("/search", methods=["GET", "POST"])
def search_cards():
    q = ""
    if request.method == "POST":
        q = request.form.get("keyword", "").strip()
    else:
        q = request.args.get("q", "").strip()

    results = []
    if q:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT id, card_id, side, raw_text, image_path, created_at
            FROM business_cards
            WHERE raw_text LIKE %s
            ORDER BY created_at DESC, card_id, side
            """,
            (f"%{q}%",),
        )
        results = cursor.fetchall()
        cursor.close()
        conn.close()

    # Results is a flat list of rows; bc_search.html will loop over it
    return render_template("bc_search.html", q=q, results=results)

# Card detail view (shows both sides)
@app.route("/card/<card_id>", methods=["GET"])
def card_detail(card_id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT id, card_id, side, raw_text, image_path, created_at FROM business_cards WHERE card_id = %s ORDER BY side",
        (card_id,),
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template("bc_detail.html", card_id=card_id, rows=rows)

import os
from flask import redirect, url_for, jsonify

@app.route("/card/<card_id>/delete", methods=["POST"])
def delete_card(card_id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    # Fetch all rows for this card
    cursor.execute("SELECT id, side, image_path FROM business_cards WHERE card_id = %s", (card_id,))
    rows = cursor.fetchall()

    if not rows:
        cursor.close()
        conn.close()
        return jsonify({"success": False, "error": "Card not found"}), 404

    # Separate front and back
    front_rows = [row for row in rows if row["side"].lower() == "front"]
    back_rows = [row for row in rows if row["side"].lower() == "back"]

    ids_to_delete = []
    images_to_delete = []

    # Always delete the front row(s)
    for r in front_rows:
        ids_to_delete.append(r["id"])
        images_to_delete.append(r["image_path"])

    # Only delete the back row if it's not the placeholder
    for r in back_rows:
        if r["image_path"] != "static/cards/blank.jpg":
            ids_to_delete.append(r["id"])
            images_to_delete.append(r["image_path"])
        else:
            # Just delete the DB entry for blank back (not the file itself)
            ids_to_delete.append(r["id"])

    # Delete DB entries
    if ids_to_delete:
        cursor.executemany("DELETE FROM business_cards WHERE id = %s", [(i,) for i in ids_to_delete])
        conn.commit()

    cursor.close()
    conn.close()

    # Delete image files safely (skip blank.jpg)
    for img_path in images_to_delete:
        if img_path and os.path.exists(img_path) and not img_path.endswith("blank.jpg"):
            os.remove(img_path)

    return jsonify({"success": True})

@app.route("/api/search_cards", methods=["GET"])
def api_search_cards():
    keyword = request.args.get("q", "").strip()
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    if keyword:
        cursor.execute(
            """
            SELECT card_id, side, raw_text, image_path 
            FROM business_cards
            WHERE raw_text LIKE %s
            ORDER BY created_at DESC
            """,
            (f"%{keyword}%",),
        )
    else:
        cursor.execute(
            """
            SELECT card_id, side, raw_text, image_path
            FROM business_cards
            ORDER BY created_at DESC
            """
        )

    results = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(results)


# ------------------ MAIN ------------------
if __name__ == "__main__":
    
    # You can set host="0.0.0.0" to access on LAN
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1", host="0.0.0.0", port=5200)
    