from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from config.config import Config
from config.database import mysql
from flask import send_from_directory
import os
from werkzeug.utils import secure_filename
import uuid
from dotenv import load_dotenv

from groq import Groq

from models import job, user


app = Flask(__name__)

app.config.from_object(Config)

mysql.init_app(app)

@app.route("/translations/<filename>")
def translations(filename):
    return send_from_directory("translations", filename)

# =========================
# Groq AI Configuration
# =========================

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

client = Groq(
    api_key=GROQ_API_KEY
)

# =========================
# Flask Routes Below
# =========================
# ---------------- HOME ---------------- #

@app.route("/")
def home():
    return render_template("index.html")


# ---------------- REGISTER ---------------- #

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        full_name = request.form["full_name"]
        email = request.form["email"]
        phone = request.form["phone"]
        location = request.form["location"]
        role = request.form["role"]
        password = request.form["password"]


        company_name = request.form.get("company_name","")

        hashed_password = generate_password_hash(password)

        cur = mysql.connection.cursor()

        cur.execute("""
INSERT INTO users
(
    full_name,
    email,
    phone,
    password,
    role,
    location,
    company_name
)
VALUES
(
    %s,
    %s,
    %s,
    %s,
    %s,
    %s,
    %s
)
""",
(
    full_name,
    email,
    phone,
    hashed_password,
    role,
    location,
    company_name
))

        mysql.connection.commit()
        cur.close()

        flash("Registration Successful!", "success")

        return redirect(url_for("login"))

    return render_template("register.html")
# ---------------- LOGIN ---------------- #

# ---------------- LOGIN ---------------- #

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        role = request.form.get("role")
        email = request.form.get("email")
        password = request.form.get("password")

        # Check required fields
        if not role:
            flash("Please select a role", "danger")
            return redirect(url_for("login"))

        if not email or not password:
            flash("Please enter email and password", "danger")
            return redirect(url_for("login"))

        print("HOST:", app.config.get("MYSQL_HOST"))
        print("USER:", app.config.get("MYSQL_USER"))
        print("DB:", app.config.get("MYSQL_DB"))

        # ---------------- ADMIN ---------------- #

        if role == "Admin":

            cur = mysql.connection.cursor()

            cur.execute(
                "SELECT * FROM admins WHERE email=%s",
                (email,)
            )

            admin = cur.fetchone()

            cur.close()

            if admin and admin[3] == password:

                session["admin_id"] = admin[0]
                session["user_name"] = admin[1]
                session["role"] = "Admin"

                return redirect(url_for("admin_dashboard"))

            flash("Unauthorized Administrator", "danger")
            return redirect(url_for("login"))

        # ---------------- JOB SEEKER / EMPLOYER ---------------- #

        cur = mysql.connection.cursor()

        cur.execute("""
            SELECT *
            FROM users
            WHERE email=%s AND role=%s
        """, (email, role))

        user = cur.fetchone()

        cur.close()

        # Debug information
        print("USER:", user)

        if user:

            print("USER ID:", user[0])
            print("USER NAME:", user[1])
            print("USER EMAIL:", user[2])
            print("USER LOCATION:", user[4])
            print("USER ROLE:", user[6])

            # user[5] = password
            if check_password_hash(user[5], password):

                print("PASSWORD CORRECT")

                session["user_id"] = user[0]
                session["user_name"] = user[1]
                session["company_name"] = user[7]
                session["role"] = user[6]

                # Job Seeker
                if user[6] == "Job Seeker":

                    return redirect(
                        url_for("jobseeker_dashboard")
                    )

                # Employer
                elif user[6] == "Employer":

                    return redirect(
                        url_for("employer_dashboard")
                    )

            else:

                print("PASSWORD INCORRECT")
                flash("Incorrect password", "danger")

        else:

            print("USER NOT FOUND")
            flash("Invalid Email or Role", "danger")

    return render_template("login.html")
# ---------------- DASHBOARDS ---------------- #

@app.route("/jobseeker/dashboard")
def jobseeker_dashboard():

    if session.get("role") != "Job Seeker":
        return redirect(url_for("login"))

    return render_template(
        "jobseeker/dashboard.html",
        name=session["user_name"]
    )


# ---------------- VIEW JOBS ---------------- #

@app.route("/employer/jobs")
def view_jobs():

    if "user_id" not in session:
        return redirect(url_for("login"))


    cur = mysql.connection.cursor()



    # ---------------- VIEW AVAILABLE JOBS ---------------- #

    cur.execute("""
    SELECT *
    FROM jobs
    WHERE status='Open'
    ORDER BY created_at DESC
    """)


    jobs = cur.fetchall()


    cur.close()


    return render_template(
        "jobseeker/jobs.html",
        jobs=jobs
    )


# ---------------- EMPLOYER DASHBOARD ---------------- #

@app.route("/employer/dashboard")
def employer_dashboard():

    if session.get("role") != "Employer":
        return redirect(url_for("login"))

    cur = mysql.connection.cursor()

    # Employer Details
    cur.execute("""
        SELECT
            full_name,
            profile_image
        FROM users
        WHERE id=%s
    """, (session["user_id"],))

    user = cur.fetchone()

    # Total Jobs
    cur.execute("""
        SELECT COUNT(*)
        FROM jobs
        WHERE employer_id=%s
    """, (session["user_id"],))

    total_jobs = cur.fetchone()[0]

    # Open Jobs
    cur.execute("""
        SELECT COUNT(*)
        FROM jobs
        WHERE employer_id=%s
        AND status='Open'
    """, (session["user_id"],))

    open_jobs = cur.fetchone()[0]

    # Total Applicants
    cur.execute("""
        SELECT COUNT(*)
        FROM applications
        WHERE employer_id=%s
    """, (session["user_id"],))

    total_applicants = cur.fetchone()[0]

    cur.close()

    return render_template(
        "employer/dashboard.html",
        name=user[0],
        profile_image=user[1],
        total_jobs=total_jobs,
        open_jobs=open_jobs,
        total_applicants=total_applicants
    )
# ---------------- APPLY JOB ---------------- #

