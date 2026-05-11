from email.mime.text import MIMEText
import smtplib
from flask import Flask, render_template, request, redirect, session, url_for, flash, jsonify
import mysql.connector
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
from twilio.rest import Client
from dotenv import load_dotenv
import os


# ================= LOAD ENV =================
load_dotenv()

# ================= FLASK APP =================
app = Flask(__name__)
app.secret_key = "supersecretkey"

# ================= DATABASE =================
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="Kishore@2210",
        database="her_voice"
    )

# ================= UPLOAD FOLDERS =================
UPLOAD_EVIDENCE = "static/uploads/evidence"
UPLOAD_VOICE = "static/uploads/voice"

os.makedirs(UPLOAD_EVIDENCE, exist_ok=True)
os.makedirs(UPLOAD_VOICE, exist_ok=True)

app.config["UPLOAD_EVIDENCE"] = UPLOAD_EVIDENCE
app.config["UPLOAD_VOICE"] = UPLOAD_VOICE

# ================= TWILIO CONFIG =================
TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_NUMBER = os.getenv("TWILIO_NUMBER")
TARGET_NUMBER = os.getenv("TARGET_NUMBER")

# ================= DECORATORS =================
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("user_login"))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "admin_id" not in session:
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated

# ================= HOME =================
@app.route("/")
def home():
    return redirect(url_for("user_login"))


# ================= USER SIGNUP =================
@app.route("/user_signup", methods=["GET", "POST"])
def user_signup():

    if request.method == "POST":

        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        hashed_password = generate_password_hash(
            request.form["password"]
        )

        cursor.execute(
            "SELECT * FROM users WHERE mobile=%s OR email=%s",
            (request.form["mobile"], request.form["email"])
        )

        existing_user = cursor.fetchone()

        if existing_user:
            flash("User already registered!", "danger")
            return redirect(url_for("user_signup"))

        cursor.execute("""
            INSERT INTO users
            (name, mobile, dob, aadhaar, email, password)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            request.form["name"],
            request.form["mobile"],
            request.form["dob"],
            request.form["aadhaar"],
            request.form["email"],
            hashed_password
        ))

        db.commit()

        cursor.close()
        db.close()

        flash("Account created successfully!", "success")

        return redirect(url_for("user_login"))

    return render_template("user_signup.html")

# ================= USER LOGIN =================
@app.route("/user_login", methods=["GET", "POST"])
def user_login():

    error = None

    if request.method == "POST":

        mobile = request.form.get("mobile")
        password = request.form.get("password")

        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        cursor.execute(
            "SELECT * FROM users WHERE mobile=%s",
            (mobile,)
        )

        user = cursor.fetchone()

        cursor.close()
        db.close()

        if not user:
            error = "User not registered"

        elif not check_password_hash(user["password"], password):
            error = "Invalid password"

        else:
            session["user_id"] = user["id"]
            session["name"] = user["name"]

            return redirect(url_for("user_dashboard"))

    return render_template("user_login.html", error=error)

# ================= USER DASHBOARD =================
@app.route("/user_dashboard")
@login_required
def user_dashboard():
    return render_template(
        "user_dashboard.html",
        name=session["name"]
    )

# ================= COMPLAINT =================
@app.route("/complaint", methods=["GET", "POST"])
@login_required
def complaint():

    if request.method == "POST":

        user_id = session["user_id"]

        complaint_type = request.form.get("complaint_type")
        incident_date = request.form.get("incident_date")
        location = request.form.get("location")
        description = request.form.get("description")

        if not complaint_type or not incident_date or not location or not description:
            flash("Please fill all details!", "danger")
            return redirect(url_for("complaint"))

        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        # FILES
        evidence_files = request.files.getlist("evidence_files")

        saved_files = []

        for file in evidence_files:

            if file and file.filename:

                filename = secure_filename(file.filename)

                unique_name = f"{datetime.now().timestamp()}_{filename}"

                file.save(
                    os.path.join(
                        app.config["UPLOAD_EVIDENCE"],
                        unique_name
                    )
                )

                saved_files.append(unique_name)

        evidence_string = ",".join(saved_files)

        cursor.execute("""
            INSERT INTO complaints
            (
                user_id,
                complaint_type,
                incident_date,
                location,
                description,
                evidence_files,
                voice_file,
                status
            )
            VALUES
            (%s,%s,%s,%s,%s,%s,%s,'Pending')
        """, (
            user_id,
            complaint_type,
            incident_date,
            location,
            description,
            evidence_string,
            request.form.get("voice_file_name")
        ))

        db.commit()

        cursor.close()
        db.close()

        flash("Complaint submitted successfully!", "success")

        return redirect(url_for("user_dashboard"))

    return render_template("complaint.html")

# ================= VOICE UPLOAD =================
@app.route("/upload_voice", methods=["POST"])
def upload_voice():

    voice = request.files["voice"]

    filename = f"voice_{datetime.now().timestamp()}.webm"

    save_path = os.path.join(
        app.config["UPLOAD_VOICE"],
        filename
    )

    voice.save(save_path)

    return {"file_name": filename}

# ================= FEEDBACK PAGE =================
@app.route("/user_feedback")
@login_required
def user_feedback():
    return render_template("feedback.html")

# ================= SAFETY GUIDE =================
@app.route("/safety_guide")
def safety_guide():
    return render_template("safety_guide.html")

# ================= SUBMIT FEEDBACK =================
@app.route("/submit_feedback", methods=["POST"])
@login_required
def submit_feedback():

    user_id = session["user_id"]

    category = request.form.get("category")
    message = request.form.get("message")
    rating = request.form.get("rating")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        INSERT INTO feedback
        (user_id, category, message, rating)
        VALUES (%s,%s,%s,%s)
    """, (
        user_id,
        category,
        message,
        rating
    ))

    conn.commit()

    cursor.close()
    conn.close()

    flash("Feedback submitted successfully!", "success")

    return redirect(url_for("user_dashboard"))

