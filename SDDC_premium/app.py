from dotenv import load_dotenv

load_dotenv()
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    jsonify,
    session,
    send_from_directory
)

import os
from datetime import datetime, timedelta

import psycopg
from psycopg.rows import dict_row

from werkzeug.utils import secure_filename

DATABASE_URL = os.environ.get("DATABASE_URL")
app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "sri-danwandhri-development-key"
)

DATABASE_URL = os.environ.get("DATABASE_URL")


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_db():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not configured")

    return psycopg.connect(
        DATABASE_URL,
        row_factory=dict_row
    )


# =========================================================
# HOME PAGE
# =========================================================

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
        SELECT *
        FROM media
        WHERE visible = 1
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    return render_template(
        "index.html",
        reviews=reviews,
        gallery_items=gallery_items,
        media_items=media_items
    )


# =========================================================
# UPLOADED FILES
# =========================================================

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


# =========================================================
# SUBMIT REVIEW
# =========================================================

@app.route("/submit-review", methods=["POST"])
def submit_review():

    patient_name = request.form.get(
        "patient_name",
        ""
    ).strip()

    rating = request.form.get(
        "rating",
        ""
    ).strip()

    comment = request.form.get(
        "comment",
        ""
    ).strip()

    photo = request.files.get("photo")

    if not patient_name or not rating or not comment:
        return "Please fill in your name, rating and review.", 400

    try:
        rating = int(rating)

    except ValueError:
        return "Invalid rating.", 400

    if rating < 1 or rating > 5:
        return "Rating must be between 1 and 5.", 400

    photo_filename = None

    if photo and photo.filename:

        filename = secure_filename(photo.filename)

        timestamp = datetime.now().strftime(
            "%Y%m%d%H%M%S"
        )

        photo_filename = (
            timestamp + "_" + filename
        )

        upload_folder = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "uploads"
        )

        os.makedirs(
            upload_folder,
            exist_ok=True
        )

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
            VALUES (%s, %s, %s, %s, %s)
        """, (
            patient_name,
            rating,
            comment,
            photo_filename,
            datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        ))

        conn.commit()

    except Exception as e:

        conn.rollback()

        print(
            "REVIEW DATABASE ERROR:",
            e
        )

        return (
            "Database error: " + str(e),
            500
        )

    finally:

        conn.close()

    return redirect(url_for("home"))


# =========================================================
# ADD GALLERY ITEM
# =========================================================

@app.route("/admin/gallery/add", methods=["POST"])
def add_gallery_item():

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    title = request.form.get(
        "title",
        ""
    ).strip()

    category = request.form.get(
        "category",
        ""
    ).strip()

    before_photo = request.files.get(
        "before_photo"
    )

    after_photo = request.files.get(
        "after_photo"
    )

    if (
        not title
        or not category
        or not before_photo
        or not after_photo
    ):
        return (
            "Please provide title, category, "
            "before photo and after photo.",
            400
        )

    upload_folder = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "uploads",
        "before_after"
    )

    os.makedirs(
        upload_folder,
        exist_ok=True
    )

    before_filename = secure_filename(
        before_photo.filename
    )

    after_filename = secure_filename(
        after_photo.filename
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d%H%M%S"
    )

    before_filename = (
        "before_"
        + timestamp
        + "_"
        + before_filename
    )

    after_filename = (
        "after_"
        + timestamp
        + "_"
        + after_filename
    )

    before_photo.save(
        os.path.join(
            upload_folder,
            before_filename
        )
    )

    after_photo.save(
        os.path.join(
            upload_folder,
            after_filename
        )
    )

    conn = get_db()

    try:

        conn.execute("""
            INSERT INTO before_after
            (
                title,
                category,
                before_photo,
                after_photo,
                visible,
                created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            title,
            category,
            before_filename,
            after_filename,
            1,
            datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        ))

        conn.commit()

    finally:

        conn.close()

    return redirect(
        url_for("admin_dashboard")
    )


# =========================================================
# ADD MEDIA
# =========================================================

