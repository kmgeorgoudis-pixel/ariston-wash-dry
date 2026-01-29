from flask import Flask, render_template, request, redirect, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from email.header import Header
from database import db, init_db
from database import Review
from database import siteReview



from datetime import datetime, timedelta
from flask_migrate import Migrate
from flask_login import LoginManager, login_user, logout_user, login_required, current_user

from database import db, init_db, User, Coupon, Announcement, Review, ContactMessage, Score
import random
import smtplib
from email.mime.text import MIMEText
from email.message import EmailMessage


def register_user(fullname, email, password, confirm):
    if password != confirm:
        return "Οι κωδικοί δεν ταιριάζουν."

    existing = User.query.filter_by(email=email).first()
    if existing:
        return "Το email υπάρχει ήδη."

    hashed = generate_password_hash(password)

    user = User(fullname=fullname, email=email, password=hashed)
    db.session.add(user)
    db.session.commit()

    return "OK"

app = Flask(__name__, template_folder="templates", static_folder="templates")
app.secret_key = "supersecretkey123"

# === SQLAlchemy Init ===
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///users.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
init_db(app)
migrate = Migrate(app, db)

# === Login Manager ===
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

def send_coupon_email(user, coupon):
    body = f"""
Αγαπητέ/ή {user.fullname},

Έχετε λάβει ένα νέο προσωπικό κουπόνι από το ARISTON Wash & Dry.

━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 ΣΤΟΙΧΕΙΑ ΚΟΥΠΟΝΙΟΥ
━━━━━━━━━━━━━━━━━━━━━━━━━━
Τίτλος: {coupon.title}
Περιγραφή: {coupon.description}
Ποσό έκπτωσης: {coupon.amount}€
Ισχύει από: {coupon.start_date.strftime('%d/%m/%Y')}
Ισχύει έως: {coupon.end_date.strftime('%d/%m/%Y')}

━━━━━━━━━━━━━━━━━━━━━━━━━━
Για να δείτε όλα τα κουπόνια σας:
https://aristonwashdry.gr/coupons
━━━━━━━━━━━━━━━━━━━━━━━━━━

Με εκτίμηση,
Η ομάδα του ARISTON Wash & Dry

<a href="https://aristonwashdry.gr" target="_blank" style="text-decoration:none;">
  <img src="https://aristonwashdry.gr/templates/images/1new.png"
       alt="ARISTON Wash & Dry"
       style="height:100px; width:auto; margin-top:12px;">
</a>

<hr>
<p style='font-size: 12px; color: #666;'>
Το παρόν email στάλθηκε από το ARISTON Wash & Dry σύμφωνα με την 
<a href="https://aristonwashdry.gr/privacy">Πολιτική Απορρήτου</a>. 
Τα δεδομένα σας χρησιμοποιούνται αποκλειστικά για τη λειτουργία της υπηρεσίας 
και δεν κοινοποιούνται σε τρίτους.
</p>
"""

    send_email(user.email, "Νέο Κουπόνι από το ARISTON Wash & Dry", body)

from flask import session, request

MAINTENANCE_MODE = False
ACCESS_CODE = "the@code@is9!8!7!4!5!6!3!2!1!ARISTON_Wash_Dry"

@app.before_request
def maintenance_lock():
    if MAINTENANCE_MODE:
        # Αν έχει βάλει σωστό κωδικό → πλήρης πρόσβαση
        if session.get("access_granted") == True:
            return

        # Αν πάει στη σελίδα εισαγωγής κωδικού → επιτρέπεται
        if request.path == "/access":
            return

        # Αλλιώς → δείξε maintenance page
        return render_template("maintenance.html"), 503
@app.route("/lock-secret-ARISTON-987654321")
def lock_secret():
    global MAINTENANCE_MODE
    MAINTENANCE_MODE = True
    session["access_granted"] = False
    return "🔒 Το site κλειδώθηκε ξανά με επιτυχία."


from email.message import EmailMessage

import requests
import os

