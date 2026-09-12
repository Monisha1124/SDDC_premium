from flask import Flask, render_template, request, redirect, url_for,jsonify, session , send_from_directory
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = "sri-danwandhri-development-key"
import os
from werkzeug.utils import secure_filename

DATABASE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "database.db")


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn
def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            email TEXT,
            concern TEXT NOT NULL,
            appointment_date TEXT NOT NULL,
            appointment_time TEXT NOT NULL,
            dental_concern TEXT,
            message TEXT,
            status TEXT DEFAULT 'PENDING',
            rescheduled_date TEXT,
            rescheduled_time TEXT,
            created_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_name TEXT NOT NULL,
            rating INTEGER NOT NULL,
            comment TEXT NOT NULL,
            photo TEXT,
            created_at TEXT NOT NULL
        )
    """)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS before_after (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        category TEXT NOT NULL,
        before_photo TEXT NOT NULL,
        after_photo TEXT NOT NULL,
        visible INTEGER DEFAULT 1,
        created_at TEXT NOT NULL
    )
""")
    conn.execute("""
CREATE TABLE IF NOT EXISTS media (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    category TEXT NOT NULL,
    media_type TEXT NOT NULL,
    filename TEXT NOT NULL,
    visible INTEGER DEFAULT 1,
    created_at TEXT NOT NULL
)
""")
    conn.execute("""
CREATE TABLE IF NOT EXISTS patients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_name TEXT NOT NULL,
    phone TEXT,
    email TEXT,
    date_of_birth TEXT,
    gender TEXT,
    address TEXT,
    medical_notes TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
)
""")

    conn.commit()
    conn.close()
@app.route("/")
def home():
    conn = get_db()

    reviews = conn.execute("""
        SELECT *
        FROM reviews
        ORDER BY id DESC
    """).fetchall()
    gallery_items = conn.execute("""
    SELECT *
    FROM before_after
    WHERE visible = 1
    ORDER BY id DESC
""").fetchall()
    media_items = conn.execute("""
        SELECT * FROM media
        WHERE visible = 1
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    return render_template(
        "index.html",
        reviews=reviews,
        gallery_items=gallery_items,
        medai_items=media_items
    )
@app.route("/uploads/<filename>")
def uploaded_file(filename):
    upload_folder = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "uploads"
    )

    return send_from_directory(
        upload_folder,
        filename
    )
@app.route("/submit-review", methods=["POST"])
def submit_review():

    patient_name = request.form.get("patient_name", "").strip()
    rating = request.form.get("rating", "").strip()
    comment = request.form.get("comment", "").strip()

    photo = request.files.get("photo")

    # Validate required fields
    if not patient_name or not rating or not comment:
        return "Please fill in your name, rating and review.", 400

    try:
        rating = int(rating)
    except ValueError:
        return "Invalid rating.", 400

    if rating < 1 or rating > 5:
        return "Rating must be between 1 and 5.", 400

    # Save photo
    photo_filename = None

    if photo and photo.filename:
        filename = secure_filename(photo.filename)

        # Add timestamp to avoid duplicate filenames
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

        photo_filename = timestamp + "_" + filename

        upload_folder = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "uploads"
        )

        os.makedirs(upload_folder, exist_ok=True)

        photo.save(
            os.path.join(
                upload_folder,
                photo_filename
            )
        )

    conn = get_db()

    try:
        conn.execute("""
            INSERT INTO reviews
            (
                patient_name,
                rating,
                comment,
                photo,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            patient_name,
            rating,
            comment,
            photo_filename,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))

        conn.commit()

    except Exception as e:
        conn.rollback()
        print("REVIEW DATABASE ERROR:", e)
        return "Database error: " + str(e), 500

    finally:
        conn.close()

    return redirect(url_for("home"))