@app.route("/apply/<int:job_id>", methods=["GET", "POST"])
def apply_for_job(job_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    cur = mysql.connection.cursor()

    # Get Job Details
    cur.execute(
        "SELECT * FROM jobs WHERE id=%s",
        (job_id,)
    )

    job = cur.fetchone()

    if not job:
        cur.close()
        flash("Job not found", "danger")
        return redirect(url_for("available_jobs"))

    if request.method == "POST":

        job_seeker_id = session["user_id"]

        # Get Employer ID from the Job
        cur.execute(
            """
            SELECT employer_id
            FROM jobs
            WHERE id=%s
            """,
            (job_id,)
        )

        employer = cur.fetchone()

        employer_id = employer[0]

        # Check if already applied
        cur.execute(
            """
            SELECT *
            FROM applications
            WHERE job_id=%s
            AND job_seeker_id=%s
            """,
            (job_id, job_seeker_id)
        )

        existing = cur.fetchone()

        if existing:
            cur.close()
            flash("You already applied for this job", "warning")
            return redirect(url_for("available_jobs"))

        # Insert Application
        cur.execute(
            """
            INSERT INTO applications
            (job_id, job_seeker_id, employer_id, status)
            VALUES (%s, %s, %s, %s)
            """,
            (
                job_id,
                job_seeker_id,
                employer_id,
                "Pending"
            )
        )

        mysql.connection.commit()

        cur.close()

        flash(
            "Application submitted successfully!",
            "success"
        )

        return redirect(url_for("available_jobs"))

    cur.close()

    return render_template(
        "jobseeker/apply.html",
        job=job
    )
# ---------------- MY APPLICATIONS ---------------- #

@app.route("/my_applications")
def my_applications():

    if "user_id" not in session:
        return redirect(url_for("login"))


    user_id = session["user_id"]


    cur = mysql.connection.cursor()


    cur.execute("""
        SELECT 
            jobs.title,
            jobs.category,
            jobs.location,
            jobs.salary,
            applications.status,
            applications.applied_at

        FROM applications

        JOIN jobs
        ON applications.job_id = jobs.id

        WHERE applications.job_seeker_id=%s

        ORDER BY applications.applied_at DESC

    """,(user_id,))


    applications = cur.fetchall()


    cur.close()


    return render_template(
        "jobseeker/my_applications.html",
        applications=applications
    )



# ---------------- POST JOB ---------------- #

@app.route("/post_job", methods=["GET", "POST"])
def post_job():

    if "user_id" not in session:
        return redirect(url_for("login"))


    if request.method == "POST":

        employer_id = session["user_id"]

        title = request.form["title"]
        category = request.form["category"]
        location = request.form["location"]
        salary = request.form["salary"]
        experience = request.form["experience"]
        job_type = request.form["job_type"]
        vacancies = request.form["vacancies"]
        skills = request.form["skills"]
        description = request.form["description"]
        deadline = request.form["deadline"]


        cur = mysql.connection.cursor()


        cur.execute("""
        INSERT INTO jobs
        (
        employer_id,
        title,
        category,
        location,
        salary,
        experience,
        job_type,
        vacancies,
        skills,
        description,
        deadline,
        status
        )

        VALUES
        (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)

        """,

        (
        employer_id,
        title,
        category,
        location,
        salary,
        experience,
        job_type,
        vacancies,
        skills,
        description,
        deadline,
        "Open"
        ))


        mysql.connection.commit()

        cur.close()


        flash("Job Posted Successfully!", "success")

        return redirect(url_for("employer_dashboard"))


    return render_template("employer/post_job.html")









# ---------------- LOGOUT ---------------- #

@app.route("/logout")
def logout():

    session.clear()

    flash("Logged out successfully!", "success")

    return redirect(url_for("login"))
#----------------------feedback--------------------#

from flask import request, redirect, flash

@app.route("/submit_feedback", methods=["POST"])
def submit_feedback():

    name = request.form["name"]
    email = request.form["email"]
    message = request.form["message"]

    conn = mysql.connection
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO feedback(name,email,message) VALUES(%s,%s,%s)",
        (name, email, message)
    )

    conn.commit()
    cursor.close()

    flash("Thank you! Your feedback has been submitted successfully.")

    return redirect("/")
#---------------------- Groq AI Chat --------------------#

@app.route("/chat", methods=["POST"])
def chat():

    data = request.get_json()

    user_message = data.get("message", "")

    prompt = f"""
You are JobBridge AI Assistant.

Help users with:
- Finding jobs
- Applying for jobs
- Resume improvement
- Interview preparation
- Employer support
- JobBridge platform features

User Question:
{user_message}
"""


    try:

        response = client.chat.completions.create(

            model="openai/gpt-oss-20b",

            messages=[
                {
                    "role":"system",
                    "content":"You are a helpful JobBridge AI assistant."
                },
                {
                    "role":"user",
                    "content":prompt
                }
            ]

        )


        return jsonify({

            "reply":response.choices[0].message.content

        })


    except Exception as e:

        print("Groq Error:",e)

        return jsonify({

            "reply":"AI Assistant is temporarily unavailable."

        }),500
   # ---------------- AVAILABLE JOBS ---------------- #

@app.route("/jobs")
def available_jobs():

    if "user_id" not in session:
        return redirect(url_for("login"))


    search = request.args.get("search","")


    cur = mysql.connection.cursor()


    if search:


        cur.execute("""
        SELECT *
        FROM jobs
        WHERE 
        title LIKE %s
        OR category LIKE %s
        OR location LIKE %s
        OR skills LIKE %s
        """,
        (
            "%"+search+"%",
            "%"+search+"%",
            "%"+search+"%",
            "%"+search+"%"
        ))


    else:


        cur.execute("""
        SELECT *
        FROM jobs
        """)


    jobs = cur.fetchall()


    cur.close()


    return render_template(
        "jobseeker/jobs.html",
        jobs=jobs
    )


# ---------------- SAVE JOB ---------------- #

@app.route("/save_job/<int:job_id>")
def save_job(job_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT * FROM saved_jobs
        WHERE job_id=%s AND job_seeker_id=%s
    """,
    (job_id,user_id))

    saved = cur.fetchone()


    if saved:

        flash("Already saved","warning")

    else:

        cur.execute("""
        INSERT INTO saved_jobs(job_id,job_seeker_id)
        VALUES(%s,%s)
        """,
        (job_id,user_id))

        mysql.connection.commit()


    cur.close()

    return redirect(url_for("available_jobs"))


# ---------------- SAVED JOBS ---------------- #

@app.route("/saved_jobs")
def saved_jobs():

    if "user_id" not in session:
        return redirect(url_for("login"))


    user_id = session["user_id"]

    cur = mysql.connection.cursor()


    cur.execute("""
    SELECT 
        jobs.*
    FROM jobs
    JOIN saved_jobs
    ON jobs.id = saved_jobs.job_id
    WHERE saved_jobs.job_seeker_id=%s
    """,
    (user_id,))


    jobs = cur.fetchall()


    cur.close()


    return render_template(
        "jobseeker/saved_jobs.html",
        jobs=jobs
    )

# ---------------- REMOVE SAVED JOB ---------------- #

@app.route("/remove_saved_job/<int:job_id>")
def remove_saved_job(job_id):

    if "user_id" not in session:
        return redirect(url_for("login"))


    user_id = session["user_id"]


    cur = mysql.connection.cursor()


    cur.execute("""
    DELETE FROM saved_jobs
    WHERE job_id=%s AND job_seeker_id=%s
    """,
    (job_id,user_id))


    mysql.connection.commit()


    cur.close()


    flash("Job removed from saved jobs","success")


    return redirect(url_for("saved_jobs"))

# ---------------- PROFILE ---------------- #

@app.route("/profile")
def profile():

    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    cur = mysql.connection.cursor()

    cur.execute(
        "SELECT * FROM users WHERE id=%s",
        (user_id,)
    )

    user = cur.fetchone()

    cur.close()

    return render_template(
        "jobseeker/profile.html",
        user=user
    )


# ---------------- UPDATE PROFILE (Image + Resume Only) ---------------- #

@app.route("/update_profile", methods=["POST"])
def update_profile():

    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT profile_image, resume
        FROM users
        WHERE id=%s
    """, (user_id,))

    old = cur.fetchone()

    image_name = old[0]
    resume_name = old[1]

    # ---------- Upload Profile Image ----------

    image = request.files.get("profile_image")

    if image and image.filename != "":
        image_name = image.filename
        image.save(os.path.join(app.root_path, "static", "images", image_name))

    # ---------- Upload Resume ----------

    resume = request.files.get("resume")

    if resume and resume.filename != "":
        resume_name = resume.filename
        resume.save(os.path.join(app.root_path, "static", "resumes", resume_name))

    cur.execute("""
        UPDATE users
        SET
            profile_image=%s,
            resume=%s
        WHERE id=%s
    """, (
        image_name,
        resume_name,
        user_id
    ))

    mysql.connection.commit()

    cur.close()

    return redirect(url_for("profile"))