def send_email(to, subject, body):
    print("=== USING RESEND SEND_EMAIL ===")
    print("EMAIL SUBJECT:", subject)

    api_key = os.getenv("RESEND_API_KEY")

    url = "https://api.resend.com/emails"

    data = {
        "from": "ARISTON Wash & Dry <info@aristonwashdry.gr>",
        "to": [to],
        "subject": subject,
        "html": body.replace("\n", "<br>")
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    response = requests.post(url, json=data, headers=headers)
    print("RESEND RESPONSE:", response.status_code, response.text)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ============================
#       PUBLIC PAGES
# ============================
@app.context_processor
def inject_coming_soon_flag():
    return dict(show_coming_soon=True)
@app.route("/access", methods=["GET", "POST"])
def access_page():
    if request.method == "POST":
        code = request.form.get("code")
        if code == ACCESS_CODE:
            session["access_granted"] = True
            return redirect("/")
        else:
            return render_template("access.html", error=True)

    return render_template("access.html", error=False)

@app.route("/")
def home():
    return render_template("index.html")
@app.route("/set_nickname", methods=["POST"])
@login_required
def set_nickname():
    data = request.get_json()
    nickname = data.get("nickname", "").strip()

    if not nickname:
        return {"ok": False, "error": "Empty nickname"}

    # Έλεγχος αν υπάρχει ήδη
    exists = User.query.filter_by(nickname=nickname).first()
    if exists:
        return {"ok": False, "error": "Nickname already taken"}

    # Αν ο χρήστης έχει ήδη nickname → δεν αλλάζει
    if current_user.nickname:
        return {"ok": False, "error": "Nickname cannot be changed"}

    current_user.nickname = nickname
    db.session.commit()

    return {"ok": True}
@app.route("/submit_score", methods=["POST"])
def submit_score():
    data = request.get_json()
    nickname = data.get("nickname", "").strip()
    score = int(data.get("score", 0))
    time_played = int(data.get("time_played", 0))  # 🔥 ΠΑΙΡΝΟΥΜΕ ΤΟΝ ΧΡΟΝΟ

    if not nickname:
        return {"ok": False, "error": "No nickname"}

    entry = Score.query.filter_by(nickname=nickname).first()

    if entry:
        # Αν έχει καλύτερο σκορ, ενημερώνουμε και τον χρόνο
        if score > entry.best_score:
            entry.best_score = score
            entry.time_played = time_played   # 🔥 ΑΠΟΘΗΚΕΥΟΥΜΕ ΤΟΝ ΧΡΟΝΟ
            entry.last_played = datetime.utcnow()
            db.session.commit()
    else:
        new_entry = Score(
            nickname=nickname,
            best_score=score,
            time_played=time_played,          # 🔥 ΑΠΟΘΗΚΕΥΟΥΜΕ ΤΟΝ ΧΡΟΝΟ
            last_played=datetime.utcnow()
        )
        db.session.add(new_entry)
        db.session.commit()

    return {"ok": True}
@app.route("/top10")
def top10():
    top_players = Score.query.order_by(Score.best_score.desc()).limit(10).all()
    return render_template("top10.html", players=top_players)
from flask import send_from_directory

@app.route('/ai-image/<path:filename>')
def ai_image(filename):
    return send_from_directory('templates/images', filename)
@app.route('/favicon.ico')
def favicon():
    return send_from_directory('templates/images', 'logo3.png')
@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


@app.route("/cookies")
def cookies():
    return render_template("cookies.html")
from flask_login import login_required

@app.route("/ai")
@login_required
def ai():
    return render_template("ai/ai.html")
@app.route("/game")
@login_required
def game():
    return render_template("game.html")
@app.route("/timokatalogos")
def timokatalogos():
    return render_template("timokatalogos.html")


@app.route("/coupon/<int:coupon_id>")
@login_required
def coupon_details(coupon_id):
    coupon = Coupon.query.filter_by(id=coupon_id, user_id=current_user.id).first_or_404()
    return render_template("coupon_details.html", coupon=coupon, today=date.today())
@app.route("/admin/coupon/<int:id>/delete", methods=["POST"])
@login_required
def admin_delete_coupon(id):
    if not current_user.is_admin:
        return redirect("/")

    coupon = Coupon.query.get(id)
    if coupon:
        db.session.delete(coupon)
        db.session.commit()

    return redirect(f"/admin/users/{coupon.user_id}")
@app.route("/epikoinonia", methods=["POST"])
def contact_submit():
    name = request.form.get("name")
    email = request.form.get("email")
    subject = request.form.get("subject")
    message = request.form.get("message")

    # Αν είναι συνδεδεμένος χρήστης → αποθηκεύουμε user_id
    user_id = current_user.id if current_user.is_authenticated else None

    msg = ContactMessage(
        user_id=user_id,
        name=name,
        email=email,
        subject=subject,
        message=message
    )

    db.session.add(msg)
    db.session.commit()

    flash("Το μήνυμά σας στάλθηκε με επιτυχία!", "success")
    return redirect("/epikoinonia")
@app.route("/epikoinonia", methods=["GET", "POST"])
def epikoinonia():
    if request.method == "POST":
        name = request.form.get("name") if not current_user.is_authenticated else current_user.fullname
        email = request.form.get("email") if not current_user.is_authenticated else current_user.email
        subject = request.form.get("subject")
        message = request.form.get("message")

        user_id = current_user.id if current_user.is_authenticated else None

        msg = ContactMessage(
            user_id=user_id,
            name=name,
            email=email,
            subject=subject,
            message=message
        )

        db.session.add(msg)
        db.session.commit()

        # 🔥 ΠΟΛΥ ΣΗΜΑΝΤΙΚΟ: ΕΠΙΣΤΡΕΦΟΥΜΕ ΑΠΛΑ "OK"
        return "OK", 200

    return render_template("epikoinonia.html")
@app.route("/eidikes-ypiresies")
def eidikes_ypiresies():
    return render_template("eidikes-ypiresies.html")
@app.route("/admin/review/delete/<int:review_id>", methods=["POST"])
@login_required
def admin_delete_review(review_id):
    if not current_user.is_admin:
        return redirect("/")

    review = Review.query.get_or_404(review_id)
    db.session.delete(review)
    db.session.commit()

    return redirect("/admin/reviews")
@app.route("/kritikes")
def kritikes():
    return render_template("kritikes.html")
@app.route("/submit_review", methods=["POST"])
def submit_review():
    if current_user.is_authenticated:
        user_id = current_user.id
        name = current_user.fullname
    else:
        user_id = None
        name = "Όχι μέλος"

    new_review = Review(
        user_id=user_id,
        rating=request.form.get("rating"),
        q2=request.form.get("q2"),
        q3=request.form.get("q3"),
        q4=request.form.get("q4"),
        recommend=request.form.get("recommend"),
        comment_like=request.form.get("comment_like"),
        comment_improve=request.form.get("comment_improve"),
        name=name,
        want_contact=request.form.get("wantContact"),
        contact_info=request.form.get("contactInfo")
    )

    db.session.add(new_review)
    db.session.commit()

    return jsonify({"success": True})
@app.route("/admin/review/<int:review_id>")
@login_required
def admin_review_detail(review_id):
    if not current_user.is_admin:
        return redirect("/")

    review = Review.query.get(review_id)

    return render_template(
        "admin/review_detail.html",
        review=review,
        active_page="reviews"
    )
from datetime import datetime, timedelta, date

@app.route("/coupons")
@login_required
def user_coupons():
    # 1. Φέρνουμε τα κουπόνια του χρήστη
    coupons = Coupon.query.filter_by(user_id=current_user.id).order_by(Coupon.id.desc()).all()

    # 2. Αυτόματος καθαρισμός κουπονιών που χρησιμοποιήθηκαν πριν 15 μέρες
    limit = datetime.utcnow() - timedelta(days=15)
    old_used = Coupon.query.filter(
        Coupon.user_id == current_user.id,
        Coupon.used == True,
        Coupon.used_at < limit
    ).all()

    for c in old_used:
        db.session.delete(c)

    db.session.commit()

    # 3. Στέλνουμε στο template και τη σημερινή ημερομηνία
    return render_template("coupons.html", coupons=coupons, today=date.today())
@app.route("/admin/messages/<int:id>/delete", methods=["POST"])
@login_required
def admin_delete_message(id):
    if not current_user.is_admin:
        return redirect("/")

    msg = ContactMessage.query.get(id)
    if msg:
        db.session.delete(msg)
        db.session.commit()

    return redirect("/admin/messages")
@app.route("/admin/messages/<int:id>")
@login_required
def admin_message_view(id):
    if not current_user.is_admin:
        return redirect("/")

    msg = ContactMessage.query.get_or_404(id)

    return render_template("admin/message_view.html", m=msg)
@app.route("/admin/announcement/<int:id>/delete", methods=["POST"])
@login_required
def admin_delete_announcement(id):
    if not current_user.is_admin:
        return redirect("/")

    ann = Announcement.query.get(id)
    if ann:
        db.session.delete(ann)
        db.session.commit()

    # ΠΑΝΤΑ επιστροφή στη λίστα ανακοινώσεων
    return redirect("/admin/announcements/list")
@app.route("/fwtografies")
def fwtografies():
    return render_template("fwtografies.html")
@app.route("/admin/announcements")
@login_required
def admin_announcements():
    if not current_user.is_admin:
        return redirect("/")
    announcements = Announcement.query.all()
    return render_template("admin/announcements.html", announcements=announcements)
@app.route("/admin/messages")
@login_required
def admin_messages():
    if not current_user.is_admin:
        return redirect("/")

    messages = ContactMessage.query.order_by(ContactMessage.created_at.desc()).all()
    return render_template("admin/messages.html", messages=messages)


@app.route("/admin/coupons")
@login_required
def admin_coupons_page():
    if not current_user.is_admin:
        return redirect("/")

    users = User.query.all()
    return render_template("admin/coupons_send.html", users=users)
# ============================
#       REGISTER
# ============================

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    fullname = request.form["fullname"]
    email = request.form["email"]
    password = request.form["password"]
    confirm = request.form["confirm_password"]

    result = register_user(fullname, email, password, confirm)

    if result == "OK":
        # ===== EMAIL ΚΑΛΩΣΟΡΙΣΜΑΤΟΣ =====
        body = f"""
Αγαπητέ/ή {fullname},

Καλωσόρισες στην οικογένεια του Ariston Wash & Dry!

Η εγγραφή σου ολοκληρώθηκε με επιτυχία και πλέον είσαι επίσημα μέλος της υπηρεσίας μας.
Από σήμερα θα λαμβάνεις αποκλειστικές προσφορές, κουπόνια, εκπτώσεις και ενημερώσεις 
για νέες υπηρεσίες που ετοιμάζουμε για τα μέλη μας.

Στόχος μας είναι να κάνουμε το πλύσιμο και το στέγνωμα των ρούχων σου πιο εύκολα, 
πιο γρήγορα και πιο οικονομικά από ποτέ.

Σε ευχαριστούμε που μας εμπιστεύτηκες.
Αν χρειαστείς οτιδήποτε, είμαστε πάντα δίπλα σου.

Με εκτίμηση,
Η ομάδα του Ariston Wash & Dry

<a href="https://aristonwashdry.gr" target="_blank" style="text-decoration:none;">
<img src="https://aristonwashdry.gr/templates/images/1new.png"
alt="ARISTON Wash & Dry" style="height:100px; width:auto; margin-top:12px;">
</a>

<hr>
<p style='font-size: 12px; color: #666;'>
Το παρόν email στάλθηκε από το ARISTON Wash & Dry σύμφωνα με την 
<a href="https://aristonwashdry.gr/privacy">Πολιτική Απορρήτου</a>. 
Τα δεδομένα σας χρησιμοποιούνται αποκλειστικά για τη λειτουργία της υπηρεσίας 
και δεν κοινοποιούνται σε τρίτους.
</p>
"""
        

        send_email(
            to=email,
            subject="Καλωσόρισες στο Ariston Wash & Dry",
            body=body
        )
        # =================================

        flash("Ο λογαριασμός δημιουργήθηκε με επιτυχία! Μπορείτε τώρα να συνδεθείτε.", "success")
        return redirect("/login")

    else:
        return result


# ============================
#       LOGIN
# ============================
@app.route("/index")
@login_required
def index():
    return render_template("index.html")
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email")
    password = request.form.get("password")

    user = User.query.filter_by(email=email).first()

    if not user or not check_password_hash(user.password, password):
        flash("Λάθος email ή κωδικός.", "danger")
        return redirect("/login")

    # Αν ο χρήστης υπάρχει και ο κωδικός είναι σωστός
    login_user(user)

    # ===== ADMIN REDIRECT =====
    if user.is_admin:
        return redirect("/admin")
    # ==========================

    # Απλός χρήστης
    return redirect("/index")
@app.route("/profile")
@login_required
def profile():
    return render_template("profile.html")
@app.route("/change-name", methods=["GET", "POST"])
@login_required
def change_name():
    if request.method == "POST":
        new_name = request.form.get("fullname")

        if not new_name or new_name.strip() == "":
            flash("Το όνομα δεν μπορεί να είναι κενό.", "error")
            return redirect("/profile")

        current_user.fullname = new_name.strip()
        db.session.commit()

        flash("Το όνομα ενημερώθηκε με επιτυχία!", "success")
        return redirect("/profile")

    # Αν είναι GET request → δείξε τη φόρμα αλλαγής ονόματος
    return render_template("change_name.html")
@app.route("/admin/users")
@login_required
def admin_users():
    if not current_user.is_admin:
        return redirect("/")

    search = request.args.get("search", "").strip()

    query = User.query

    if search:
        search_like = f"%{search}%"
        query = query.filter(
            db.or_(
                User.email.ilike(search_like),
                User.fullname.ilike(search_like)  # αν έχεις πεδίο name
            )
        )

    users = query.order_by(User.id.desc()).all()

    return render_template(
        "admin/users.html",
        users=users,
        search=search,
        active_page="users"
    )
@app.route("/admin/users/<int:user_id>")
@login_required
def admin_user_profile(user_id):
    if not current_user.is_admin:
        return redirect("/")

    user = User.query.get(user_id)

    if not user:
        flash("Ο χρήστης δεν βρέθηκε.", "danger")
        return redirect("/admin/users")

    # 🔥 Φέρνουμε ΚΑΙ προσωπικές ΚΑΙ μαζικές ανακοινώσεις
    announcements = Announcement.query.filter(
        (Announcement.user_id == user.id) |
        (Announcement.user_id == None)
    ).order_by(Announcement.id.desc()).all()

    coupons = Coupon.query.filter_by(user_id=user.id).order_by(Coupon.id.desc()).all()

    return render_template(
        "admin/user_profile.html",
        user=user,
        announcements=announcements,
        coupons=coupons,
        active_page="users"
    )
# ============================
#  ΦΟΡΜΑ ΚΟΥΠΟΝΙΟΥ (GET)
# ============================
@app.route("/admin/users/<int:user_id>/coupon", methods=["GET"])
@login_required
def admin_coupon_form(user_id):
    if not current_user.is_admin:
        return redirect("/")

    user = User.query.get(user_id)
    if not user:
        flash("Ο χρήστης δεν βρέθηκε.", "danger")
        return redirect("/admin/users")

    return render_template(
        "admin/coupon_form.html",
        user=user,
        active_page="users"
    )


# ============================
#  ΑΠΟΣΤΟΛΗ ΚΟΥΠΟΝΙΟΥ (POST)
# ============================
@app.route("/admin/users/<int:user_id>/coupon", methods=["POST"])
@login_required
def admin_coupon_submit(user_id):
    if not current_user.is_admin:
        return redirect("/")

    user = User.query.get(user_id)
    if not user:
        flash("Ο χρήστης δεν βρέθηκε.", "danger")
        return redirect("/admin/users")

    title = request.form.get("title")
    description = request.form.get("description")
    amount = request.form.get("amount")
    start_date = request.form.get("start_date")
    end_date = request.form.get("end_date")

    coupon = Coupon(
        user_id=user.id,
        title=title,
        description=description,
        amount=float(amount),
        start_date=datetime.strptime(start_date, "%Y-%m-%d"),
        end_date=datetime.strptime(end_date, "%Y-%m-%d")
    )

    db.session.add(coupon)
    db.session.commit()
    send_coupon_email(user, coupon)

    flash("Το κουπόνι δημιουργήθηκε και στάλθηκε με email.", "success")
    return redirect(f"/admin/users/{user.id}")


# ============================
#  ΜΑΖΙΚΗ ΑΠΟΣΤΟΛΗ ΚΟΥΠΟΝΙΩΝ
# ============================
# ============================
#  ΜΑΖΙΚΗ ΑΠΟΣΤΟΛΗ ΚΟΥΠΟΝΙΩΝ (με φίλτρα)
# ============================
@app.route("/admin/coupons/send_filtered", methods=["POST"])
@login_required
def admin_send_coupons_filtered():
    if not current_user.is_admin:
        return redirect("/")

    filter_type = request.form.get("filter_type")
    users_query = User.query

    if filter_type == "1month":
        users_query = users_query.filter(User.created_at >= datetime.utcnow() - timedelta(days=30))
    elif filter_type == "3months":
        users_query = users_query.filter(User.created_at >= datetime.utcnow() - timedelta(days=90))
    elif filter_type == "6months":
        users_query = users_query.filter(User.created_at >= datetime.utcnow() - timedelta(days=180))

    users = users_query.all()

    title = request.form.get("title")
    description = request.form.get("description")
    amount = float(request.form.get("amount"))
    start_date = datetime.strptime(request.form.get("start_date"), "%Y-%m-%d")
    end_date = datetime.strptime(request.form.get("end_date"), "%Y-%m-%d")

    for user in users:
        coupon = Coupon(
            user_id=user.id,
            title=title,
            description=description,
            amount=amount,
            start_date=start_date,
            end_date=end_date
        )
        db.session.add(coupon)

    db.session.commit()

    flash("Τα κουπόνια στάλθηκαν επιτυχώς.", "success")
    return redirect("/admin/coupons")

@app.route("/admin/coupons/send", methods=["GET"])
@login_required
def admin_send_coupons_form():
    if not current_user.is_admin:
        return redirect("/")

    users = User.query.order_by(User.fullname.asc()).all()

    return render_template(
        "admin/send_coupons.html",
        users=users
    )
from datetime import datetime

import threading
import time

def send_coupons_background(users, title, description, amount, start_date, end_date):
    with app.app_context():  # 🔥 ΑΠΑΡΑΙΤΗΤΟ
        count = 0

        for user in users:
            try:
                if not user.email or user.email.strip() == "":
                    print(f"⚠️ SKIPPED: User {user.id} έχει άδειο email")
                    continue

                coupon = Coupon(
                    user_id=user.id,
                    title=title,
                    description=description,
                    amount=amount,
                    start_date=start_date,
                    end_date=end_date
                )

                db.session.add(coupon)
                db.session.flush()

                send_coupon_email(user, coupon)
                count += 1

                if count % 2 == 0:
                    time.sleep(1)

            except Exception as e:
                print(f"❌ ERROR sending coupon to user {user.id}: {e}")
                continue

        db.session.commit()


@app.route("/admin/coupons/send", methods=["POST"])
@login_required
def admin_send_coupons_selected():
    if not current_user.is_admin:
        return redirect("/")

    title = request.form.get("title")
    description = request.form.get("description")

    start_date = datetime.strptime(request.form.get("start_date"), "%Y-%m-%d").date()
    end_date = datetime.strptime(request.form.get("end_date"), "%Y-%m-%d").date()

    amount_raw = request.form.get("amount")
    amount = float(amount_raw) if amount_raw else 0.0

    selected_ids = request.form.getlist("selected_users")
    users = User.query.filter(User.id.in_(selected_ids)).all()

    # 🔥 Background thread
    threading.Thread(
        target=send_coupons_background,
        args=(users, title, description, amount, start_date, end_date),
        daemon=True
    ).start()

    flash("Η αποστολή κουπονιών ξεκίνησε στο παρασκήνιο.", "success")
    return redirect("/admin/coupons")













@app.route("/admin/reviews")
@login_required
def admin_reviews():
    if not current_user.is_admin:
        return redirect("/")

    rating_filter = request.args.get("rating", "all")

    query = Review.query.order_by(Review.created_at.desc())

    if rating_filter != "all":
        query = query.filter(Review.rating == int(rating_filter))

    reviews = query.all()

    return render_template(
        "admin/reviews.html",
        reviews=reviews,
        rating_filter=rating_filter,
        active_page="reviews"
    )


@app.route("/admin/users/<int:user_id>/delete", methods=["POST"])
@login_required
def admin_delete_user(user_id):
    if not current_user.is_admin:
        return redirect("/")

    user = User.query.get(user_id)

    if not user:
        flash("Ο χρήστης δεν βρέθηκε.", "danger")
        return redirect("/admin/users")

    # Ασφάλεια: ο admin δεν μπορεί να διαγράψει τον εαυτό του
    if user.id == current_user.id:
        flash("Δεν μπορείτε να διαγράψετε τον δικό σας λογαριασμό.", "danger")
        return redirect("/admin/users")

    # 🔥 Σβήνουμε πρώτα όλες τις ανακοινώσεις του χρήστη
    Announcement.query.filter_by(user_id=user.id).delete()

    # 🔥 Μετά σβήνουμε τον χρήστη
    db.session.delete(user)
    db.session.commit()

    flash("Ο χρήστης διαγράφηκε οριστικά.", "success")
    return redirect("/admin/users")
# ============================
#  ΦΟΡΜΑ ΑΝΑΚΟΙΝΩΣΗΣ (GET)
# ============================

@app.route("/admin/announcements/")
@login_required
def admin_announcements_page_slash():
    return redirect("/admin/announcements")
@app.route("/admin/users/<int:user_id>/announcement", methods=["POST"])
@login_required
def admin_announcement_submit(user_id):
    if not current_user.is_admin:
        return redirect("/")

    user = User.query.get(user_id)
    if not user:
        flash("Ο χρήστης δεν βρέθηκε.", "danger")
        return redirect("/admin/users")

    title = request.form.get("title")
    description = request.form.get("description")

    # Αποθήκευση στη βάση
    announcement = Announcement(
        user_id=user.id,
        title=title,
        description=description
    )
    db.session.add(announcement)
    db.session.commit()

    

    # Αποστολή email μέσω Resend
    subject = "Νέα ανακοίνωση από το ARISTON Wash & Dry"

    body = f"""
Αγαπητέ/ή {user.fullname},

Έχεις μία νέα ανακοίνωση επειδή είσαι μέλος του ARISTON Wash & Dry.

──────────────────────────────────
Τίτλος ανακοίνωσης:
{title}

Περιγραφή:
{description}
──────────────────────────────────

Δες τις ανακοινώσεις σου από εδώ:
https://aristonwashdry.gr/updates

Σε ευχαριστούμε που είσαι μέλος της οικογένειας ARISTON.

Με εκτίμηση,
ARISTON Wash & Dry
https://aristonwashdry.gr/
"""

    send_email(
        user.email,
        subject,
        body
    )

    flash("Η ανακοίνωση στάλθηκε επιτυχώς.", "success")
    return redirect(f"/admin/users/{user.id}")
@app.route("/admin/users/<int:user_id>/announcement", methods=["GET"])
@login_required
def admin_announcement_form(user_id):
    if not current_user.is_admin:
        return redirect("/")

    user = User.query.get(user_id)
    if not user:
        flash("Ο χρήστης δεν βρέθηκε.", "danger")
        return redirect("/admin/users")

    return render_template(
        "admin/announcement_form.html",
        user=user,
        active_page="users"
    )




# ============================
#  ΜΑΖΙΚΗ ΑΠΟΣΤΟΛΗ ΑΝΑΚΟΙΝΩΣΕΩΝ
# ============================
@app.route("/admin/announcements2", methods=["GET"])
@login_required
def admin_announcements_page():
    print("🔥 ROUTE ANNOUNCEMENTS LOADED")
    if not current_user.is_admin:
        return redirect("/")

    users = User.query.all()  # 🔥 Φέρνει όλους τους χρήστες
    return render_template(
        "admin/announcements.html",
        users=users,
        active_page="announcements"
    )
import threading
import time

def send_announcements_background(users, title, description):
    with app.app_context():  # 🔥 ΑΥΤΟ ΕΙΝΑΙ ΤΟ ΣΩΣΤΟ
        count = 0

        for user in users:
            try:
                if not user.email or user.email.strip() == "":
                    print(f"⚠️ SKIPPED: User {user.id} έχει άδειο email")
                    continue

                subject = "Νέα ανακοίνωση από το ARISTON Wash & Dry"
                body = f"""
Αγαπητέ/ή {user.fullname},

Υπάρχει μια νέα ανακοίνωση από το ARISTON Wash & Dry.

──────────────────────────────────
Τίτλος:
{title}

Περιγραφή:
{description}
──────────────────────────────────
Δες τις ανακοινώσεις σου απο εδώ: https://aristonwashdry.gr/updates

Με εκτίμηση,
ARISTON Wash & Dry
https://aristonwashdry.gr/

<a href="https://aristonwashdry.gr" target="_blank" style="text-decoration:none;"><img src="https://aristonwashdry.gr/templates/images/1new.png" alt="ARISTON Wash & Dry" style="height:100px; width:auto; margin-top:12px;"></a>
<hr>
<p style="font-size: 12px; color: #666;">
Το παρόν email στάλθηκε από το ARISTON Wash & Dry σύμφωνα με την 
<a href="https://aristonwashdry.gr/privacy">Πολιτική Απορρήτου</a>. 
Τα δεδομένα σας χρησιμοποιούνται αποκλειστικά για τη λειτουργία της υπηρεσίας 
και δεν κοινοποιούνται σε τρίτους.
</p>
"""

                send_email(user.email, subject, body)
                count += 1

                # Resend → 2 emails/sec
                if count % 2 == 0:
                    time.sleep(1)

            except Exception as e:
                print(f"❌ ERROR sending to user {user.id}: {e}")
                continue



@app.route("/admin/announcements2/send", methods=["POST"])
@login_required
def admin_send_announcements():
    if not current_user.is_admin:
        return redirect("/")

    title = request.form.get("title")
    description = request.form.get("description")
    selected_ids = request.form.getlist("selected_users")

    if not selected_ids:
        flash("Δεν επιλέχθηκαν χρήστες.", "danger")
        return redirect("/admin/announcements2")

    # Φέρνουμε τους επιλεγμένους χρήστες
    users = User.query.filter(User.id.in_(selected_ids)).all()

    announcements = []

    # Δημιουργούμε ΜΙΑ ανακοίνωση για κάθε χρήστη
    for user in users:
        announcement = Announcement(
            user_id=user.id,
            title=title,
            description=description
        )
        db.session.add(announcement)
        announcements.append(announcement)

    db.session.commit()

    
    # 🔥 Background thread για αποστολή email
    threading.Thread(
        target=send_announcements_background,
        args=(users, title, description),
        daemon=True
    ).start()

    flash("Η αποστολή ξεκίνησε στο παρασκήνιο.", "success")
    return redirect("/admin/announcements2")

@app.route("/admin/announcements/list")
@login_required
def admin_announcements_list():
    if not current_user.is_admin:
        return redirect("/")

    announcements = Announcement.query.order_by(Announcement.date.desc()).all()

    return render_template("admin/announcements_list.html", announcements=announcements)    
@app.route("/admin")
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        return redirect("/")

    total_users = User.query.count()
    total_coupons = Coupon.query.count()
    total_announcements = Announcement.query.count()
    total_reviews = Review.query.count()
    total_messages = ContactMessage.query.count()

    return render_template(
        "admin/dashboard.html",
        total_users=total_users,
        total_coupons=total_coupons,
        total_announcements=total_announcements,
        total_reviews=total_reviews,
        total_messages=total_messages,
        active_page="dashboard"
    )
@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form["email"]
        user = User.query.filter_by(email=email).first()

        if not user:
            flash("Το email δεν αντιστοιχεί σε κανέναν λογαριασμό.", "danger")
            return redirect("/forgot-password")

        code = random.randint(100000, 999999)
        user.reset_code = str(code)
        db.session.commit()

        body = f"""
Αγαπητέ/ή {user.fullname},

Λάβαμε αίτημα για επαναφορά του κωδικού πρόσβασής σας στο ARISTON Wash & Dry.

Για να συνεχίσετε, χρησιμοποιήστε τον παρακάτω 6ψήφιο κωδικό επαλήθευσης:

{code}

Ο κωδικός ισχύει για περιορισμένο χρονικό διάστημα.

Αν δεν ζητήσατε εσείς την επαναφορά, μπορείτε να αγνοήσετε αυτό το μήνυμα.

Με εκτίμηση,
Η ομάδα του ARISTON Wash & Dry

<a href="https://aristonwashdry.gr" target="_blank" style="text-decoration:none;">
    <img src="https://aristonwashdry.gr/templates/images/1new.png"
         alt="ARISTON Wash & Dry"
         style="height:100px; width:auto; margin-top:12px;">
</a>
<hr>
<p style="font-size: 12px; color: #666;">
Το παρόν email στάλθηκε από το ARISTON Wash & Dry σύμφωνα με την 
<a href="https://aristonwashdry.gr/privacy">Πολιτική Απορρήτου</a>. 
Τα δεδομένα σας χρησιμοποιούνται αποκλειστικά για τη λειτουργία της υπηρεσίας 
και δεν κοινοποιούνται σε τρίτους.
</p>
"""

        send_email(
            to=email,
            subject="Κωδικός Επαλήθευσης - ARISTON Wash & Dry",
            body=body
        )

        return redirect("/verify-code")

    return render_template("forgot-password.html")

    
@app.route("/goodbye")
def goodbye():
    return render_template("goodbye.html")
@app.route("/verify-code", methods=["GET", "POST"])
def verify_code():
    if request.method == "POST":
        code = request.form["code"]
        user = User.query.filter_by(reset_code=code).first()

        if not user:
            flash("Λάθος κωδικός.")
            return redirect("/verify-code")

        session["reset_user_id"] = user.id
        return redirect("/reset-password")

    return render_template("verify-code.html")
@app.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    if request.method == "POST":
        password = request.form["password"]
        confirm = request.form["confirm"]

        if password != confirm:
            flash("Οι κωδικοί δεν ταιριάζουν.")
            return redirect("/reset-password")

        user = User.query.get(session["reset_user_id"])
        user.password = generate_password_hash(password)
        user.reset_code = None
        db.session.commit()

        flash("Ο κωδικός άλλαξε με επιτυχία!")
        return redirect("/login")

    return render_template("reset-password.html")
# ============================
#       LOGOUT
# ============================

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/")

@app.route("/updates-menu")
@login_required
def updates_menu():
    return render_template("updates-menu.html")

@app.route("/admin/coupon/<int:id>/use", methods=["POST"])
@login_required
def admin_use_coupon(id):
    if not current_user.is_admin:
        return redirect("/")

    coupon = Coupon.query.get(id)
    if not coupon:
        return redirect("/admin/users")

    coupon.used = True
    coupon.used_at = datetime.utcnow()

    db.session.commit()

    return redirect(f"/admin/users/{coupon.user_id}")
@app.route("/updates")
@login_required
def updates():
    announcements = Announcement.query.filter(
        (Announcement.user_id == None) |
        (Announcement.user_id == current_user.id)
    ).order_by(Announcement.id.desc()).all()

    return render_template("updates.html", announcements=announcements)
@app.route("/announcement/<int:announcement_id>")
@login_required
def announcement_view(announcement_id):
    announcement = Announcement.query.filter(
        (Announcement.id == announcement_id) &
        ((Announcement.user_id == None) | (Announcement.user_id == current_user.id))
    ).first_or_404()

    return render_template("announcement_view.html", announcement=announcement)



# ============================
#       MEMBER PAGES
# ============================

@app.route("/settings")
@login_required
def settings():
    from datetime import datetime
    days_member = (datetime.now() - current_user.created_at).days
    return render_template("settings.html", days_member=days_member)
@app.route("/account-settings")
@login_required
def account_settings():
    return render_template("account-settings.html")
@app.route("/settings-menu")
@login_required
def settings_menu():
    return render_template("settings-menu.html")
@app.route("/member-info")
@login_required
def member_info():
    from datetime import datetime
    days_member = (datetime.now() - current_user.created_at).days
    return render_template("member-info.html", days_member=days_member)

from datetime import datetime, timedelta
from flask import render_template, request, redirect, flash
from flask_login import login_required, current_user, logout_user

@app.route("/delete-account", methods=["GET", "POST"])
@login_required
def delete_account():
    if request.method == "GET":
        return render_template("delete-account.html")

    email = request.form.get("email")
    password = request.form.get("password")

    # 1) Έλεγχος email
    if email != current_user.email:
        flash("Το email δεν ταιριάζει με το λογαριασμό σας.", "danger")
        return redirect("/delete-account")

    # 2) Έλεγχος κωδικού
    if not check_password_hash(current_user.password, password):
        flash("Ο κωδικός δεν είναι σωστός.", "danger")
        return redirect("/delete-account")

    # 3) Αποστολή επίσημου email διαγραφής με ΟΝΟΜΑ ΧΡΗΣΤΗ
    body = f"""
Αγαπητέ/ή {current_user.fullname},

Ο λογαριασμός σας στο ARISTON Wash & Dry διαγράφηκε οριστικά.
Όλα τα προσωπικά σας δεδομένα, οι ρυθμίσεις και το ιστορικό χρήσης 
έχουν αφαιρεθεί από το σύστημά μας σύμφωνα με την πολιτική απορρήτου.

Δεν είστε πλέον μέλος της υπηρεσίας.

Ευχαριστούμε που χρησιμοποιήσατε το ARISTON Wash & Dry.
https://aristonwashdry.gr/

<a href="https://aristonwashdry.gr" target="_blank" style="text-decoration:none;">
<img src="https://aristonwashdry.gr/templates/images/1new.png"
alt="ARISTON Wash & Dry" style="height:100px; width:auto; margin-top:12px;">
</a>

<hr>
<p style='font-size: 12px; color: #666;'>
Το παρόν email στάλθηκε από το ARISTON Wash & Dry σύμφωνα με την 
<a href="https://aristonwashdry.gr/privacy">Πολιτική Απορρήτου</a>. 
Τα δεδομένα σας χρησιμοποιούνται αποκλειστικά για τη λειτουργία της υπηρεσίας 
και δεν κοινοποιούνται σε τρίτους.
</p>
"""

    send_email(
        to=current_user.email,
        subject="Επιβεβαίωση Διαγραφής Λογαριασμού - ARISTON Wash & Dry",
        body=body
    )

    # 4) Αποθήκευση ID πριν το logout
    user_id = current_user.id

    # 5) Logout
    logout_user()

    # 6) 🔥 Σβήνουμε πρώτα ΟΛΑ τα κουπόνια του χρήστη
    Coupon.query.filter_by(user_id=user_id).delete()

    # 7) 🔥 Σβήνουμε όλες τις ανακοινώσεις του χρήστη
    Announcement.query.filter_by(user_id=user_id).delete()

    # 8) 🔥 Τώρα σβήνουμε τον χρήστη
    user = User.query.get(user_id)
    db.session.delete(user)
    db.session.commit()

    flash("Ο λογαριασμός σας διαγράφηκε οριστικά.", "success")
    return redirect("/goodbye")
@app.route("/change-email", methods=["GET", "POST"])
@login_required
def change_email():
    if request.method == "POST":
        new_email = request.form.get("new_email")
        password_confirm = request.form.get("password_confirm")

        if not check_password_hash(current_user.password, password_confirm):
            flash("Ο κωδικός δεν είναι σωστός.", "danger")
            return redirect("/change-email")

        current_user.email = new_email
        db.session.commit()

        flash("Το email ενημερώθηκε επιτυχώς.", "success")
        return redirect("/change-email")   # ⭐ ΕΔΩ Η ΑΛΛΑΓΗ

    return render_template("change-email.html")


def send_password_change_email(user):
    subject = "Η αλλαγή κωδικού ολοκληρώθηκε"
    content = f"""
Αγαπητέ/ή {user.fullname},

Ο κωδικός πρόσβασής σου στο ARISTON Wash & Dry άλλαξε με επιτυχία.

Αν δεν έκανες εσύ αυτή την αλλαγή, επικοινώνησε άμεσα μαζί μας.

Με εκτίμηση,
Η ομάδα του ARISTON Wash & Dry

<a href="https://aristonwashdry.gr" target="_blank" style="text-decoration:none;">
    <img src="https://aristonwashdry.gr/templates/images/1new.png"
         alt="ARISTON Wash & Dry"
         style="height:100px; width:auto; margin-top:12px;">
</a>
<hr>
<p style="font-size: 12px; color: #666;">
Το παρόν email στάλθηκε από το ARISTON Wash & Dry σύμφωνα με την 
<a href="https://aristonwashdry.gr/privacy">Πολιτική Απορρήτου</a>. 
Τα δεδομένα σας χρησιμοποιούνται αποκλειστικά για τη λειτουργία της υπηρεσίας 
και δεν κοινοποιούνται σε τρίτους.
</p>
"""

    send_email(
        to=user.email,
        subject=subject,
        body=content   # ⭐ ΕΔΩ Η ΔΙΟΡΘΩΣΗ
    )

@app.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        old_password = request.form.get("old_password")
        new_password = request.form.get("new_password")
        confirm_new_password = request.form.get("confirm_new_password")

        if not check_password_hash(current_user.password, old_password):
            flash("Ο παλιός κωδικός δεν είναι σωστός.", "danger")
            return redirect("/change-password")

        if new_password != confirm_new_password:
            flash("Οι νέοι κωδικοί δεν ταιριάζουν.", "danger")
            return redirect("/change-password")

        current_user.password = generate_password_hash(new_password)
        db.session.commit()

        # ⭐ ΣΤΕΛΝΟΥΜΕ EMAIL ΕΠΙΒΕΒΑΙΩΣΗΣ
        send_password_change_email(current_user)

        flash("Ο κωδικός ενημερώθηκε επιτυχώς.", "success")
        return redirect("/change-password")

    return render_template("change-password.html")

######APOSTOLHMAIL####
import threading
import time

def send_bulk_email_background(users, subject, message):
    count = 0

    for user in users:
        try:
            if not user.email or user.email.strip() == "":
                print(f"⚠️ SKIPPED: User {user.id} έχει άδειο email")
                continue

            body = f"""
Αγαπητέ/ή {user.fullname},

{message}

──────────────────────────────────
Με εκτίμηση,
ARISTON Wash & Dry
https://aristonwashdry.gr/

<a href="https://aristonwashdry.gr" target="_blank" style="text-decoration:none;">
<img src="https://aristonwashdry.gr/templates/images/1new.png"
alt="ARISTON Wash & Dry"
style="height:100px; width:auto; margin-top:12px;">
</a>
<hr>
<p style="font-size: 12px; color: #666;">
Το παρόν email στάλθηκε από το ARISTON Wash & Dry σύμφωνα με την 
<a href="https://aristonwashdry.gr/privacy">Πολιτική Απορρήτου</a>. 
Τα δεδομένα σας χρησιμοποιούνται αποκλειστικά για τη λειτουργία της υπηρεσίας 
και δεν κοινοποιούνται σε τρίτους.
</p>
"""

            send_email(user.email, subject, body)
            count += 1

            # 2 emails/sec
            if count % 2 == 0:
                time.sleep(1)

        except Exception as e:
            print(f"❌ ERROR sending to user {user.id}: {e}")
            continue
@app.route("/admin/bulk-email/send", methods=["POST"])
@login_required
def admin_send_bulk_email():
    if not current_user.is_admin:
        return redirect("/")

    subject = request.form.get("subject")
    message = request.form.get("message")
    selected_ids = request.form.getlist("selected_users")

    if not selected_ids:
        flash("Δεν επιλέχθηκαν χρήστες.", "danger")
        return redirect("/admin/bulk-email")

    users = User.query.filter(User.id.in_(selected_ids)).all()

    # 🔥 Background thread (όπως οι ανακοινώσεις)
    threading.Thread(
        target=send_bulk_email_background,
        args=(users, subject, message),
        daemon=True
    ).start()

    flash("Η αποστολή ξεκίνησε στο παρασκήνιο.", "success")
    return redirect("/admin/bulk-email")
@app.route("/admin/bulk-email")
@login_required
def admin_bulk_email():
    if not current_user.is_admin:
        return redirect("/")

    users = User.query.all()
    return render_template("admin/bulk-email.html", users=users, active_page="bulk_email")
@app.route("/auth_choice")
def auth_choice():
    return render_template("auth_choice.html")
@app.route("/site-review", methods=["GET", "POST"])
def site_review():
    if request.method == "POST":
        try:
            review = siteReview(
                q1=request.form.get("q1"),
                q2=request.form.get("q2"),
                q3=request.form.get("q3"),
                q4=request.form.get("q4"),
                q5=request.form.get("q5"),
                t1=request.form.get("t1"),
                t2=request.form.get("t2"),
                t3=request.form.get("t3"),
                t4=request.form.get("t4"),
                t5=request.form.get("t5"),
                email=request.form.get("email"),
                phone=request.form.get("phone")
            )

            db.session.add(review)
            db.session.commit()

            return jsonify({"status": "ok"})
        except Exception as e:
            print("⚠️ ERROR:", e)
            return jsonify({"status": "error", "message": str(e)}), 500

    return render_template("sitereview.html")
@app.route("/admin/reviews_site")
@login_required
def admin_reviews_site():
    if not current_user.is_admin:
        return redirect("/")
    
    reviews = siteReview.query.order_by(siteReview.created_at.desc()).all()
    return render_template("admin/admin_reviews_site.html", reviews=reviews)
@app.route("/admin/review/<int:review_id>")
@login_required
def admin_review_details(review_id):
    if not session.get("admin_logged_in"):
        return redirect("/admin/login")

    review = siteReview.query.get_or_404(review_id)
    return render_template("admin_review_details_site.html", review=review)
@app.route("/admin/review_site/<int:review_id>")
@login_required
def admin_review_details_site(review_id):
    if not current_user.is_admin:
        return redirect("/")
    
    review = siteReview.query.get_or_404(review_id)
    return render_template("admin/admin_review_details_site.html", review=review)
@app.route("/admin/review_site/delete/<int:review_id>", methods=["POST"])
@login_required
def delete_review_site(review_id):
    if not current_user.is_admin:
        return redirect("/")

    review = siteReview.query.get_or_404(review_id)
    db.session.delete(review)
    db.session.commit()

    return redirect("/admin/reviews_site")









#####AGGLIKA####
# Αγγλική έκδοση αρχικής
@app.route("/en")
def en_index():
    return render_template("en/index.html")
@app.route("/en/index")
@login_required
def home_en_index():
    return render_template("en/index.html")
@app.route("/en/auth_choice_en")
def auth_choice_en():
    return render_template("en/auth_choice_en.html")



# Αγγλική έκδοση Terms / Όροι Χρήσης
@app.route("/en/terms")
def en_terms():
    return render_template("en/terms.html")
@app.route("/en/photos")
def en_photos():
    return render_template("en/photos.html")
# Αγγλική έκδοση Privacy / Πολιτική Απορρήτου
@app.route("/en/privacy")
def en_privacy():
    return render_template("en/privacy.html")

# Αγγλική έκδοση Cookies / Πολιτική Cookies
@app.route("/en/cookies")
def en_cookies():
    return render_template("en/cookies.html")
@app.route("/en/pricing")
def en_pricing():
    return render_template("en/pricing.html")
@app.route("/en/special-services")
def en_special_services():
    return render_template("en/special-services.html")
# Αγγλική σελίδα κριτικών
@app.route("/en/reviews")
def reviews_en():
    return render_template("en/reviews.html")

# Υποβολή φόρμας (χρησιμοποιεί το ίδιο POST route, αν θέλεις να ξεχωρίζεις μπορεί να φτιάξεις /en/submit_review)
@app.route("/en/submit_review", methods=["POST"])
def submit_review_en():
    if current_user.is_authenticated:
        user_id = current_user.id
        name = current_user.fullname
    else:
        user_id = None
        name = "Guest"

    new_review = Review(
        user_id=user_id,
        rating=request.form.get("rating"),
        q2=request.form.get("q2"),
        q3=request.form.get("q3"),
        q4=request.form.get("q4"),
        recommend=request.form.get("recommend"),
        comment_like=request.form.get("comment_like"),
        comment_improve=request.form.get("comment_improve"),
        name=name,
        want_contact=request.form.get("wantContact"),
        contact_info=request.form.get("contactInfo")
    )

    db.session.add(new_review)
    db.session.commit()

    return jsonify({"success": True})

@app.route("/en/contact", methods=["GET", "POST"])
def contact_en():
    if request.method == "POST":
        name = current_user.fullname if current_user.is_authenticated else request.form.get("name")
        email = current_user.email if current_user.is_authenticated else request.form.get("email")
        subject = request.form.get("subject")
        message = request.form.get("message")

        user_id = current_user.id if current_user.is_authenticated else None

        msg = ContactMessage(
            user_id=user_id,
            name=name,
            email=email,
            subject=subject,
            message=message
        )

        db.session.add(msg)
        db.session.commit()
        return "OK", 200

    return render_template("en/contact.html")

@app.route("/en/login", methods=["GET", "POST"])
def login_en():
    if request.method == "GET":
        return render_template("en/login.html")

    email = request.form.get("email")
    password = request.form.get("password")

    user = User.query.filter_by(email=email).first()

    if not user or not check_password_hash(user.password, password):
        flash("Wrong email or password.", "danger")
        return redirect("/en/login")

    # Αν ο χρήστης υπάρχει και ο κωδικός είναι σωστός
    login_user(user)

    # ===== ADMIN REDIRECT =====
    if user.is_admin:
        return redirect("/admin")
    # ==========================

    # Regular user
    return redirect("/en/index")
@app.route("/en/register", methods=["GET", "POST"])
def register_en():
    if request.method == "GET":
        return render_template("en/register.html")

    fullname = request.form["fullname"]
    email = request.form["email"]
    password = request.form["password"]
    confirm = request.form["confirm_password"]

    result = register_user(fullname, email, password, confirm)

    if result == "OK":
        # Welcome email in English
        body = f"""
Dear {fullname},

Welcome to the Ariston Wash & Dry family!

Your registration has been successfully completed and you are now officially a member of our service.
From today, you will receive exclusive offers, coupons, discounts, and updates 
about new services we are preparing for our members.

Our goal is to make your laundry experience easier, faster, and more affordable than ever.

Thank you for trusting us.
If you need anything, we are always here for you.

Best regards,
The ARISTON Wash & Dry Team

<a href="https://aristonwashdry.gr" target="_blank" style="text-decoration:none;">
<img src="https://aristonwashdry.gr/templates/images/1new.png"
alt="ARISTON Wash & Dry" style="height:100px; width:auto; margin-top:12px;">
</a>

<hr>
<p style='font-size: 12px; color: #666;'>
This email was sent by ARISTON Wash & Dry in accordance with our 
<a href="https://aristonwashdry.gr/en/privacy">Privacy Policy</a>. 
Your data is used exclusively for service purposes and is not shared with third parties.
</p>
"""
        
        send_email(
            to=email,
            subject="Welcome to Ariston Wash & Dry",
            body=body
        )

        flash("Your account has been successfully created! You can now log in.", "success")
        return redirect("/en/login")

    else:
        return result
@app.route("/en/forgot-password", methods=["GET", "POST"])
def forgot_password_en():
    if request.method == "POST":
        email = request.form["email"]
        user = User.query.filter_by(email=email).first()

        if not user:
            flash("No account found with this email.", "danger")
            return redirect("/en/forgot-password")

        code = random.randint(100000, 999999)
        user.reset_code = str(code)
        db.session.commit()

        body = f"""
Dear {user.fullname},

We received a request to reset your password for ARISTON Wash & Dry.

To continue, please use the 6-digit verification code below:

{code}

The code is valid for a limited time.

If you did not request a password reset, you can safely ignore this email.

Best regards,
The ARISTON Wash & Dry Team

<a href="https://aristonwashdry.gr" target="_blank" style="text-decoration:none;">
    <img src="https://aristonwashdry.gr/templates/images/1new.png"
         alt="ARISTON Wash & Dry"
         style="height:100px; width:auto; margin-top:12px;">
</a>
<hr>
<p style="font-size: 12px; color: #666;">
This email was sent by ARISTON Wash & Dry in accordance with our 
<a href="https://aristonwashdry.gr/en/privacy">Privacy Policy</a>. 
Your data is used exclusively for service purposes and is not shared with third parties.
</p>
"""

        send_email(
            to=email,
            subject="Verification Code - ARISTON Wash & Dry",
            body=body
        )

        return redirect("/en/verify-code")

    return render_template("en/forgot-password.html")
@app.route("/en/settings-menu")
@login_required
def en_settings_menu():
    return render_template("en/settings-menu.html")

@app.route("/en/verify-code", methods=["GET", "POST"])
def verify_code_en():
    if request.method == "POST":
        code = request.form["code"]
        user = User.query.filter_by(reset_code=code).first()

        if not user:
            flash("Wrong code.", "danger")
            return redirect("/en/verify-code")

        session["reset_user_id"] = user.id
        return redirect("/en/reset-password")

    return render_template("en/verify-code.html")

@app.route("/en/reset-password", methods=["GET", "POST"])
def reset_password_en():
    if request.method == "POST":
        password = request.form["password"]
        confirm = request.form["confirm"]

        if password != confirm:
            flash("Passwords do not match.", "danger")
            return redirect("/en/reset-password")

        user = User.query.get(session["reset_user_id"])
        user.password = generate_password_hash(password)
        user.reset_code = None
        db.session.commit()

        flash("Password changed successfully!")
        return redirect("/en/login")

    return render_template("en/reset-password.html")
@app.route("/en/member-info")
@login_required
def member_info_en():
    from datetime import datetime
    days_member = (datetime.now() - current_user.created_at).days
    return render_template("en/member-info.html", days_member=days_member)
@app.route("/en/account-settings")
@login_required
def account_settings_en():
    return render_template("en/account-settings.html")
@app.route("/en/change-name", methods=["GET", "POST"])
@login_required
def change_name_en():
    if request.method == "POST":
        new_name = request.form.get("fullname")

        if not new_name or new_name.strip() == "":
            flash("Name cannot be empty.", "error")
            return redirect("/en/change-name")

        current_user.fullname = new_name.strip()
        db.session.commit()

        flash("Name updated successfully!", "success")
        return redirect("/en/account-settings")

    return render_template("en/change-name.html")
@app.route("/en/change-email", methods=["GET", "POST"])
@login_required
def change_email_en():
    if request.method == "POST":
        new_email = request.form.get("new_email")
        password_confirm = request.form.get("password_confirm")

        if not check_password_hash(current_user.password, password_confirm):
            flash("Password is incorrect.", "danger")
            return redirect("/en/change-email")

        current_user.email = new_email
        db.session.commit()

        flash("Email updated successfully.", "success")
        return redirect("/en/account-settings")

    return render_template("en/change-email.html")

def send_password_change_email_en(user):
    subject = "Password Change Completed"
    content = f"""
Dear {user.fullname},

Your password at ARISTON Wash & Dry has been changed successfully.

If you did not make this change, please contact us immediately.

Best regards,
The ARISTON Wash & Dry Team

<a href="https://aristonwashdry.gr" target="_blank" style="text-decoration:none;">
    <img src="https://aristonwashdry.gr/templates/images/1new.png"
         alt="ARISTON Wash & Dry"
         style="height:100px; width:auto; margin-top:12px;">
</a>
<hr>
<p style="font-size: 12px; color: #666;">
This email was sent by ARISTON Wash & Dry according to our 
<a href="https://aristonwashdry.gr/en/privacy">Privacy Policy</a>. 
Your data is used solely for service purposes and is not shared with third parties.
</p>
"""
    send_email(
        to=user.email,
        subject=subject,
        body=content
    )

@app.route("/en/change-password", methods=["GET", "POST"])
@login_required
def change_password_en():
    if request.method == "POST":
        old_password = request.form.get("old_password")
        new_password = request.form.get("new_password")
        confirm_new_password = request.form.get("confirm_new_password")

        if not check_password_hash(current_user.password, old_password):
            flash("Old password is incorrect.", "danger")
            return redirect("/en/change-password")

        if new_password != confirm_new_password:
            flash("New passwords do not match.", "danger")
            return redirect("/en/change-password")

        current_user.password = generate_password_hash(new_password)
        db.session.commit()

        # Send confirmation email
        send_password_change_email_en(current_user)

        flash("Password updated successfully.", "success")
        return redirect("/en/account-settings")

    return render_template("en/change-password.html")
@app.route("/en/delete-account", methods=["GET", "POST"])
@login_required
def delete_account_en():
    if request.method == "GET":
        return render_template("en/delete-account-en.html")

    email = request.form.get("email")
    password = request.form.get("password")

    # 1) Email check
    if email != current_user.email:
        flash("Email does not match your account.", "danger")
        return redirect("/en/delete-account")

    # 2) Password check
    if not check_password_hash(current_user.password, password):
        flash("Password is incorrect.", "danger")
        return redirect("/en/delete-account")

    # 3) Send confirmation email
    body = f"""
Dear {current_user.fullname},

Your account on ARISTON Wash & Dry has been permanently deleted.
All your personal data, settings, and usage history have been removed
from our system according to our privacy policy.

You are no longer a member of the service.

Thank you for using ARISTON Wash & Dry.
https://aristonwashdry.gr/

<a href="https://aristonwashdry.gr" target="_blank" style="text-decoration:none;">
<img src="https://aristonwashdry.gr/templates/images/1new.png"
alt="ARISTON Wash & Dry" style="height:100px; width:auto; margin-top:12px;">
</a>

<hr>
<p style='font-size: 12px; color: #666;'>
This email was sent by ARISTON Wash & Dry in accordance with the 
<a href="https://aristonwashdry.gr/privacy">Privacy Policy</a>. 
Your data is used solely for the operation of the service and is not shared with third parties.
</p>
"""
    send_email(
        to=current_user.email,
        subject="Account Deletion Confirmation - ARISTON Wash & Dry",
        body=body
    )

    # 4) Save ID & logout
    user_id = current_user.id
    logout_user()

    # 5) Delete user data
    Coupon.query.filter_by(user_id=user_id).delete()
    Announcement.query.filter_by(user_id=user_id).delete()
    user = User.query.get(user_id)
    db.session.delete(user)
    db.session.commit()

    flash("Your account has been permanently deleted.", "success")
    return redirect("/en/goodbye")


@app.route("/en/goodbye")
def goodbye_en():
    return render_template("en/goodbye-en.html")



@app.route("/en/updates-menu-en")
@login_required
def updates_menu_en():
    return render_template("en/updates-menu-en.html")
@app.route("/en/updates")
@login_required
def updates_en():
    announcements = Announcement.query.filter(
        (Announcement.user_id == None) |
        (Announcement.user_id == current_user.id)
    ).order_by(Announcement.id.desc()).all()
    return render_template("en/updates-en.html", announcements=announcements)


@app.route("/en/coupons")
@login_required
def user_coupons_en():
    coupons = Coupon.query.filter_by(user_id=current_user.id).order_by(Coupon.id.desc()).all()
    limit = datetime.utcnow() - timedelta(days=15)
    old_used = Coupon.query.filter(
        Coupon.user_id == current_user.id,
        Coupon.used == True,
        Coupon.used_at < limit
    ).all()
    for c in old_used:
        db.session.delete(c)
    db.session.commit()
    return render_template("en/coupons-en.html", coupons=coupons, today=date.today())
@app.route("/en/ai")
@login_required
def ai_en():
    return render_template("en/ai/ai.html")

from flask import send_from_directory

@app.route('/templates/en/ai/<path:filename>')
def custom_static(filename):
    return send_from_directory('templates/en/ai', filename)
@app.route("/en/site-review", methods=["GET", "POST"])
def site_review_en():
    if request.method == "POST":
        try:
            review = siteReview(
                q1=request.form.get("q1"),
                q2=request.form.get("q2"),
                q3=request.form.get("q3"),
                q4=request.form.get("q4"),
                q5=request.form.get("q5"),
                t1=request.form.get("t1"),
                t2=request.form.get("t2"),
                t3=request.form.get("t3"),
                t4=request.form.get("t4"),
                t5=request.form.get("t5"),
                email=request.form.get("email"),
                phone=request.form.get("phone")
            )

            db.session.add(review)
            db.session.commit()

            return jsonify({"status": "ok"})
        except Exception as e:
            print("⚠️ ERROR:", e)
            return jsonify({"status": "error", "message": str(e)}), 500

    return render_template("en/sitereview.html")




# ============================
#       RUN APP
# ============================

if __name__ == "__main__":
    app.run(debug=True)