@app.route("/admin/gallery/add", methods=["POST"])
def add_gallery_item():

    # Only logged-in doctor/admin can add gallery items
    if "admin_logged_in" not in session:
        return redirect(url_for("admin_login"))

    title = request.form.get("title", "").strip()
    category = request.form.get("category", "").strip()

    before_photo = request.files.get("before_photo")
    after_photo = request.files.get("after_photo")

    if not title or not category or not before_photo or not after_photo:
        return "Please provide title, category, before photo and after photo.", 400

    upload_folder = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "uploads",
        "before_after"
    )

    os.makedirs(upload_folder, exist_ok=True)

    before_filename = secure_filename(before_photo.filename)
    after_filename = secure_filename(after_photo.filename)

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

    before_filename = "before_" + timestamp + "_" + before_filename
    after_filename = "after_" + timestamp + "_" + after_filename

    before_photo.save(
        os.path.join(upload_folder, before_filename)
    )

    after_photo.save(
        os.path.join(upload_folder, after_filename)
    )

    conn = get_db()

    conn.execute("""
        INSERT INTO before_after
        (title, category, before_photo, after_photo, visible, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        title,
        category,
        before_filename,
        after_filename,
        1,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()

    return redirect(url_for("admin_dashboard"))

@app.route("/admin/media/add", methods=["POST"])
def add_media():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    category = request.form.get("category", "").strip()
    media_type = request.form.get("media_type", "").strip()
    media_file = request.files.get("media_file")

    if not title or not category or not media_type or not media_file:
        return "Please fill in all required fields.", 400

    if media_type not in ["photo", "video"]:
        return "Invalid media type.", 400

    filename = secure_filename(media_file.filename)

    if not filename:
        return "Invalid file.", 400

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    filename = timestamp + "_" + filename

    upload_folder = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "uploads",
        "media"
    )

    os.makedirs(upload_folder, exist_ok=True)

    media_file.save(os.path.join(upload_folder, filename))

    conn = get_db()

    try:
        conn.execute("""
            INSERT INTO media
            (title, description, category, media_type, filename, visible, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            title,
            description,
            category,
            media_type,
            filename,
            1,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))

        conn.commit()

    except Exception as e:
        conn.rollback()
        print("MEDIA DATABASE ERROR:", e)
        return "Database error: " + str(e), 500

    finally:
        conn.close()

    return redirect(url_for("admin_dashboard"))
@app.route("/admin/media/<int:media_id>/visibility", methods=["POST"])
def toggle_media_visibility(media_id):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    conn = get_db()

    item = conn.execute(
        "SELECT visible FROM media WHERE id = ?",
        (media_id,)
    ).fetchone()

    if not item:
        conn.close()
        return "Media item not found", 404

    new_visible = 0 if item["visible"] else 1

    conn.execute(
        "UPDATE media SET visible = ? WHERE id = ?",
        (new_visible, media_id)
    )

    conn.commit()
    conn.close()

    return redirect(url_for("admin_dashboard"))


@app.route("/admin/media/<int:media_id>/delete", methods=["POST"])
def delete_media(media_id):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    conn = get_db()

    item = conn.execute(
        "SELECT filename FROM media WHERE id = ?",
        (media_id,)
    ).fetchone()

    if not item:
        conn.close()
        return "Media item not found", 404

    conn.execute(
        "DELETE FROM media WHERE id = ?",
        (media_id,)
    )

    conn.commit()
    conn.close()

    upload_folder = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "uploads",
        "media"
    )

    filepath = os.path.join(upload_folder, item["filename"])

    if os.path.exists(filepath):
        os.remove(filepath)

    return redirect(url_for("admin_dashboard"))
@app.route("/admin/media/<int:media_id>/edit", methods=["GET", "POST"])
def edit_media(media_id):

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    conn = get_db()

    item = conn.execute(
        "SELECT * FROM media WHERE id = ?",
        (media_id,)
    ).fetchone()

    if not item:
        conn.close()
        return "Media item not found", 404

    if request.method == "POST":

        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        category = request.form.get("category", "").strip()

        if not title or not category:
            conn.close()
            return "Title and category are required.", 400

        conn.execute("""
            UPDATE media
            SET title = ?, description = ?, category = ?
            WHERE id = ?
        """, (
            title,
            description,
            category,
            media_id
        ))

        conn.commit()
        conn.close()

        return redirect(url_for("admin_dashboard"))

    conn.close()

    return render_template(
        "admin/edit_media.html",
        item=item
    )
@app.route("/before-after/<filename>")
def before_after_file(filename):
    upload_folder = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "uploads",
        "before_after"
    )

    return send_from_directory(
        upload_folder,
        filename
    )
@app.route("/admin/gallery/<int:item_id>/visibility", methods=["POST"])
def toggle_gallery_visibility(item_id):

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    conn = get_db()

    item = conn.execute("""
        SELECT visible
        FROM before_after
        WHERE id = ?
    """, (item_id,)).fetchone()

    if item is None:
        conn.close()
        return "Gallery item not found.", 404

    new_visibility = 0 if item["visible"] == 1 else 1

    conn.execute("""
        UPDATE before_after
        SET visible = ?
        WHERE id = ?
    """, (new_visibility, item_id))

    conn.commit()
    conn.close()

    return redirect(url_for("admin_dashboard"))

