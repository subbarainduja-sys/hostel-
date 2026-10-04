import os
import sqlite3
import secrets
import base64
from datetime import datetime, timedelta
from functools import wraps

import cv2
import numpy as np
import qrcode

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, jsonify, flash
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key-in-production")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_DIR = os.path.join(BASE_DIR, "database")
FACE_DIR = os.path.join(BASE_DIR, "face_captures")
os.makedirs(DATABASE_DIR, exist_ok=True)
os.makedirs(FACE_DIR, exist_ok=True)
DATABASE = os.path.join(DATABASE_DIR, "hostel.db")


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT UNIQUE,
            name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'student',
            room_number TEXT,
            department TEXT,
            year TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            method TEXT NOT NULL,
            status TEXT DEFAULT 'Present',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_number TEXT UNIQUE NOT NULL,
            block TEXT NOT NULL,
            capacity INTEGER NOT NULL,
            occupied INTEGER DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS leave_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            from_date TEXT NOT NULL,
            to_date TEXT NOT NULL,
            reason TEXT NOT NULL,
            status TEXT DEFAULT 'Pending',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS qr_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token TEXT UNIQUE NOT NULL,
            expires_at TEXT NOT NULL
        )
    """)

    cursor.execute("SELECT * FROM users WHERE student_id = ?", ("ADMIN",))
    if not cursor.fetchone():
        cursor.execute("""
            INSERT INTO users
            (student_id, name, email, password, role)
            VALUES (?, ?, ?, ?, ?)
        """, ("ADMIN", "Hostel Administrator", "admin@hostel.com", "admin123", "admin"))

    students = [
        ("STU001", "Rahul Kumar", "rahul@example.com", "9876543210",
         "student123", "student", "A-101", "Computer Science", "3"),
        ("STU002", "Priya Sharma", "priya@example.com", "9876543211",
         "student123", "student", "A-102", "Information Technology", "2"),
        ("STU003", "Arun Kumar", "arun@example.com", "9876543212",
         "student123", "student", "B-201", "Computer Science", "3")
    ]

    for student in students:
        try:
            cursor.execute("""
                INSERT INTO users
                (student_id, name, email, phone, password, role,
                 room_number, department, year)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, student)
        except sqlite3.IntegrityError:
            pass

    rooms = [
        ("A-101", "A Block", 4), ("A-102", "A Block", 4),
        ("A-103", "A Block", 4), ("B-201", "B Block", 4),
        ("B-202", "B Block", 4), ("B-203", "B Block", 4)
    ]

    for room in rooms:
        try:
            cursor.execute("""
                INSERT INTO rooms (room_number, block, capacity)
                VALUES (?, ?, ?)
            """, room)
        except sqlite3.IntegrityError:
            pass

    conn.commit()
    conn.close()


def login_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return function(*args, **kwargs)
    return wrapper


def admin_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        if session.get("role") != "admin":
            flash("Admin access required.", "error")
            return redirect(url_for("student_dashboard"))
        return function(*args, **kwargs)
    return wrapper


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        student_id = request.form.get("student_id", "").strip()
        password = request.form.get("password", "")

        conn = get_db()
        user = conn.execute("""
            SELECT * FROM users
            WHERE student_id = ? AND password = ?
        """, (student_id, password)).fetchone()
        conn.close()

        if user:
            session["user_id"] = user["id"]
            session["student_id"] = user["student_id"]
            session["name"] = user["name"]
            session["role"] = user["role"]

            if user["role"] == "admin":
                return redirect(url_for("admin_dashboard"))
            return redirect(url_for("student_dashboard"))

        flash("Invalid Student ID or Password.", "error")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    conn = get_db()
    total_students = conn.execute(
        "SELECT COUNT(*) FROM users WHERE role = 'student'"
    ).fetchone()[0]

    today = datetime.now().strftime("%Y-%m-%d")
    present_today = conn.execute("""
        SELECT COUNT(DISTINCT student_id)
        FROM attendance WHERE date = ?
    """, (today,)).fetchone()[0]

    total_rooms = conn.execute("SELECT COUNT(*) FROM rooms").fetchone()[0]
    leave_pending = conn.execute("""
        SELECT COUNT(*) FROM leave_requests WHERE status = 'Pending'
    """).fetchone()[0]

    recent = conn.execute("""
        SELECT attendance.*, users.name
        FROM attendance
        JOIN users ON attendance.student_id = users.student_id
        ORDER BY attendance.id DESC LIMIT 8
    """).fetchall()
    conn.close()

    return render_template(
        "admin_dashboard.html",
        total_students=total_students,
        present_today=present_today,
        absent_today=max(total_students - present_today, 0),
        total_rooms=total_rooms,
        leave_pending=leave_pending,
        recent=recent
    )


