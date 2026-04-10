from email.mime import message
from email.mime.text import MIMEText
import smtplib
from flask import Flask, render_template, request, redirect, session, url_for, flash
import mysql.connector
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
from flask import jsonify
from twilio.rest import Client
import os
from dotenv import load_dotenv
import os

load_dotenv()

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
        cursor = db.cursor()

        hashed_password = generate_password_hash(request.form["password"])

        cursor.execute("SELECT * FROM users WHERE mobile=%s OR email=%s",
               (request.form["mobile"], request.form["email"]))
        existing_user = cursor.fetchone()

        if existing_user:
         flash("User already registered!", "danger")
         return redirect(url_for("user_signup"))

        cursor.execute("""
            INSERT INTO users (name, mobile, dob, aadhaar, email, password)
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

        if not mobile or not password:
            error = "All fields are required"
            return render_template("user_login.html", error=error)

        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        cursor.execute("SELECT * FROM users WHERE mobile=%s", (mobile,))
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
    return render_template("user_dashboard.html", name=session["name"])


# ================= SUBMIT COMPLAINT =================
# ================= SUBMIT COMPLAINT =================
@app.route("/complaint", methods=["GET", "POST"])
@login_required
def complaint():

    if request.method == "POST":

        user_id = session.get("user_id")

        if not user_id:
            flash("Session expired. Please login again.", "danger")
            return redirect(url_for("user_login"))

        # ================= GET FORM DATA =================
        complaint_type = request.form.get("complaint_type")
        incident_date = request.form.get("incident_date")
        location = request.form.get("location")
        description = request.form.get("description")

        # ✅ VALIDATION FIRST (VERY IMPORTANT)
        if not complaint_type or not incident_date or not location or not description:
            flash("Please enter all details!", "danger")
            return redirect(url_for("complaint"))

        db = get_db_connection()
        cursor = db.cursor()

        # ✅ CHECK USER EXISTS
        cursor.execute("SELECT id FROM users WHERE id=%s", (user_id,))
        user = cursor.fetchone()

        if not user:
            flash("Invalid user. Please login again.", "danger")
            return redirect(url_for("user_login"))

        # ================= FILE UPLOAD =================
        evidence_files = request.files.getlist("evidence_files")
        saved_files = []

        for file in evidence_files:
            if file and file.filename:
                filename = secure_filename(file.filename)
                unique_name = f"{datetime.now().timestamp()}_{filename}"
                file.save(os.path.join(app.config["UPLOAD_EVIDENCE"], unique_name))
                saved_files.append(unique_name)

        evidence_string = ",".join(saved_files)

        # ================= INSERT =================
        cursor.execute("""
            INSERT INTO complaints
            (user_id, complaint_type, incident_date, location,
             description, evidence_files, voice_file, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'Pending')
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

    save_path = os.path.join(app.config["UPLOAD_VOICE"], filename)

    voice.save(save_path)

    return {"file_name": filename}


# ================= USER FEEDBACK PAGE =================
@app.route("/user_feedback")
@login_required
def user_feedback():
    return render_template("feedback.html")

@app.route('/safety_guide')
def safety_guide():
    return render_template('safety_guide.html')

# ================= SUBMIT FEEDBACK =================
@app.route("/submit_feedback", methods=["POST"])
@login_required
def submit_feedback():

    user_id = session["user_id"]

    category = request.form.get("category")
    message = request.form.get("message")
    rating = request.form.get("rating")

    # ✅ STRONG VALIDATION
    if not category or category.strip() == "" or \
       not message or message.strip() == "" or \
       not rating or rating.strip() == "":
        
        flash("Please fill all details!", "danger")
        return redirect(url_for("user_feedback"))

    try:
        rating = int(rating)
    except:
        flash("Invalid rating!", "danger")
        return redirect(url_for("user_feedback"))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO feedback (user_id, category, message, rating)
        VALUES (%s, %s, %s, %s)
    """, (user_id, category, message, rating))

    conn.commit()
    cursor.close()
    conn.close()

    flash("Feedback submit successfully", "admin_success")
    return redirect(url_for("user_dashboard"))

# ================= SOLVE FEEDBACK =================
@app.route("/solve_feedback/<int:feedback_id>")
@admin_required
def solve_feedback(feedback_id):

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE feedback SET status='Solved' WHERE id=%s
    """, (feedback_id,))

    conn.commit()

    cursor.close()
    conn.close()

    flash("Feedback marked as solved!", "success")

    return redirect(url_for("admin_feedback"))  


# ================= ADMIN LOGIN =================
@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    error = None

    if request.method == "POST":
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        cursor.execute("SELECT * FROM admin_login WHERE admin_name=%s",
                       (request.form["admin_name"],))
        admin = cursor.fetchone()

        cursor.close()
        db.close()

        if admin and request.form["password"] == admin["password"]:
            session["admin_id"] = admin["id"]
            return redirect(url_for("admin_dashboard"))
        else:
            error = "Invalid Admin Credentials"

    return render_template("admin_login.html", error=error)