# ================= ADMIN LOGIN =================
@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():

    error = None

    if request.method == "POST":

        db = get_db_connection()

        cursor = db.cursor(dictionary=True)

        cursor.execute(
            "SELECT * FROM admin_login WHERE admin_name=%s",
            (request.form["admin_name"],)
        )

        admin = cursor.fetchone()

        cursor.close()
        db.close()

        if admin and request.form["password"] == admin["password"]:

            session["admin_id"] = admin["id"]

            return redirect(url_for("admin_dashboard"))

        else:
            error = "Invalid Admin Credentials"

    return render_template(
        "admin_login.html",
        error=error
    )

# ================= ADMIN DASHBOARD =================
@app.route("/admin_dashboard")
@admin_required
def admin_dashboard():

    conn = get_db_connection()

    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM complaints")
    total = cursor.fetchall()

    cursor.execute(
        "SELECT * FROM complaints WHERE status='Pending'"
    )
    pending = cursor.fetchall()

    cursor.execute(
        "SELECT * FROM complaints WHERE status='Under Review'"
    )
    review = cursor.fetchall()

    cursor.execute(
        "SELECT * FROM complaints WHERE status='Resolved'"
    )
    resolved = cursor.fetchall()

    cursor.execute("""
        SELECT feedback.*, users.name, users.mobile
        FROM feedback
        JOIN users ON feedback.user_id = users.id
    """)

    feedback_list = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "admin_dashboard.html",
        total=total,
        pending=pending,
        review=review,
        resolved=resolved,
        feedback_list=feedback_list
    )

# ================= ADMIN FEEDBACK =================
@app.route("/admin_feedback")
@admin_required
def admin_feedback():

    conn = get_db_connection()

    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT feedback.*, users.name, users.mobile
        FROM feedback
        JOIN users ON feedback.user_id = users.id
    """)

    feedback_list = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "admin_feedback.html",
        feedback_list=feedback_list
    )

# ================= SOLVE FEEDBACK =================
@app.route("/solve_feedback/<int:feedback_id>")
@admin_required
def solve_feedback(feedback_id):

    conn = get_db_connection()

    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        UPDATE feedback
        SET status='Solved'
        WHERE id=%s
    """, (feedback_id,))

    conn.commit()

    cursor.close()
    conn.close()

    flash("Feedback marked as solved!", "success")

    return redirect(url_for("admin_feedback"))