@app.route("/student/dashboard")
@login_required
def student_dashboard():
    if session.get("role") == "admin":
        return redirect(url_for("admin_dashboard"))

    conn = get_db()
    student = conn.execute(
        "SELECT * FROM users WHERE student_id = ?",
        (session["student_id"],)
    ).fetchone()

    attendance_count = conn.execute("""
        SELECT COUNT(*) FROM attendance WHERE student_id = ?
    """, (session["student_id"],)).fetchone()[0]

    present_count = conn.execute("""
        SELECT COUNT(*) FROM attendance
        WHERE student_id = ? AND status = 'Present'
    """, (session["student_id"],)).fetchone()[0]

    recent = conn.execute("""
        SELECT * FROM attendance
        WHERE student_id = ?
        ORDER BY id DESC LIMIT 10
    """, (session["student_id"],)).fetchall()
    conn.close()

    percentage = round(present_count / attendance_count * 100, 2) if attendance_count else 0

    return render_template(
        "student_dashboard.html",
        student=student,
        attendance_count=attendance_count,
        percentage=percentage,
        recent=recent
    )


@app.route("/students")
@admin_required
def students():
    conn = get_db()
    students = conn.execute("""
        SELECT * FROM users
        WHERE role = 'student' ORDER BY name
    """).fetchall()
    conn.close()
    return render_template("students.html", students=students)


@app.route("/students/add", methods=["POST"])
@admin_required
def add_student():
    data = request.form
    try:
        conn = get_db()
        conn.execute("""
            INSERT INTO users
            (student_id, name, email, phone, password, role,
             room_number, department, year)
            VALUES (?, ?, ?, ?, ?, 'student', ?, ?, ?)
        """, (
            data["student_id"], data["name"], data["email"],
            data["phone"], data["password"], data["room_number"],
            data["department"], data["year"]
        ))
        conn.commit()
        conn.close()
        flash("Student added successfully.", "success")
    except sqlite3.IntegrityError:
        flash("Student ID already exists.", "error")
    return redirect(url_for("students"))


@app.route("/attendance")
@admin_required
def attendance():
    conn = get_db()
    records = conn.execute("""
        SELECT attendance.*, users.name, users.room_number
        FROM attendance
        JOIN users ON attendance.student_id = users.student_id
        ORDER BY attendance.id DESC
    """).fetchall()
    conn.close()
    return render_template("attendance.html", records=records)


def record_attendance(student_id, method):
    today = datetime.now().strftime("%Y-%m-%d")
    current_time = datetime.now().strftime("%H:%M:%S")

    conn = get_db()
    existing = conn.execute("""
        SELECT * FROM attendance
        WHERE student_id = ? AND date = ?
    """, (student_id, today)).fetchone()

    if existing:
        conn.close()
        return False, "Attendance already recorded today."

    conn.execute("""
        INSERT INTO attendance
        (student_id, date, time, method, status)
        VALUES (?, ?, ?, ?, 'Present')
    """, (student_id, today, current_time, method))
    conn.commit()
    conn.close()
    return True, "Attendance recorded successfully."


@app.route("/qr-attendance")
@admin_required
def qr_attendance():
    return render_template("qr_attendance.html")


@app.route("/api/generate-qr")
@admin_required
def generate_qr():
    token = secrets.token_urlsafe(24)
    expires = datetime.now() + timedelta(seconds=60)

    conn = get_db()
    conn.execute("DELETE FROM qr_sessions WHERE expires_at < ?",
                 (datetime.now().isoformat(),))
    conn.execute("""
        INSERT INTO qr_sessions (token, expires_at)
        VALUES (?, ?)
    """, (token, expires.isoformat()))
    conn.commit()
    conn.close()

    scan_url = url_for("scan_qr", token=token, _external=True)

    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(scan_url)
    qr.make(fit=True)
    image = qr.make_image()

    import io
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

    return jsonify({
        "image": "data:image/png;base64," + qr_base64,
        "expires_at": expires.strftime("%H:%M:%S")
    })