# ---------------- EDIT PROFILE ---------------- #

@app.route("/edit_profile")
def edit_profile():

    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    cur = mysql.connection.cursor()

    cur.execute(
        "SELECT * FROM users WHERE id=%s",
        (user_id,)
    )

    user = cur.fetchone()

    cur.close()

    return render_template(
        "jobseeker/edit_profile.html",
        user=user
    )

# ---------------- SAVE PROFILE ---------------- #

@app.route("/save_profile", methods=["POST"])
def save_profile():

    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    phone = request.form.get("phone")
    location = request.form.get("location")
    qualification = request.form.get("qualification")
    skills = request.form.get("skills")
    experience = request.form.get("experience")
    bio = request.form.get("bio")

    cur = mysql.connection.cursor()

    cur.execute("""
        UPDATE users
        SET
            phone=%s,
            location=%s,
            qualification=%s,
            skills=%s,
            experience=%s,
            bio=%s
        WHERE id=%s
    """, (
        phone,
        location,
        qualification,
        skills,
        experience,
        bio,
        user_id
    ))

    mysql.connection.commit()
    cur.close()

    return redirect(url_for("profile"))

@app.route("/messages")
def messages():

    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT
            u.id,
            u.full_name,
            u.role,
            MAX(m.message),
            MAX(m.sent_at)

        FROM messages m

        JOIN users u
        ON (
            u.id = m.sender_id
            OR
            u.id = m.receiver_id
        )

        WHERE 
        (
            m.sender_id=%s
            OR
            m.receiver_id=%s
        )

        AND u.id != %s

        GROUP BY
            u.id,
            u.full_name,
            u.role

        ORDER BY MAX(m.sent_at) DESC

    """, (user_id, user_id, user_id))


    conversations = cur.fetchall()

    cur.close()


    return render_template(
        "jobseeker/messages.html",
        conversations=conversations
    )
# ---------------- DELETE PROFILE PHOTO ---------------- #

@app.route("/delete_profile_image")
def delete_profile_image():

    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    cur = mysql.connection.cursor()

    cur.execute("""
        UPDATE users
        SET profile_image='default.png'
        WHERE id=%s
    """, (user_id,))

    mysql.connection.commit()

    cur.close()

    return redirect(url_for("profile"))

# ---------------- MY JOBS ---------------- #

@app.route("/my_jobs")
def my_jobs():

    if "user_id" not in session:
        return redirect(url_for("login"))

    employer_id = session["user_id"]

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT
        id,
        title,
        category,
        location,
        salary,
        experience,
        job_type,
        vacancies,
        deadline,
        status

        FROM jobs

        WHERE employer_id=%s

        ORDER BY id DESC
    """, (employer_id,))

    jobs = cur.fetchall()

    cur.close()

    return render_template(
        "employer/my_jobs.html",
        jobs=jobs
    )


# ---------------- EDIT JOB ---------------- #