@app.route("/admin/media/add", methods=["POST"])
def add_media():

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    title = request.form.get(
        "title",
        ""
    ).strip()

    description = request.form.get(
        "description",
        ""
    ).strip()

    category = request.form.get(
        "category",
        ""
    ).strip()

    media_type = request.form.get(
        "media_type",
        ""
    ).strip()

    media_file = request.files.get(
        "media_file"
    )

    if (
        not title
        or not category
        or not media_type
        or not media_file
    ):
        return (
            "Please fill in all required fields.",
            400
        )

    if media_type not in [
        "photo",
        "video"
    ]:
        return "Invalid media type.", 400

    filename = secure_filename(
        media_file.filename
    )

    if not filename:
        return "Invalid file.", 400

    timestamp = datetime.now().strftime(
        "%Y%m%d%H%M%S"
    )

    filename = (
        timestamp + "_" + filename
    )

    upload_folder = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "uploads",
        "media"
    )

    os.makedirs(
        upload_folder,
        exist_ok=True
    )

    media_file.save(
        os.path.join(
            upload_folder,
            filename
        )
    )

    conn = get_db()

    try:

        conn.execute("""
            INSERT INTO media
            (
                title,
                description,
                category,
                media_type,
                filename,
                visible,
                created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            title,
            description,
            category,
            media_type,
            filename,
            1,
            datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        ))

        conn.commit()

    except Exception as e:

        conn.rollback()

        print(
            "MEDIA DATABASE ERROR:",
            e
        )

        return (
            "Database error: " + str(e),
            500
        )

    finally:

        conn.close()

    return redirect(
        url_for("admin_dashboard")
    )


# =========================================================
# TOGGLE MEDIA VISIBILITY
# =========================================================

@app.route(
    "/admin/media/<int:media_id>/visibility",
    methods=["POST"]
)
def toggle_media_visibility(media_id):

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    conn = get_db()

    item = conn.execute(
        """
        SELECT visible
        FROM media
        WHERE id = %s
        """,
        (media_id,)
    ).fetchone()

    if not item:

        conn.close()

        return (
            "Media item not found",
            404
        )

    new_visible = (
        0 if item["visible"] else 1
    )

    conn.execute(
        """
        UPDATE media
        SET visible = %s
        WHERE id = %s
        """,
        (
            new_visible,
            media_id
        )
    )

    conn.commit()
    conn.close()

    return redirect(
        url_for("admin_dashboard")
    )


# =========================================================
# DELETE MEDIA
# =========================================================

@app.route(
    "/admin/media/<int:media_id>/delete",
    methods=["POST"]
)
def delete_media(media_id):

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    conn = get_db()

    item = conn.execute(
        """
        SELECT filename
        FROM media
        WHERE id = %s
        """,
        (media_id,)
    ).fetchone()

    if not item:

        conn.close()

        return (
            "Media item not found",
            404
        )

    conn.execute(
        """
        DELETE FROM media
        WHERE id = %s
        """,
        (media_id,)
    )

    conn.commit()
    conn.close()

    upload_folder = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "uploads",
        "media"
    )

    filepath = os.path.join(
        upload_folder,
        item["filename"]
    )

    if os.path.exists(filepath):
        os.remove(filepath)

    return redirect(
        url_for("admin_dashboard")
    )


# =========================================================
# EDIT MEDIA
# =========================================================

@app.route(
    "/admin/media/<int:media_id>/edit",
    methods=["GET", "POST"]
)
def edit_media(media_id):

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    conn = get_db()

    item = conn.execute(
        """
        SELECT *
        FROM media
        WHERE id = %s
        """,
        (media_id,)
    ).fetchone()

    if not item:

        conn.close()

        return (
            "Media item not found",
            404
        )

    if request.method == "POST":

        title = request.form.get(
            "title",
            ""
        ).strip()

        description = request.form.get(
            "description",
            ""
        ).strip()

        category = request.form.get(
            "category",
            ""
        ).strip()

        if not title or not category:

            conn.close()

            return (
                "Title and category are required.",
                400
            )

        conn.execute(
            """
            UPDATE media
            SET
                title = %s,
                description = %s,
                category = %s
            WHERE id = %s
            """,
            (
                title,
                description,
                category,
                media_id
            )
        )

        conn.commit()
        conn.close()

        return redirect(
            url_for("admin_dashboard")
        )

    conn.close()

    return render_template(
        "admin/edit_media.html",
        item=item
    )


# =========================================================
# BEFORE / AFTER FILE
# =========================================================

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


# =========================================================
# TOGGLE GALLERY VISIBILITY
# =========================================================

@app.route(
    "/admin/gallery/<int:item_id>/visibility",
    methods=["POST"]
)
def toggle_gallery_visibility(item_id):

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    conn = get_db()

    item = conn.execute(
        """
        SELECT visible
        FROM before_after
        WHERE id = %s
        """,
        (item_id,)
    ).fetchone()

    if item is None:

        conn.close()

        return (
            "Gallery item not found.",
            404
        )

    new_visibility = (
        0 if item["visible"] == 1 else 1
    )

    conn.execute(
        """
        UPDATE before_after
        SET visible = %s
        WHERE id = %s
        """,
        (
            new_visibility,
            item_id
        )
    )

    conn.commit()
    conn.close()

    return redirect(
        url_for("admin_dashboard")
    )


# =========================================================
# DELETE GALLERY ITEM
# =========================================================

@app.route(
    "/admin/gallery/<int:item_id>/delete",
    methods=["POST"]
)
def delete_gallery_item(item_id):

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    conn = get_db()

    item = conn.execute(
        """
        SELECT before_photo, after_photo
        FROM before_after
        WHERE id = %s
        """,
        (item_id,)
    ).fetchone()

    if item is None:

        conn.close()

        return (
            "Gallery item not found.",
            404
        )

    conn.execute(
        """
        DELETE FROM before_after
        WHERE id = %s
        """,
        (item_id,)
    )

    conn.commit()
    conn.close()

    upload_folder = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "uploads",
        "before_after"
    )

    before_path = os.path.join(
        upload_folder,
        item["before_photo"]
    )

    after_path = os.path.join(
        upload_folder,
        item["after_photo"]
    )

    if os.path.exists(before_path):
        os.remove(before_path)

    if os.path.exists(after_path):
        os.remove(after_path)

    return redirect(
        url_for("admin_dashboard")
    )


# =========================================================
# APPOINTMENT API
# =========================================================

@app.post("/api/appointment")
def appointment():

    data = (
        request.get_json(silent=True)
        or request.form
    )

    patient_name = str(
        data.get("name", "")
    ).strip()

    phone = str(
        data.get("phone", "")
    ).strip()

    email = str(
        data.get("email", "")
    ).strip()

    concern = str(
        data.get("concern", "")
    ).strip()

    appointment_date = str(
        data.get("date", "")
    ).strip()

    appointment_time = str(
        data.get("time", "")
    ).strip()

    message = str(
        data.get("message", "")
    ).strip()

    if (
        not patient_name
        or not phone
        or not concern
        or not appointment_date
    ):
        return jsonify(
            ok=False,
            message="Please fill in all required fields."
        ), 400

    conn = get_db()

    try:

        conn.execute(
            """
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
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                patient_name,
                phone,
                email,
                concern,
                appointment_date,
                appointment_time,
                message,
                "PENDING",
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            )
        )

        conn.commit()

    except Exception as e:

        conn.rollback()

        print(
            "DATABASE ERROR:",
            e
        )

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