@app.route("/scan")
@login_required
def scan_qr():
    token = request.args.get("token")
    if not token:
        return "Invalid QR code.", 400

    conn = get_db()
    qr = conn.execute(
        "SELECT * FROM qr_sessions WHERE token = ?",
        (token,)
    ).fetchone()
    conn.close()

    if not qr:
        return "QR code is invalid or expired.", 400

    if datetime.fromisoformat(qr["expires_at"]) < datetime.now():
        return "QR code has expired.", 400

    success, message = record_attendance(session["student_id"], "QR")

    if success:
        return render_template("qr_attendance.html", student_success=message)
    return render_template("qr_attendance.html", student_error=message)


@app.route("/face-attendance")
@login_required
def face_attendance():
    return render_template("face_attendance.html")


@app.route("/api/face-capture", methods=["POST"])
@login_required
def face_capture():
    data = request.get_json()
    if not data or "image" not in data:
        return jsonify({"success": False, "message": "No image received."}), 400

    try:
        image_data = data["image"].split(",")[1]
        image_bytes = base64.b64decode(image_data)
        np_array = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(np_array, cv2.IMREAD_COLOR)

        if frame is None:
            return jsonify({"success": False, "message": "Invalid image."}), 400

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        face_detector = cv2.CascadeClassifier(cascade_path)

        faces = face_detector.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80)
        )

        if len(faces) == 0:
            return jsonify({
                "success": False,
                "message": "No face detected. Please position your face clearly."
            })

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{session['student_id']}_{timestamp}.jpg"
        filepath = os.path.join(FACE_DIR, filename)
        cv2.imwrite(filepath, frame)

        success, message = record_attendance(session["student_id"], "FACE")

        if success:
            return jsonify({
                "success": True,
                "message": "Face captured and attendance recorded."
            })

        return jsonify({"success": False, "message": message})

    except Exception as error:
        print(error)
        return jsonify({
            "success": False,
            "message": "Face processing failed."
        }), 500


@app.route("/rooms")
@admin_required
def rooms():
    conn = get_db()
    rooms = conn.execute(
        "SELECT * FROM rooms ORDER BY room_number"
    ).fetchall()
    conn.close()
    return render_template("rooms.html", rooms=rooms)


@app.route("/leave")
@login_required
def leave():
    conn = get_db()

    if session["role"] == "admin":
        requests = conn.execute("""
            SELECT leave_requests.*, users.name, users.room_number
            FROM leave_requests
            JOIN users ON leave_requests.student_id = users.student_id
            ORDER BY leave_requests.id DESC
        """).fetchall()
    else:
        requests = conn.execute("""
            SELECT * FROM leave_requests
            WHERE student_id = ? ORDER BY id DESC
        """, (session["student_id"],)).fetchall()

    conn.close()
    return render_template("leave.html", requests=requests)


@app.route("/leave/apply", methods=["POST"])
@login_required
def apply_leave():
    conn = get_db()
    conn.execute("""
        INSERT INTO leave_requests
        (student_id, from_date, to_date, reason)
        VALUES (?, ?, ?, ?)
    """, (
        session["student_id"],
        request.form["from_date"],
        request.form["to_date"],
        request.form["reason"]
    ))
    conn.commit()
    conn.close()
    flash("Leave request submitted.", "success")
    return redirect(url_for("leave"))


@app.route("/leave/<int:request_id>/<action>")
@admin_required
def update_leave(request_id, action):
    if action not in ["approve", "reject"]:
        return "Invalid action.", 400

    status = "Approved" if action == "approve" else "Rejected"
    conn = get_db()
    conn.execute(
        "UPDATE leave_requests SET status = ? WHERE id = ?",
        (status, request_id)
    )
    conn.commit()
    conn.close()
    flash(f"Leave request {status.lower()}.", "success")
    return redirect(url_for("leave"))


@app.route("/reports")
@admin_required
def reports():
    conn = get_db()
    records = conn.execute("""
        SELECT attendance.*, users.name, users.room_number, users.department
        FROM attendance
        JOIN users ON attendance.student_id = users.student_id
        ORDER BY attendance.date DESC, attendance.time DESC
    """).fetchall()
    conn.close()
    return render_template("reports.html", records=records)


init_db()

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=True
    )