@app.route("/admin/gallery/<int:item_id>/delete", methods=["POST"])
def delete_gallery_item(item_id):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    conn = get_db()

    item = conn.execute("""
        SELECT before_photo, after_photo
        FROM before_after
        WHERE id = ?
    """, (item_id,)).fetchone()

    if item is None:
        conn.close()
        return "Gallery item not found.", 404

    # Delete the database record
    conn.execute("""
        DELETE FROM before_after
        WHERE id = ?
    """, (item_id,))

    conn.commit()
    conn.close()

    # Delete the uploaded photos from the server
    upload_folder = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "uploads",
        "before_after"
    )

    before_path = os.path.join(upload_folder, item["before_photo"])
    after_path = os.path.join(upload_folder, item["after_photo"])

    if os.path.exists(before_path):
        os.remove(before_path)

    if os.path.exists(after_path):
        os.remove(after_path)

    return redirect(url_for("admin_dashboard"))
@app.post("/api/appointment")
def appointment():

    data = request.get_json(silent=True) or request.form

    patient_name = str(data.get("name", "")).strip()
    phone = str(data.get("phone", "")).strip()
    email = str(data.get("email", "")).strip()
    concern = str(data.get("concern", "")).strip()
    appointment_date = str(data.get("date", "")).strip()
    appointment_time = str(data.get("time", "")).strip()
    message = str(data.get("message", "")).strip()

    if not patient_name or not phone or not concern or not appointment_date:
        return jsonify(
            ok=False,
            message="Please fill in all required fields."
        ), 400

    conn = get_db()

    try:
        conn.execute("""
            INSERT INTO appointments
            (
                patient_name,
                phone,
                email,
                concern,
                appointment_date,
                appointment_time,
                message,
                status,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            patient_name,
            phone,
            email,
            concern,
            appointment_date,
            appointment_time,
            message,
            "PENDING",
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))

        conn.commit()

    except Exception as e:
        conn.rollback()
        print("DATABASE ERROR:", e)
        return jsonify(
            ok=False,
            message="Database error: " + str(e)
        ), 500

    finally:
        conn.close()

    return jsonify(
        ok=True,
        message="Appointment booked successfully!"
    )
# =========================
# ADMIN LOGIN
# =========================

@app.route("/admin", methods=["GET", "POST"])
def admin_login():

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        # Temporary login for testing
        if username == "admin" and password == "ChangeMe123!":
            session["admin_logged_in"] = True
            return redirect(url_for("admin_dashboard"))

        return render_template(
            "admin/login.html",
            error="Invalid username or password."

   
)

    return render_template("admin/login.html")


# =========================
# ADMIN DASHBOARD
# =========================

@app.route("/admin/dashboard")
def admin_dashboard():

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    conn = get_db()

    # ---------------- APPOINTMENTS ----------------

    appointments = conn.execute("""
        SELECT *
        FROM appointments
        ORDER BY appointment_date ASC,
                 appointment_time ASC
    """).fetchall()

    # ---------------- GALLERY ----------------

    gallery_items = conn.execute("""
        SELECT *
        FROM before_after
        ORDER BY id DESC
    """).fetchall()
    media_items = conn.execute("""
    SELECT * FROM media ORDER BY id DESC
""").fetchall()

    print("DASHBOARD APPOINTMENTS:", [dict(a) for a in appointments])

    # ---------------- APPOINTMENT STATUS COUNTS ----------------

    total = conn.execute("""
        SELECT COUNT(*)
        FROM appointments
    """).fetchone()[0]

    pending = conn.execute("""
        SELECT COUNT(*)
        FROM appointments
        WHERE status = 'PENDING'
    """).fetchone()[0]

    confirmed = conn.execute("""
        SELECT COUNT(*)
        FROM appointments
        WHERE status = 'CONFIRMED'
    """).fetchone()[0]

    cancelled = conn.execute("""
        SELECT COUNT(*)
        FROM appointments
        WHERE status = 'CANCELLED'
    """).fetchone()[0]

    completed = conn.execute("""
        SELECT COUNT(*)
        FROM appointments
        WHERE status = 'COMPLETED'
    """).fetchone()[0]

    # ---------------- ANALYTICS ----------------

    today = datetime.now().strftime("%Y-%m-%d")

    # Today's appointments
    today_count = conn.execute("""
        SELECT COUNT(*)
        FROM appointments
        WHERE appointment_date = ?
    """, (today,)).fetchone()[0]

    # This week's appointments
    week_count = conn.execute("""
        SELECT COUNT(*)
        FROM appointments
        WHERE appointment_date >= date('now', '-6 days')
        AND appointment_date <= date('now')
    """).fetchone()[0]

    # This month's appointments
    month_count = conn.execute("""
        SELECT COUNT(*)
        FROM appointments
        WHERE strftime('%Y-%m', appointment_date)
              = strftime('%Y-%m', 'now')
    """).fetchone()[0]

    # ---------------- CLOSE DATABASE ----------------

    conn.close()

    # ---------------- SEND DATA TO DASHBOARD ----------------

    return render_template(
        "admin/dashboard.html",
        appointments=appointments,
        total=total,
        pending=pending,
        confirmed=confirmed,
        cancelled=cancelled,
        completed=completed,
        gallery_items=gallery_items,
        media_items=media_items,
        today_count=today_count,
        week_count=week_count,
        month_count=month_count
    )

# =========================
# UPDATE APPOINTMENT STATUS
# =========================

@app.route(
    "/admin/appointment/<int:appointment_id>/status",
    methods=["POST"]
)
def update_status(appointment_id):

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    status = request.form.get("status", "").strip()

    allowed_statuses = [
        "PENDING",
        "CONFIRMED",
        "RESCHEDULED",
        "CANCELLED",
        "COMPLETED"
    ]

    if status not in allowed_statuses:
        return "Invalid status", 400

    rescheduled_date = request.form.get(
        "rescheduled_date", ""
    ).strip()

    rescheduled_time = request.form.get(
        "rescheduled_time", ""
    ).strip()

    # If appointment is being rescheduled,
    # doctor must provide new date and time
    if status == "RESCHEDULED":

        if not rescheduled_date:
            return "Please select a new appointment date.", 400

        if not rescheduled_time:
            return "Please select a new appointment time.", 400

    conn = get_db()

    try:

        if status == "RESCHEDULED":

            conn.execute("""
                UPDATE appointments
                SET status = ?,
                    rescheduled_date = ?,
                    rescheduled_time = ?
                WHERE id = ?
            """, (
                status,
                rescheduled_date,
                rescheduled_time,
                appointment_id
            ))

        else:

            conn.execute("""
                UPDATE appointments
                SET status = ?
                WHERE id = ?
            """, (
                status,
                appointment_id
            ))

        conn.commit()

    except Exception as e:

        conn.rollback()
        print("STATUS UPDATE ERROR:", e)
        return "Database error: " + str(e), 500

    finally:

        conn.close()

    return redirect(url_for("admin_dashboard"))

# =========================
# PATIENT RECORDS
# =========================

@app.route("/admin/patients")
def admin_patients():

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    conn = get_db()

    patients = conn.execute("""
        SELECT *
        FROM patients
        ORDER BY patient_name ASC
    """).fetchall()

    conn.close()

    return render_template(
        "admin/patients.html",
        patients=patients
    )

# =========================
# ADD PATIENT
# =========================

@app.route("/admin/patients/add", methods=["GET", "POST"])
def add_patient():

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    if request.method == "POST":

        patient_name = request.form.get("patient_name")
        phone = request.form.get("phone")
        email = request.form.get("email")
        date_of_birth = request.form.get("date_of_birth")
        gender = request.form.get("gender")
        address = request.form.get("address")
        medical_notes = request.form.get("medical_notes")

        conn = get_db()

        conn.execute("""
            INSERT INTO patients
            (
                patient_name,
                phone,
                email,
                date_of_birth,
                gender,
                address,
                medical_notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            patient_name,
            phone,
            email,
            date_of_birth,
            gender,
            address,
            medical_notes
        ))

        conn.commit()
        conn.close()

        return redirect(url_for("admin_patients"))

    return render_template("admin/add_patient.html")
# =========================
# ADMIN LOGOUT
# =========================

@app.route("/admin/logout")
def admin_logout():

    session.clear()

    return redirect(url_for("admin_login"))


@app.route("/booking-success")
def booking_success():

    return """
    <html>
    <head>
        <title>Appointment Requested</title>
    </head>

    <body style="font-family:Arial;text-align:center;padding:80px">

        <h1>Appointment Request Received ✓</h1>

        <p>Thank you for choosing Sri Danwandhri Clinic.</p>

        <p>Your appointment request has been sent to the clinic.</p>

        <a href="/">Return to Website</a>

    </body>
    </html>
    """
print("DATABASE FILE:", os.path.abspath(DATABASE))
if __name__ == "__main__":
    init_db()
    app.run(debug=True)