# =========================================================
# ADMIN LOGIN
# =========================================================
@app.route("/admin", methods=["GET", "POST"])
def admin_login():

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        admin_username = os.getenv("ADMIN_USERNAME", "admin")
        admin_password = os.getenv("ADMIN_PASSWORD", "")

        if username == admin_username and password == admin_password:

            session["admin_logged_in"] = True

            return redirect(url_for("admin_dashboard"))

        return render_template(
            "admin/login.html",
            error="Invalid username or password."
        )

    return render_template("admin/login.html")


# =========================================================
# ADMIN DASHBOARD
# =========================================================

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

    # ---------------- MEDIA ----------------

    media_items = conn.execute("""
        SELECT *
        FROM media
        ORDER BY id DESC
    """).fetchall()

    print(
        "DASHBOARD APPOINTMENTS:",
        [dict(a) for a in appointments]
    )

    # ---------------- APPOINTMENT STATUS COUNTS ----------------

    total = conn.execute("""
        SELECT COUNT(*) AS count
        FROM appointments
    """).fetchone()["count"]

    pending = conn.execute("""
        SELECT COUNT(*) AS count
        FROM appointments
        WHERE status = 'PENDING'
    """).fetchone()["count"]

    confirmed = conn.execute("""
        SELECT COUNT(*) AS count
        FROM appointments
        WHERE status = 'CONFIRMED'
    """).fetchone()["count"]

    cancelled = conn.execute("""
        SELECT COUNT(*) AS count
        FROM appointments
        WHERE status = 'CANCELLED'
    """).fetchone()["count"]

    completed = conn.execute("""
        SELECT COUNT(*) AS count
        FROM appointments
        WHERE status = 'COMPLETED'
    """).fetchone()["count"]

    # ---------------- ANALYTICS ----------------

    today = datetime.now().date()

    today_str = today.strftime(
        "%Y-%m-%d"
    )

    week_start_str = (
        today - timedelta(days=6)
    ).strftime("%Y-%m-%d")

    month_start_str = (
        today.replace(day=1)
    ).strftime("%Y-%m-%d")

    next_month_str = (
        (
            today.replace(day=1)
            + timedelta(days=32)
        )
        .replace(day=1)
        .strftime("%Y-%m-%d")
    )

    # ---------------- TODAY ----------------

    today_count = conn.execute("""
        SELECT COUNT(*) AS count
        FROM appointments
        WHERE appointment_date = %s
    """, (
        today_str,
    )).fetchone()["count"]

    # ---------------- THIS WEEK ----------------

    week_count = conn.execute("""
        SELECT COUNT(*) AS count
        FROM appointments
        WHERE appointment_date >= %s
          AND appointment_date <= %s
    """, (
        week_start_str,
        today_str
    )).fetchone()["count"]

    # ---------------- THIS MONTH ----------------

    month_count = conn.execute("""
        SELECT COUNT(*) AS count
        FROM appointments
        WHERE appointment_date >= %s
          AND appointment_date < %s
    """, (
        month_start_str,
        next_month_str
    )).fetchone()["count"]

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


