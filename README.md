# Smart Hostel Attendance System

A smartphone-based hostel attendance system using Flask, SQLite, QR Code, smartphone camera, OpenCV, HTML, CSS and JavaScript.

## Features

- Admin login
- Student login
- Admin dashboard
- Student dashboard
- Dynamic QR attendance with 60-second expiry
- Smartphone camera face capture
- OpenCV face detection
- Attendance records
- Room management
- Leave management
- Attendance reports
- Responsive UI
- Gunicorn deployment support

## Run locally

```bash
python -m venv venv
```

Windows PowerShell:

```powershell
venv\Scripts\activate
```

If PowerShell blocks activation:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
venv\Scripts\activate
```

Install:

```bash
pip install -r requirements.txt
```

Run:

```bash
python app.py
```

Open http://127.0.0.1:5000

## Demo accounts

Admin:
- ID: ADMIN
- Password: admin123

Student:
- ID: STU001
- Password: student123

Other sample students:
- STU002 / student123
- STU003 / student123

## Important

This demo uses plain-text passwords to keep the college-project code easy to understand. Before production deployment, use password hashing, a strong SECRET_KEY, HTTPS, secure database storage, and proper biometric privacy/security controls.

The face feature currently performs face detection/capture. It does not perform identity recognition.