# ================= PENDING =================
@app.route("/pending_complaints")
@admin_required
def pending_complaints():

    conn = get_db_connection()

    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT * FROM complaints
        WHERE status='Pending'
    """)

    complaints = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "pending_complaints.html",
        complaints=complaints
    )

# ================= REVIEW =================
@app.route("/review_complaints")
@admin_required
def review_complaints():

    conn = get_db_connection()

    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT * FROM complaints
        WHERE status='Under Review'
    """)

    complaints = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "review_complaints.html",
        complaints=complaints
    )

# ================= RESOLVED =================
@app.route("/resolved_complaints")
@admin_required
def resolved_complaints():

    conn = get_db_connection()

    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT * FROM complaints
        WHERE status='Resolved'
    """)

    complaints = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "resolved_complaints.html",
        complaints=complaints
    )

# ================= VIEW COMPLAINT =================
@app.route("/complaint/<int:complaint_id>")
@admin_required
def view_complaint(complaint_id):

    conn = get_db_connection()

    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT complaints.*, users.mobile
        FROM complaints
        JOIN users ON complaints.user_id = users.id
        WHERE complaints.id=%s
    """, (complaint_id,))

    complaint = cursor.fetchone()

    cursor.close()
    conn.close()

    return render_template(
        "view_complaint.html",
        complaint=complaint
    )

# ================= UPDATE STATUS =================
@app.route("/update_status/<int:complaint_id>/<status>")
@admin_required
def update_status(complaint_id, status):

    db = get_db_connection()

    cursor = db.cursor(dictionary=True)

    cursor.execute(
        "SELECT status FROM complaints WHERE id=%s",
        (complaint_id,)
    )

    complaint = cursor.fetchone()

    current_status = complaint["status"]

    if current_status == "Resolved":
        flash("Already resolved!", "warning")
        return redirect(
            url_for(
                "view_complaint",
                complaint_id=complaint_id
            )
        )

    cursor.execute("""
        UPDATE complaints
        SET status=%s
        WHERE id=%s
    """, (
        status,
        complaint_id
    ))

    db.commit()

    cursor.close()
    db.close()

    return redirect(
        url_for(
            "view_complaint",
            complaint_id=complaint_id
        )
    )

# ================= SEND SMS =================
def send_sms_sos(name, phone, location_link):

    try:

        client = Client(
            TWILIO_SID,
            TWILIO_AUTH_TOKEN
        )

        message = client.messages.create(

            body=f"""
🚨 SOS ALERT 🚨

{name} needs immediate help!

📱 Phone: {phone}

📍 Location:
{location_link}

🕒 Time:
{datetime.now().strftime("%d-%m-%Y %H:%M:%S")}
""",

            from_=TWILIO_NUMBER,
            to=TARGET_NUMBER
        )

        print("SMS SENT:", message.sid)

    except Exception as e:
        print("SMS ERROR:", str(e))

# ================= SEND SOS =================
@app.route("/send_sos", methods=["POST"])
@login_required
def send_sos():

    try:

        data = request.get_json()

        lat = data.get("lat")
        lng = data.get("lng")

        if not lat or not lng:
            return jsonify({
                "status": "Location not available"
            })

        location_link = (
            f"https://www.google.com/maps?q={lat},{lng}"
        )

        db = get_db_connection()

        cursor = db.cursor(dictionary=True)

        cursor.execute("""
            SELECT name, mobile
            FROM users
            WHERE id=%s
        """, (session["user_id"],))

        user = cursor.fetchone()

        cursor.close()
        db.close()

        send_sms_sos(
            user["name"],
            user["mobile"],
            location_link
        )

        return jsonify({
            "status": "SMS Sent"
        })

    except Exception as e:

        print("ERROR:", str(e))

        return jsonify({
            "status": "error"
        })

# ================= LOGOUT =================
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("user_login"))

@app.route("/admin_logout")
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))

# ================= RUN =================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

if __name__ == "__main__":
    app.run(debug=True)