# =========================================================
# UPDATE APPOINTMENT STATUS
# =========================================================

@app.route(
    "/admin/appointment/<int:appointment_id>/status",
    methods=["POST"]
)
def update_status(appointment_id):

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    status = request.form.get(
        "status",
        ""
    ).strip()

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
        "rescheduled_date",
        ""
    ).strip()

    rescheduled_time = request.form.get(
        "rescheduled_time",
        ""
    ).strip()

    if status == "RESCHEDULED":

        if not rescheduled_date:
            return (
                "Please select a new appointment date.",
                400
            )

        if not rescheduled_time:
            return (
                "Please select a new appointment time.",
                400
            )

    conn = get_db()

    try:

        if status == "RESCHEDULED":

            conn.execute("""
                UPDATE appointments
                SET
                    status = %s,
                    rescheduled_date = %s,
                    rescheduled_time = %s
                WHERE id = %s
            """, (
                status,
                rescheduled_date,
                rescheduled_time,
                appointment_id
            ))

        else:

            conn.execute("""
                UPDATE appointments
                SET status = %s
                WHERE id = %s
            """, (
                status,
                appointment_id
            ))

        conn.commit()

    except Exception as e:

        conn.rollback()

        print(
            "STATUS UPDATE ERROR:",
            e
        )

        return (
            "Database error: " + str(e),
            500
        )

    finally:

        conn.close()

    return redirect(
        url_for("admin_dashboard")
    )


# =========================================================
# PATIENT RECORDS
# =========================================================

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


# =========================================================
# ADD PATIENT
# =========================================================

@app.route(
    "/admin/patients/add",
    methods=["GET", "POST"]
)
def add_patient():

    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    if request.method == "POST":

        patient_name = request.form.get(
            "patient_name"
        )

        phone = request.form.get(
            "phone"
        )

        email = request.form.get(
            "email"
        )

        date_of_birth = request.form.get(
            "date_of_birth"
        )

        gender = request.form.get(
            "gender"
        )

        address = request.form.get(
            "address"
        )

        medical_notes = request.form.get(
            "medical_notes"
        )

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
            VALUES (%s, %s, %s, %s, %s, %s, %s)
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

        return redirect(
            url_for("admin_patients")
        )

    return render_template(
        "admin/add_patient.html"
    )


# =========================================================
# ADMIN LOGOUT
# =========================================================

@app.route("/admin/logout")
def admin_logout():

    session.clear()

    return redirect(
        url_for("admin_login")
    )


# =========================================================
# BOOKING SUCCESS
# =========================================================

@app.route("/booking-success")
def booking_success():

    return """
    <html>
    <head>
        <title>Appointment Requested</title>
    </head>

    <body style="font-family:Arial;text-align:center;padding:80px">

        <h1>Appointment Request Received ✓</h1>

        <p>
            Thank you for choosing Sri Danwandhri Clinic.
        </p>

        <p>
            Your appointment request has been sent to the clinic.
        </p>

        <a href="/">
            Return to Website
        </a>

    </body>
    </html>
    """


# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":
    app.run(debug=True)