# ================= ADMIN DASHBOARD =================
@app.route("/admin_dashboard")
@admin_required
def admin_dashboard():

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Complaints
    cursor.execute("SELECT * FROM complaints")
    total = cursor.fetchall()

    cursor.execute("SELECT * FROM complaints WHERE status='Pending'")
    pending = cursor.fetchall()

    cursor.execute("SELECT * FROM complaints WHERE status='Under Review'")
    review = cursor.fetchall()

    cursor.execute("SELECT * FROM complaints WHERE status='Resolved'")
    resolved = cursor.fetchall()

    # Feedback
    cursor.execute("""
    SELECT feedback.*, users.name, users.mobile
    FROM feedback
    JOIN users ON feedback.user_id = users.id
    ORDER BY feedback.created_at DESC
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

    return render_template("admin_feedback.html", feedback_list=feedback_list)

# ================= PENDING COMPLAINTS PAGE =================
@app.route("/pending_complaints")
@admin_required
def pending_complaints():

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM complaints WHERE status='Pending'")
    complaints = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("pending_complaints.html", complaints=complaints)


# ================= REVIEW COMPLAINTS PAGE =================
@app.route("/review_complaints")
@admin_required
def review_complaints():

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM complaints WHERE status='Under Review'")
    complaints = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("review_complaints.html", complaints=complaints)


# ================= RESOLVED COMPLAINTS PAGE =================
@app.route("/resolved_complaints")
@admin_required
def resolved_complaints():

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM complaints WHERE status='Resolved'")
    complaints = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("resolved_complaints.html", complaints=complaints)


# ================= VIEW SINGLE COMPLAINT =================
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

    return render_template("view_complaint.html", complaint=complaint)


# ================= UPDATE STATUS =================
@app.route("/update_status/<int:complaint_id>/<status>")
@admin_required
def update_status(complaint_id, status):

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT status FROM complaints WHERE id=%s", (complaint_id,))
    complaint = cursor.fetchone()

    current_status = complaint["status"]

    # Prevent moving back
    if current_status == "Resolved":
        flash("Complaint already resolved. Cannot change status.", "warning")
        return redirect(url_for("view_complaint", complaint_id=complaint_id))

    if current_status == "Under Review" and status == "Pending":
        flash("Cannot move back to Pending.", "warning")
        return redirect(url_for("view_complaint", complaint_id=complaint_id))

    cursor = db.cursor()

    cursor.execute(
        "UPDATE complaints SET status=%s WHERE id=%s",
        (status, complaint_id)
    )

    db.commit()

    cursor.close()
    db.close()

    return redirect(url_for("view_complaint", complaint_id=complaint_id))


# ================= LOGOUT =================
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("user_login"))


@app.route("/admin_logout")
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))


# from twilio.rest import Client

# ================= TWILIO CONFIG =================
TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_NUMBER = os.getenv("TWILIO_NUMBER")
TARGET_NUMBER = os.getenv("TARGET_NUMBER")

# ================= SEND SMS FUNCTION =================
def send_sms_sos(name, phone, location_link):
    try:
        client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)

        message = client.messages.create(
            body=f"""
🚨 SOS ALERT 🚨

{name} needs immediate help!

📱 Phone: {phone}

📍 Live Location:
{location_link}

🕒 Time: {datetime.now().strftime("%d-%m-%Y %H:%M:%S")}
""",
            from_=TWILIO_NUMBER,
            to=TARGET_NUMBER
        )

        print("✅ SMS SENT:", message.sid)

    except Exception as e:
        print("❌ SMS ERROR:", str(e))


# ================= SOS ROUTE =================
@app.route('/send_sos', methods=['POST'])
@login_required
def send_sos():
    try:
        data = request.get_json()

        lat = data.get('lat')
        lng = data.get('lng')

        # ✅ FIX: check location FIRST
        if not lat or not lng:
            return jsonify({"status": "Location not available"})

        location_link = f"https://www.google.com/maps?q={lat},{lng}"

        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        cursor.execute(
            "SELECT name, mobile FROM users WHERE id=%s",
            (session["user_id"],)
        )
        user = cursor.fetchone()

        cursor.close()
        db.close()

        # ✅ SEND SMS
        send_sms_sos(
            user["name"],
            user["mobile"],
            location_link
        )

        return jsonify({"status": "SMS Sent"})

    except Exception as e:
        print("❌ ERROR:", str(e))
        return jsonify({"status": "error"})
        

# ================= RUN (ALWAYS LAST) =================
if __name__ == "__main__":
    app.run(debug=True)