@app.route("/edit_job/<int:job_id>", methods=["GET", "POST"])
def edit_job(job_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    cur = mysql.connection.cursor()

    if request.method == "POST":

        title = request.form["title"]
        category = request.form["category"]
        location = request.form["location"]
        salary = request.form["salary"]
        experience = request.form["experience"]
        job_type = request.form["job_type"]
        vacancies = request.form["vacancies"]
        skills = request.form["skills"]
        description = request.form["description"]
        deadline = request.form["deadline"]
        status = request.form["status"]

        cur.execute("""

        UPDATE jobs

        SET

        title=%s,
        category=%s,
        location=%s,
        salary=%s,
        experience=%s,
        job_type=%s,
        vacancies=%s,
        skills=%s,
        description=%s,
        deadline=%s,
        status=%s

        WHERE id=%s

        """,

        (

        title,
        category,
        location,
        salary,
        experience,
        job_type,
        vacancies,
        skills,
        description,
        deadline,
        status,
        job_id

        ))

        mysql.connection.commit()

        cur.close()

        flash("Job Updated Successfully!")

        return redirect(url_for("my_jobs"))

    cur.execute("SELECT * FROM jobs WHERE id=%s",(job_id,))
    job = cur.fetchone()

    cur.close()

    return render_template(
        "employer/edit_job.html",
        job=job
    )


# ---------------- DELETE JOB ---------------- #

@app.route("/delete_job/<int:job_id>")
def delete_job(job_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    cur = mysql.connection.cursor()

    cur.execute(

        "DELETE FROM jobs WHERE id=%s",

        (job_id,)

    )

    mysql.connection.commit()

    cur.close()

    flash("Job Deleted Successfully!")

    return redirect(url_for("my_jobs"))



# ---------------- VIEW APPLICANTS ---------------- #
# ================= VIEW APPLICANTS ================= #

@app.route("/view_applicants")
def view_applicants():

    if "user_id" not in session:
        return redirect(url_for("login"))

    employer_id = session["user_id"]

    cur = mysql.connection.cursor()

    cur.execute("""

    SELECT

    applications.id,

    users.id,

    users.full_name,

    users.email,

    users.phone,

    jobs.title,

    applications.status,

    applications.applied_at,

    users.resume

    FROM applications

    JOIN users
    ON applications.job_seeker_id = users.id

    JOIN jobs
    ON applications.job_id = jobs.id

    WHERE jobs.employer_id=%s

    ORDER BY applications.applied_at DESC

    """, (employer_id,))

    applicants = cur.fetchall()

    cur.close()

    return render_template(
        "employer/view_applicants.html",
        applicants=applicants
    )

# ================= ACCEPT APPLICATION ================= #

@app.route("/accept_application/<int:application_id>")
def accept_application(application_id):

    print("Accept route called:", application_id)

    if "user_id" not in session:
        return redirect(url_for("login"))

    cur = mysql.connection.cursor()

    cur.execute("""
        UPDATE applications
        SET status='Accepted'
        WHERE id=%s
    """, (application_id,))

    mysql.connection.commit()

    print("Rows Updated:", cur.rowcount)

    cur.close()

    flash("Application Accepted Successfully", "success")

    return redirect(url_for("view_applicants"))

# ================= REJECT APPLICATION ================= #

@app.route("/reject_application/<int:application_id>")
def reject_application(application_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    cur = mysql.connection.cursor()

    cur.execute("""
        UPDATE applications
        SET status='Rejected'
        WHERE id=%s
    """,(application_id,))

    mysql.connection.commit()

    cur.close()

    flash("Application Rejected","danger")

    return redirect(url_for("view_applicants"))


# ================= SCHEDULE INTERVIEW ================= #

@app.route("/schedule_interview/<int:application_id>", methods=["GET", "POST"])
def schedule_interview(application_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    cur = mysql.connection.cursor()

    if request.method == "POST":

        interview_date = request.form["interview_date"]
        interview_mode = request.form["interview_mode"]
        interview_location = request.form["interview_location"]

        # Update interview details
        cur.execute("""
            UPDATE applications
            SET
                interview_date=%s,
                interview_mode=%s,
                interview_location=%s,
                status='Shortlisted'
            WHERE id=%s
        """, (
            interview_date,
            interview_mode,
            interview_location,
            application_id
        ))

        mysql.connection.commit()

        # Get Job Seeker ID
        cur.execute("""
            SELECT job_seeker_id
            FROM applications
            WHERE id=%s
        """, (application_id,))

        job_seeker = cur.fetchone()

        # Insert Notification
        cur.execute("""
            INSERT INTO notifications(user_id, message)
            VALUES(%s, %s)
        """, (
            job_seeker[0],
            "Your interview has been scheduled. Please check My Interviews."
        ))

        mysql.connection.commit()

        cur.close()

        flash("Interview Scheduled Successfully!", "success")

        return redirect(url_for("view_applicants"))

    # GET Request
    cur.execute("""
        SELECT
            applications.id,
            users.full_name,
            jobs.title
        FROM applications
        JOIN users
            ON applications.job_seeker_id = users.id
        JOIN jobs
            ON applications.job_id = jobs.id
        WHERE applications.id=%s
    """, (application_id,))

    application = cur.fetchone()

    cur.close()

    return render_template(
        "employer/schedule_interview.html",
        application=application
    )





# ================= VIEW JOB DETAILS ================= #

@app.route("/job/<int:job_id>")
def view_job(job_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT *
        FROM jobs
        WHERE id=%s
    """, (job_id,))

    job = cur.fetchone()

    cur.close()

    if not job:
        return "Job Not Found", 404

    return render_template(
        "employer/view_job.html",
        job=job
    )



# ================= MY INTERVIEWS ================= #

@app.route("/my_interviews")
def my_interviews():

    if "user_id" not in session:
        return redirect(url_for("login"))

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT
            jobs.title,
            applications.interview_date,
            applications.interview_mode,
            applications.interview_location,
            applications.status
        FROM applications
        JOIN jobs
            ON applications.job_id = jobs.id
        WHERE applications.job_seeker_id=%s
        AND applications.status='Shortlisted'
        ORDER BY applications.interview_date ASC
    """, (session["user_id"],))

    interviews = cur.fetchall()

    cur.close()

    return render_template(
        "jobseeker/my_interviews.html",
        interviews=interviews
    )





# ---------------- EMPLOYER ANALYTICS ---------------- #

@app.route("/analytics")
def analytics():

    if session.get("role") != "Employer":
        return redirect(url_for("login"))

    employer_id = session["user_id"]

    cur = mysql.connection.cursor()

    # Total Jobs Posted
    cur.execute("""
        SELECT COUNT(*)
        FROM jobs
        WHERE employer_id=%s
    """, (employer_id,))
    total_jobs = cur.fetchone()[0]

    # Total Applications
    cur.execute("""
        SELECT COUNT(*)
        FROM applications
        WHERE employer_id=%s
    """, (employer_id,))
    total_applications = cur.fetchone()[0]

    # Pending
    cur.execute("""
        SELECT COUNT(*)
        FROM applications
        WHERE employer_id=%s
        AND status='Pending'
    """, (employer_id,))
    pending = cur.fetchone()[0]

    # Accepted
    cur.execute("""
        SELECT COUNT(*)
        FROM applications
        WHERE employer_id=%s
        AND status='Accepted'
    """, (employer_id,))
    accepted = cur.fetchone()[0]

    # Interview Scheduled
    cur.execute("""
        SELECT COUNT(*)
        FROM applications
        WHERE employer_id=%s
        AND status='Shortlisted'
    """, (employer_id,))
    interviews = cur.fetchone()[0]

    # Rejected
    cur.execute("""
        SELECT COUNT(*)
        FROM applications
        WHERE employer_id=%s
        AND status='Rejected'
    """, (employer_id,))
    rejected = cur.fetchone()[0]

    cur.close()

    return render_template(
        "employer/analytics.html",
        total_jobs=total_jobs,
        total_applications=total_applications,
        pending=pending,
        accepted=accepted,
        interviews=interviews,
        rejected=rejected
    )


# ================= MY NOTIFICATIONS ================= #

@app.route("/notifications")
def notifications():

    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT
            id,
            message,
            is_read,
            created_at
        FROM notifications
        WHERE user_id=%s
        ORDER BY created_at DESC
    """, (user_id,))

    notifications = cur.fetchall()

    # Mark all notifications as read
    cur.execute("""
        UPDATE notifications
        SET is_read=1
        WHERE user_id=%s
    """, (user_id,))

    mysql.connection.commit()

    cur.close()

    return render_template(
        "jobseeker/notifications.html",
        notifications=notifications
    )





@app.route("/start_chat/<int:user_id>")
def start_chat(user_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    sender_id = session["user_id"]
    receiver_id = user_id

    cur = mysql.connection.cursor()

    # Get Job Seeker Name
    cur.execute("""
        SELECT full_name
        FROM users
        WHERE id=%s
    """, (receiver_id,))

    receiver = cur.fetchone()

    print("Receiver:", receiver)

    # Get Chat Messages
    cur.execute("""
        SELECT sender_id, receiver_id, message, sent_at
        FROM messages
        WHERE
            (sender_id=%s AND receiver_id=%s)
            OR
            (sender_id=%s AND receiver_id=%s)
        ORDER BY sent_at ASC
    """, (
        sender_id,
        receiver_id,
        receiver_id,
        sender_id
    ))

    chats = cur.fetchall()

    cur.close()

    return render_template(
        "employer/chat.html",
        receiver_id=receiver_id,
        receiver_name=receiver[0] if receiver else "Job Seeker",
        chats=chats
    )



@app.route("/jobseeker/chat/<int:employer_id>")
def jobseeker_chat(employer_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    jobseeker_id = session["user_id"]

    cur = mysql.connection.cursor()

    # Get Employer Name
    cur.execute("""
        SELECT full_name
        FROM users
        WHERE id=%s
    """, (employer_id,))

    employer = cur.fetchone()
    print("Employer:", employer)
    # Get Chat Messages
    cur.execute("""
        SELECT sender_id, receiver_id, message, sent_at
        FROM messages
        WHERE
            (sender_id=%s AND receiver_id=%s)
            OR
            (sender_id=%s AND receiver_id=%s)
        ORDER BY sent_at ASC
    """, (
        jobseeker_id,
        employer_id,
        employer_id,
        jobseeker_id
    ))

    chats = cur.fetchall()

    cur.close()

    return render_template(
        "jobseeker/chat.html",
        receiver_id=employer_id,
        receiver_name=employer[0] if employer else "Employer",
        chats=chats
    )

@app.route("/send_message", methods=["POST"])
def send_message():

    if "user_id" not in session:
        return redirect(url_for("login"))

    sender_id = session["user_id"]
    receiver_id = int(request.form["receiver_id"])
    message = request.form["message"]

    cur = mysql.connection.cursor()

    cur.execute("""
        INSERT INTO messages(sender_id, receiver_id, message)
        VALUES(%s,%s,%s)
    """, (sender_id, receiver_id, message))

    mysql.connection.commit()
    cur.close()

    # Employer
    if session["role"] == "Employer":
        return redirect(url_for("start_chat", user_id=receiver_id))

    # Job Seeker
    return redirect(url_for("jobseeker_chat", employer_id=receiver_id))   

print("==== REGISTERED ROUTES ====")
print(app.url_map)



@app.route("/employer/messages")
def employer_messages():

    if "user_id" not in session:
        return redirect(url_for("login"))

    employer_id = session["user_id"]

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT DISTINCT
            u.id,
            u.full_name

        FROM users u

        JOIN messages m
        ON (
            (u.id = m.sender_id AND m.receiver_id = %s)
            OR
            (u.id = m.receiver_id AND m.sender_id = %s)
        )

        WHERE u.role = 'Job Seeker'

        ORDER BY u.full_name
    """, (employer_id, employer_id))

    conversations = cur.fetchall()

    cur.close()

    return render_template(
        "employer/messages.html",
        conversations=conversations
    )


@app.route("/edit_company_profile", methods=["GET", "POST"])
def edit_company_profile():

    if session.get("role") != "Employer":
        return redirect(url_for("login"))

    cur = mysql.connection.cursor()

    if request.method == "POST":

        full_name = request.form["full_name"]
        company_name = request.form["company_name"]
        phone = request.form["phone"]
        location = request.form["location"]
        bio = request.form["bio"]

        profile_image = request.files.get("profile_image")

        # ================= Upload New Image =================

        if profile_image and profile_image.filename != "":

            filename = secure_filename(profile_image.filename)

            # create unique filename
            ext = os.path.splitext(filename)[1]
            filename = str(uuid.uuid4()) + ext

            upload_folder = os.path.join(app.static_folder, "uploads")
            os.makedirs(upload_folder, exist_ok=True)

            profile_image.save(
                os.path.join(upload_folder, filename)
            )

            cur.execute("""
                UPDATE users
                SET
                    full_name=%s,
                    company_name=%s,
                    phone=%s,
                    location=%s,
                    bio=%s,
                    profile_image=%s
                WHERE id=%s
            """, (
                full_name,
                company_name,
                phone,
                location,
                bio,
                filename,
                session["user_id"]
            ))

        # ================= Without New Image =================

        else:

            cur.execute("""
                UPDATE users
                SET
                    full_name=%s,
                    company_name=%s,
                    phone=%s,
                    location=%s,
                    bio=%s
                WHERE id=%s
            """, (
                full_name,
                company_name,
                phone,
                location,
                bio,
                session["user_id"]
            ))

        mysql.connection.commit()
        cur.close()

        return redirect(url_for("employer_profile"))

    # ================= GET COMPANY DETAILS =================

    cur.execute("""
        SELECT
            full_name,
            company_name,
            phone,
            location,
            bio,
            profile_image
        FROM users
        WHERE id=%s
    """, (session["user_id"],))

    company = cur.fetchone()

    cur.close()

    return render_template(
        "employer/edit_company_profile.html",
        company=company
    )

@app.route("/employer/profile")
def employer_profile():

    if session.get("role") != "Employer":
        return redirect(url_for("login"))

    cur = mysql.connection.cursor()

    # Employer details
    cur.execute("""
        SELECT
            full_name,
            company_name,
            email,
            phone,
            location,
            bio,
            profile_image,
            created_at
        FROM users
        WHERE id=%s
    """, (session["user_id"],))

    employer = cur.fetchone()

    # Jobs Posted
    cur.execute("""
        SELECT COUNT(*)
        FROM jobs
        WHERE employer_id=%s
    """, (session["user_id"],))
    total_jobs = cur.fetchone()[0]

    # Open Jobs
    cur.execute("""
        SELECT COUNT(*)
        FROM jobs
        WHERE employer_id=%s
        AND status='Open'
    """, (session["user_id"],))
    open_jobs = cur.fetchone()[0]

    # Total Applicants
    cur.execute("""
        SELECT COUNT(*)
        FROM applications a
        JOIN jobs j
        ON a.job_id=j.id
        WHERE j.employer_id=%s
    """, (session["user_id"],))
    applicants = cur.fetchone()[0]

    cur.close()

    return render_template(
        "employer/company_profile.html",
        employer=employer,
        total_jobs=total_jobs,
        open_jobs=open_jobs,
        applicants=applicants
    )



# ================= ADMIN DASHBOARD ================= #

@app.route("/admin/dashboard")
def admin_dashboard():

    if session.get("role") != "Admin":
        return redirect(url_for("login"))


    cur = mysql.connection.cursor()


    # ================= ADMIN PROFILE ================= #

    admin_id = session["admin_id"]

    cur.execute("""
        SELECT *
        FROM admins
        WHERE id=%s
    """,
    (admin_id,))

    admin = cur.fetchone()



    # ================= TOTAL USERS ================= #

    cur.execute("SELECT COUNT(*) FROM users")
    total_users = cur.fetchone()[0]



    # ================= EMPLOYERS ================= #

    cur.execute("""
        SELECT COUNT(*)
        FROM users
        WHERE role='Employer'
    """)
    employers = cur.fetchone()[0]



    # ================= JOB SEEKERS ================= #

    cur.execute("""
        SELECT COUNT(*)
        FROM users
        WHERE role='Job Seeker'
    """)
    job_seekers = cur.fetchone()[0]



    # ================= TOTAL JOBS ================= #

    cur.execute("""
        SELECT COUNT(*)
        FROM jobs
    """)
    total_jobs = cur.fetchone()[0]



    # ================= OPEN JOBS ================= #

    cur.execute("""
        SELECT COUNT(*)
        FROM jobs
        WHERE status='Open'
    """)
    open_jobs = cur.fetchone()[0]



    # ================= APPLICATIONS ================= #

    cur.execute("""
        SELECT COUNT(*)
        FROM applications
    """)
    applications = cur.fetchone()[0]



    # ================= MESSAGES ================= #

    cur.execute("""
        SELECT COUNT(*)
        FROM messages
    """)
    messages = cur.fetchone()[0]



    # ================= FEEDBACKS ================= #

    try:

        cur.execute("""
            SELECT COUNT(*)
            FROM feedbacks
        """)

        feedbacks = cur.fetchone()[0]

    except:

        feedbacks = 0




    # ================= RECENT USERS ================= #

    cur.execute("""
        SELECT 
            id,
            full_name,
            role,
            created_at
        FROM users
        ORDER BY created_at DESC
        LIMIT 5
    """)

    recent_users = cur.fetchall()




    # ================= RECENT JOBS ================= #

    cur.execute("""
        SELECT
            j.title,
            u.company_name,
            j.status,
            j.created_at

        FROM jobs j

        JOIN users u
            ON j.employer_id = u.id

        ORDER BY j.created_at DESC

        LIMIT 5

    """)

    recent_jobs = cur.fetchall()



    cur.close()



    return render_template(

        "admin/dashboard.html",

        # Admin Profile
        admin=admin,

        admin_name=session["user_name"],


        # Dashboard Data
        total_users=total_users,
        employers=employers,
        job_seekers=job_seekers,

        total_jobs=total_jobs,
        open_jobs=open_jobs,

        applications=applications,
        messages=messages,

        feedbacks=feedbacks,


        # Tables
        recent_users=recent_users,
        recent_jobs=recent_jobs

    )

# ---------------- JOB SEEKER ANALYTICS ---------------- #

@app.route("/jobseeker/analytics")
def jobseeker_analytics():

    if session.get("role") != "Job Seeker":
        return redirect(url_for("login"))

    user_id = session["user_id"]

    cur = mysql.connection.cursor()

    # Total Applications
    cur.execute("""
        SELECT COUNT(*)
        FROM applications
        WHERE job_seeker_id=%s
    """, (user_id,))
    total_applications = cur.fetchone()[0]

    # Pending
    cur.execute("""
        SELECT COUNT(*)
        FROM applications
        WHERE job_seeker_id=%s
        AND status='Pending'
    """, (user_id,))
    pending = cur.fetchone()[0]

    # Accepted (Count Shortlisted as Accepted)
    cur.execute("""
        SELECT COUNT(*)
        FROM applications
        WHERE job_seeker_id=%s
        AND status='Shortlisted'
    """, (user_id,))
    accepted = cur.fetchone()[0]

    # Rejected
    cur.execute("""
        SELECT COUNT(*)
        FROM applications
        WHERE job_seeker_id=%s
        AND status='Rejected'
    """, (user_id,))
    rejected = cur.fetchone()[0]

    cur.close()

    return render_template(
        "jobseeker/analytics.html",
        total=total_applications,
        pending=pending,
        accepted=accepted,
        interviews=accepted,
        rejected=rejected
    )


# ================= ADMIN - MANAGE USERS ================= #

@app.route("/admin/manage_users")
def admin_manage_users():

    if session.get("role") != "Admin":
        return redirect(url_for("login"))

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT
            id,
            full_name,
            email,
            role,
            location,
            created_at
        FROM users
        ORDER BY id DESC
    """)

    users = cur.fetchall()

    cur.close()

    return render_template(
        "admin/manage_users.html",
        users=users,
        admin_name=session["user_name"]
    )


# # ================= DELETE USER ================= #

@app.route("/admin/delete_user/<int:user_id>")
def admin_delete_user(user_id):

    if session.get("role") != "Admin":
        return redirect(url_for("login"))

    cur = mysql.connection.cursor()

    try:

        # Delete messages
        cur.execute(
            "DELETE FROM messages WHERE sender_id=%s OR receiver_id=%s",
            (user_id, user_id)
        )

        # Delete notifications
        cur.execute(
            "DELETE FROM notifications WHERE user_id=%s",
            (user_id,)
        )

        # Delete saved jobs
        cur.execute(
            "DELETE FROM saved_jobs WHERE job_seeker_id=%s",
            (user_id,)
        )

        # Delete applications
        cur.execute(
            "DELETE FROM applications WHERE job_seeker_id=%s",
            (user_id,)
        )

        # Delete jobs posted by employer
        cur.execute(
            "DELETE FROM jobs WHERE employer_id=%s",
            (user_id,)
        )

        # Delete company
        cur.execute(
            "DELETE FROM companies WHERE user_id=%s",
            (user_id,)
        )

        # Finally delete user
        cur.execute(
            "DELETE FROM users WHERE id=%s",
            (user_id,)
        )

        mysql.connection.commit()

    except Exception as e:

        mysql.connection.rollback()
        print(e)

    finally:

        cur.close()

    return redirect(url_for("admin_manage_users"))

# ================= ADMIN - MANAGE JOBS ================= #

@app.route("/admin/jobs")
def admin_jobs():

    if session.get("role") != "Admin":
        return redirect(url_for("login"))

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT
            jobs.id,
            jobs.title,
            users.company_name,
            jobs.category,
            jobs.location,
            jobs.salary,
            jobs.job_type,
            jobs.vacancies,
            jobs.status,
            jobs.created_at
        FROM jobs
        JOIN users
        ON jobs.employer_id = users.id
        ORDER BY jobs.id DESC
    """)

    jobs = cur.fetchall()

    cur.close()

    return render_template(
        "admin/manage_jobs.html",
        jobs=jobs,
        admin_name=session["user_name"]
    )


@app.route("/admin/delete_job/<int:job_id>")
def admin_delete_job(job_id):

    if session.get("role") != "Admin":
        return redirect(url_for("login"))

    cur = mysql.connection.cursor()

    try:

        # Delete applications of this job
        cur.execute(
            "DELETE FROM applications WHERE job_id=%s",
            (job_id,)
        )

        # Delete saved jobs
        cur.execute(
            "DELETE FROM saved_jobs WHERE job_id=%s",
            (job_id,)
        )

        # Delete job
        cur.execute(
            "DELETE FROM jobs WHERE id=%s",
            (job_id,)
        )

        mysql.connection.commit()

    except Exception as e:

        mysql.connection.rollback()
        print(e)

    finally:

        cur.close()

    return redirect(url_for("admin_jobs"))

# ================= ADMIN - VIEW JOB ================= #
@app.route('/admin/view_job/<int:job_id>')
def admin_view_job(job_id):

    cursor = mysql.connection.cursor()

    cursor.execute(
        "SELECT * FROM jobs WHERE id=%s",
        (job_id,)
    )

    job = cursor.fetchone()

    cursor.close()


    return render_template(
        "admin/view_job.html",
        job=job,
        admin_name=session.get("name")
    )

@app.route('/admin/edit_job/<int:job_id>', methods=['GET','POST'])
def admin_edit_job(job_id):

    cursor = mysql.connection.cursor()


    if request.method == "POST":

        title = request.form['title']
        category = request.form['category']
        location = request.form['location']
        salary = request.form['salary']
        experience = request.form['experience']
        job_type = request.form['job_type']
        vacancies = request.form['vacancies']
        skills = request.form['skills']
        description = request.form['description']
        deadline = request.form['deadline']
        status = request.form['status']


        cursor.execute("""
            UPDATE jobs SET

            title=%s,
            category=%s,
            location=%s,
            salary=%s,
            experience=%s,
            job_type=%s,
            vacancies=%s,
            skills=%s,
            description=%s,
            deadline=%s,
            status=%s

            WHERE id=%s

        """,
        (
            title,
            category,
            location,
            salary,
            experience,
            job_type,
            vacancies,
            skills,
            description,
            deadline,
            status,
            job_id
        ))


        mysql.connection.commit()

        cursor.close()


        return redirect('/admin/jobs')




    cursor.execute(
        "SELECT * FROM jobs WHERE id=%s",
        (job_id,)
    )


    job = cursor.fetchone()


    cursor.close()


    return render_template(
        "admin/edit_job.html",
        job=job,
        admin_name=session.get("name")
    )

@app.route('/admin/applications')
def admin_applications():

    cursor = mysql.connection.cursor()


    cursor.execute("""
        SELECT 
            applications.id,
            jobs.title,
            users.full_name,
            users.email,
            applications.status,
            applications.interview_date,
            applications.interview_mode,
            applications.interview_location,
            applications.applied_at

        FROM applications

        JOIN jobs
        ON applications.job_id = jobs.id

        JOIN users
        ON applications.job_seeker_id = users.id

        ORDER BY applications.applied_at DESC

    """)


    applications = cursor.fetchall()


    cursor.close()


    return render_template(
        "admin/applications.html",
        applications=applications,
        admin_name=session.get("name")
    )

@app.route('/admin/view_application/<int:application_id>')
def admin_view_application(application_id):

    cursor = mysql.connection.cursor()


    cursor.execute("""
        SELECT 
            applications.id,
            jobs.title,
            users.full_name,
            users.email,
            users.phone,
            users.location,
            users.skills,
            applications.status,
            applications.interview_date,
            applications.interview_mode,
            applications.interview_location,
            applications.applied_at

        FROM applications

        JOIN jobs
        ON applications.job_id = jobs.id

        JOIN users
        ON applications.job_seeker_id = users.id

        WHERE applications.id=%s

    """,(application_id,))


    application = cursor.fetchone()


    cursor.close()


    return render_template(
        "admin/view_application.html",
        application=application,
        admin_name=session.get("name")
    )

@app.route('/admin/messages')
def admin_messages():

    if "admin_id" not in session:
        return redirect(url_for("login"))

    cursor = mysql.connection.cursor()

    cursor.execute("""
        SELECT
            am.id,
            a.name AS admin_name,
            u.full_name AS user_name,
            am.message,
            am.sent_at

        FROM admin_messages am

        INNER JOIN admins a
            ON am.admin_id = a.id

        INNER JOIN users u
            ON am.user_id = u.id

        ORDER BY am.sent_at DESC
    """)

    messages = cursor.fetchall()

    cursor.close()

    return render_template(
        "admin/messages.html",
        messages=messages,
        admin_name=session.get("user_name")
    )

@app.route('/admin/view_message/<int:message_id>')
def admin_view_message(message_id):

    cursor = mysql.connection.cursor()

    cursor.execute("""
        SELECT
            am.id,
            a.name,
            a.email,
            u.full_name,
            u.email,
            am.message,
            am.sent_at

        FROM admin_messages AS am

        LEFT JOIN admins AS a
            ON am.admin_id = a.id

        LEFT JOIN users AS u
            ON am.user_id = u.id

        WHERE am.id = %s
    """, (message_id,))

    message = cursor.fetchone()

    cursor.close()

    return render_template(
        "admin/view_message.html",
        message=message,
        admin_name=session.get("user_name")
    )


@app.route('/admin/send_message/<int:user_id>', methods=['GET', 'POST'])
def admin_send_message(user_id):

    if "admin_id" not in session:
        return redirect(url_for("login"))

    cursor = mysql.connection.cursor()

    if request.method == "POST":

        message = request.form["message"].strip()
        admin_id = session["admin_id"]

        # Save for Admin Panel
        cursor.execute("""
            INSERT INTO admin_messages
            (admin_id, user_id, message)
            VALUES (%s, %s, %s)
        """, (admin_id, user_id, message))

        # Find this admin's user account
        cursor.execute("""
            SELECT user_id
            FROM admins
            WHERE id=%s
        """, (admin_id,))

        admin = cursor.fetchone()

        if admin and admin[0]:

            sender_id = admin[0]

            # Save in normal chat
            cursor.execute("""
                INSERT INTO messages
                (sender_id, receiver_id, message)
                VALUES (%s, %s, %s)
            """, (
                sender_id,
                user_id,
                message
            ))

        mysql.connection.commit()
        cursor.close()

        flash("Message sent successfully.", "success")
        return redirect(url_for("admin_messages"))

    cursor.execute("""
        SELECT id, full_name, email, role
        FROM users
        WHERE id=%s
    """, (user_id,))

    user = cursor.fetchone()

    cursor.close()

    if not user:
        flash("User not found.", "danger")
        return redirect(url_for("admin_messages"))

    return render_template(
        "admin/send_message.html",
        user=user
    )



@app.route('/admin/manage_users')
def manage_users():

    cursor = mysql.connection.cursor()

    cursor.execute("""
        SELECT 
        id,
        full_name,
        email,
        role,
        location,
        created_at
        FROM users
    """)

    users = cursor.fetchall()

    cursor.close()


    return render_template(
        "admin/manage_users.html",
        users=users,
        admin_name=session.get("name")
    )




@app.route('/admin/notifications', methods=['GET', 'POST'])
def admin_notifications():

    if "admin_id" not in session:
        return redirect(url_for("login"))

    cursor = mysql.connection.cursor()

    if request.method == "POST":

        target = request.form["target"]
        user_id = request.form.get("user_id")
        message = request.form["message"].strip()

        admin_id = session["admin_id"]

        # ---------------- Single User ----------------

        if target == "User":

            cursor.execute("""
                INSERT INTO admin_messages
                (admin_id, user_id, target, message)
                VALUES (%s, %s, %s, %s)
            """, (
                admin_id,
                user_id,
                target,
                message
            ))

        # ---------------- All Job Seekers ----------------

        elif target == "Job Seekers":

            cursor.execute("""
                SELECT id
                FROM users
                WHERE role='Job Seeker'
            """)

            users_list = cursor.fetchall()

            for user in users_list:

                cursor.execute("""
                    INSERT INTO admin_messages
                    (admin_id, user_id, target, message)
                    VALUES (%s, %s, %s, %s)
                """, (
                    admin_id,
                    user[0],
                    target,
                    message
                ))

        # ---------------- All Employers ----------------

        elif target == "Employers":

            cursor.execute("""
                SELECT id
                FROM users
                WHERE role='Employer'
            """)

            users_list = cursor.fetchall()

            for user in users_list:

                cursor.execute("""
                    INSERT INTO admin_messages
                    (admin_id, user_id, target, message)
                    VALUES (%s, %s, %s, %s)
                """, (
                    admin_id,
                    user[0],
                    target,
                    message
                ))

        # ---------------- Everyone ----------------

        elif target == "All":

            cursor.execute("""
                SELECT id
                FROM users
            """)

            users_list = cursor.fetchall()

            for user in users_list:

                cursor.execute("""
                    INSERT INTO admin_messages
                    (admin_id, user_id, target, message)
                    VALUES (%s, %s, %s, %s)
                """, (
                    admin_id,
                    user[0],
                    target,
                    message
                ))

        mysql.connection.commit()

        flash("Notification sent successfully!", "success")

    # ---------------- Get Users ----------------

    cursor.execute("""
        SELECT
            id,
            full_name,
            role
        FROM users
        ORDER BY full_name
    """)

    users = cursor.fetchall()

    # ---------------- Notification History ----------------

    cursor.execute("""
        SELECT
            am.id,
            am.target,
            u.full_name,
            am.message,
            am.sent_at
        FROM admin_messages am
        LEFT JOIN users u
        ON am.user_id = u.id
        ORDER BY am.sent_at DESC
    """)

    notifications = cursor.fetchall()

    cursor.close()

    return render_template(
        "admin/notifications.html",
        users=users,
        notifications=notifications,
        admin_name=session.get("user_name")
    )


@app.route("/jobseeker/notifications")
def jobseeker_notifications():

    if "user_id" not in session:
        return redirect(url_for("login"))

    cursor = mysql.connection.cursor()

    cursor.execute("""
        SELECT
            message,
            sent_at
        FROM admin_messages
        WHERE user_id=%s
        ORDER BY sent_at DESC
    """, (session["user_id"],))

    notifications = cursor.fetchall()

    cursor.close()

    return render_template(
        "jobseeker/notifications.html",
        notifications=notifications
    )



@app.route("/employer/notifications")
def employer_notifications():

    if "user_id" not in session:
        return redirect(url_for("login"))

    cursor = mysql.connection.cursor()

    cursor.execute("""
        SELECT
            message,
            sent_at
        FROM admin_messages
        WHERE user_id=%s
        ORDER BY sent_at DESC
    """, (session["user_id"],))

    notifications = cursor.fetchall()

    cursor.close()

    return render_template(
        "employer/notifications.html",
        notifications=notifications,
        name=session.get("user_name")
    )


@app.route("/admin/feedbacks")
def admin_feedbacks():

    if "admin_id" not in session:
        return redirect(url_for("login"))

    cursor = mysql.connection.cursor()

    cursor.execute("""
        SELECT
            id,
            name,
            email,
            message,
            created_at
        FROM feedback
        ORDER BY created_at DESC
    """)

    feedbacks = cursor.fetchall()

    cursor.close()

    return render_template(
        "admin/feedbacks.html",
        feedbacks=feedbacks,
        admin_name=session.get("user_name")
    )



@app.route("/admin/delete_feedback/<int:feedback_id>")
def delete_feedback(feedback_id):

    if "admin_id" not in session:
        return redirect(url_for("login"))

    cursor = mysql.connection.cursor()

    cursor.execute(
        "DELETE FROM feedback WHERE id=%s",
        (feedback_id,)
    )

    mysql.connection.commit()

    cursor.close()

    flash("Feedback deleted successfully.","success")

    return redirect(url_for("admin_feedbacks"))




@app.route("/admin/reports")
def admin_reports():

    if "admin_id" not in session:
        return redirect(url_for("login"))

    cursor = mysql.connection.cursor()

    # Total Users
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]

    # Job Seekers
    cursor.execute("SELECT COUNT(*) FROM users WHERE role='Job Seeker'")
    job_seekers = cursor.fetchone()[0]

    # Employers
    cursor.execute("SELECT COUNT(*) FROM users WHERE role='Employer'")
    employers = cursor.fetchone()[0]

    # Total Jobs
    cursor.execute("SELECT COUNT(*) FROM jobs")
    total_jobs = cursor.fetchone()[0]

    # Open Jobs
    cursor.execute("SELECT COUNT(*) FROM jobs WHERE status='Open'")
    open_jobs = cursor.fetchone()[0]

    # Closed Jobs
    cursor.execute("SELECT COUNT(*) FROM jobs WHERE status='Closed'")
    closed_jobs = cursor.fetchone()[0]

    # Applications
    cursor.execute("SELECT COUNT(*) FROM applications")
    total_applications = cursor.fetchone()[0]

    # Pending
    cursor.execute("SELECT COUNT(*) FROM applications WHERE status='Pending'")
    pending = cursor.fetchone()[0]

    # Shortlisted
    cursor.execute("SELECT COUNT(*) FROM applications WHERE status='Shortlisted'")
    shortlisted = cursor.fetchone()[0]

    # Accepted
    cursor.execute("SELECT COUNT(*) FROM applications WHERE status='Accepted'")
    accepted = cursor.fetchone()[0]

    # Rejected
    cursor.execute("SELECT COUNT(*) FROM applications WHERE status='Rejected'")
    rejected = cursor.fetchone()[0]

    # Selected
    cursor.execute("SELECT COUNT(*) FROM applications WHERE status='Selected'")
    selected = cursor.fetchone()[0]

    # Messages
    cursor.execute("SELECT COUNT(*) FROM messages")
    total_messages = cursor.fetchone()[0]

    # Feedback
    cursor.execute("SELECT COUNT(*) FROM feedback")
    total_feedback = cursor.fetchone()[0]

    # Notifications
    cursor.execute("SELECT COUNT(*) FROM admin_messages")
    total_notifications = cursor.fetchone()[0]

    cursor.close()

    return render_template(
        "admin/reports.html",
        total_users=total_users,
        job_seekers=job_seekers,
        employers=employers,
        total_jobs=total_jobs,
        open_jobs=open_jobs,
        closed_jobs=closed_jobs,
        total_applications=total_applications,
        pending=pending,
        shortlisted=shortlisted,
        accepted=accepted,
        rejected=rejected,
        selected=selected,
        total_messages=total_messages,
        total_feedback=total_feedback,
        total_notifications=total_notifications,
        admin_name=session.get("user_name")
    )


@app.route("/admin/settings", methods=["GET", "POST"])
def admin_settings():

    if "admin_id" not in session:
        return redirect(url_for("login"))

    admin_id = session["admin_id"]

    cur = mysql.connection.cursor()

    if request.method == "POST":

        name = request.form.get("name")
        phone = request.form.get("phone")
        location = request.form.get("location")

        image = request.files.get("profile_image")

        # ================= IMAGE UPLOAD =================

        if image and image.filename != "":

            filename = secure_filename(image.filename)

            upload_folder = os.path.join("static", "uploads")

            if not os.path.exists(upload_folder):
                os.makedirs(upload_folder)

            image.save(os.path.join(upload_folder, filename))

            cur.execute("""
                UPDATE admins
                SET
                    name=%s,
                    phone=%s,
                    location=%s,
                    profile_image=%s
                WHERE id=%s
            """,
            (
                name,
                phone,
                location,
                filename,
                admin_id
            ))

        else:

            cur.execute("""
                UPDATE admins
                SET
                    name=%s,
                    phone=%s,
                    location=%s
                WHERE id=%s
            """,
            (
                name,
                phone,
                location,
                admin_id
            ))

        mysql.connection.commit()

        session["user_name"] = name

        flash("Profile updated successfully!", "success")

    # ================= FETCH ADMIN =================

    cur.execute("""
        SELECT *
        FROM admins
        WHERE id=%s
    """, (admin_id,))

    admin = cur.fetchone()

    cur.close()

    return render_template(
        "admin/settings.html",
        admin=admin
    )

if __name__=="__main__":
    app.run(debug=True)