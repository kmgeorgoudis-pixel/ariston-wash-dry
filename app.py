import os
from flask import Flask, render_template, request, redirect, flash, session, jsonify, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from email.header import Header
from database import db, init_db
from database import Review
from database import siteReview



from datetime import datetime, timedelta
from flask_migrate import Migrate
from flask_login import LoginManager, login_user, logout_user, login_required, current_user

from database import db, init_db, User, Coupon, Announcement, Review, ContactMessage, Score, Verification
import random
import smtplib
import time
from email.mime.text import MIMEText
from email.message import EmailMessage
from functools import wraps
from flask import redirect, session, flash
import hashlib

def get_secure_hash(user_id):
    # Αυτό το "αλάτι" κάνει το link μοναδικό για το δικό σου site
    salt = "ARISTON_WASH_DRY_2026_SECRET" 
    # Δημιουργεί ένα μοναδικό κείμενο από το ID
    return hashlib.sha256(f"{user_id}{salt}".encode()).hexdigest()[:16]


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("Πρέπει να συνδεθείς.", "warning")
            return redirect("/login")
        if not current_user.is_admin:
            flash("Δεν έχεις δικαιώματα Admin.", "danger")
            return redirect("/")
        return f(*args, **kwargs)
    return decorated_function

# === REGISTER FUNCTION ===
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

# ==========================================
# 1. ΡΥΘΜΙΣΕΙΣ ΒΑΣΗΣ (PERSISTENT DISK)
# ==========================================
# Ελέγχουμε αν υπάρχει ο φάκελος /data (που ορίσαμε στο Render Disk)
if os.path.exists("/data"):
    # Χρήση του μόνιμου Disk
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:////data/users.db"
    print("RUNNING ON RENDER - PERSISTENT DISK ENABLED")
else:
    # Τοπική χρήση στο PC σου
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///users.db"
    print("RUNNING LOCALLY - LOCAL SQLITE ENABLED")

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# 2. Μετά το initialization της βάσης
init_db(app)
migrate = Migrate(app, db)

# 3. ΤΕΛΕΥΤΑΙΟ το create_all()
with app.app_context():
    db.create_all()
    print("Οι πίνακες δημιουργήθηκαν με επιτυχία!")

# === Login Manager ===
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

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
https://aristonwashdry.gr

<a href="https://aristonwashdry.gr" target="_blank" style="text-decoration:none;"><img src="https://aristonwashdry.gr/templates/images/1new.png" alt="ARISTON Wash & Dry" style="height:100px; width:auto; margin-top:12px;"></a>


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




from email.message import EmailMessage

import requests


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
@app.route("/subadmin/messages")
@login_required
def subadmin_messages():
    # Έλεγχος αν είναι Admin ή Sub-Admin
    if not (current_user.is_admin or current_user.is_sub_admin):
        return redirect("/")

    messages = ContactMessage.query.order_by(ContactMessage.created_at.desc()).all()
    return render_template("subadmin/messages.html", messages=messages)


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
        # ===== EMAIL ΚΑΛΩΣΟΡΙΣΜΑΤΟΣ (HTML VERSION) =====
        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2 style="color: #0056b3;">Καλωσόρισες στην οικογένεια του Ariston Wash & Dry! ✨</h2>
            <p>Αγαπητέ/ή <strong>{fullname}</strong>,</p>
            <p>Καλωσόρισες στην επίσημη κοινότητα του <strong>Ariston Wash & Dry</strong>! Η εγγραφή σου ολοκληρώθηκε με επιτυχία και πλέον έχεις πρόσβαση σε έναν κόσμο προνομίων και ψηφιακών ευκολιών.</p>
            
            <h3 style="border-bottom: 2px solid #eee; padding-bottom: 5px;">🚀 Έξυπνη Εξυπηρέτηση & Διασκέδαση</h3>
            <ul>
                <li><strong>Ariston AI Assistant:</strong> Ο δικός σου ψηφιακός βοηθός για κάθε απορία: <a href="https://aristonwashdry.gr/ai">aristonwashdry.gr/ai</a></li>
                <li><strong>Ariston Game:</strong> Διασκέδασε και παιξέ το παιχνίδι πιάσε τον λεκέ ίσως φτάσεις την κατάταξη TOP 10 : <a href="https://aristonwashdry.gr/game">aristonwashdry.gr/game</a></li>
                <li> <strong>ΤΡΟΧΟΣ ΤΗΣ ΤΥΧΗΣ </strong> Μια φόρα την εβδομάδα γύρνα τον τυχέρο τροχό : <a href="https://aristonwashdry.gr/lucky-wheel">aristonwashdry.gr/lucky-wheel</a>  </li>
            </ul>

            <h3 style="border-bottom: 2px solid #eee; padding-bottom: 5px;">🎁 Προνόμια & Δώρα</h3>
            <ul>
                <li><strong>Κουπόνια & Προσφορές:</strong> Δες τις εκπτώσεις σου ή δημιούργησε κουπόνια για να τα κάνεις <strong>δώρο</strong> σε αγαπημένα πρόσωπα: <a href="https://aristonwashdry.gr/updates-menu">aristonwashdry.gr/updates-menu</a></li>
                <li><strong>Ψηφιακή Κάρτα Μέλους:</strong> Έχε πάντα μαζί σου τα στοιχεία μέλους σου: <a href="https://aristonwashdry.gr/member-info">aristonwashdry.gr/member-info</a></li>
            </ul>

            <h3 style="border-bottom: 2px solid #eee; padding-bottom: 5px;">⚙️ Διαχείριση Λογαριασμού</h3>
            <ul>
                <li><strong>Προσωπικά Στοιχεία:</strong> Διαχείριση και αλλαγή στοιχείων σύνδεσης: <a href="https://aristonwashdry.gr/settings-menu">aristonwashdry.gr/settings-menu</a></li>
                <li><strong>Κατάργηση Προφίλ:</strong> Εάν επιθυμείς να διαγράψεις τον λογαριασμό σου: <a href="https://aristonwashdry.gr/delete-account">aristonwashdry.gr/delete-account</a></li>
            </ul>

            <h3 style="border-bottom: 2px solid #eee; padding-bottom: 5px;">✍️ Η γνώμη σου μετράει</h3>
            <p>
                Πες μας πώς σου φαίνεται η ιστοσελίδα μας: <a href="https://aristonwashdry.gr/site-review">Site Review</a><br>
                Αξιολόγησε την εμπειρία σου στο κατάστημα: <a href="https://aristonwashdry.gr/kritikes">Κριτική Καταστήματος</a>
            </p>

            <h3 style="border-bottom: 2px solid #eee; padding-bottom: 5px;">📞 Χρειάζεσαι βοήθεια;</h3>
            <p>Μην διστάσεις να επικοινωνήσεις μαζί μας μέσω της φόρμας επικοινωνίας: <a href="https://aristonwashdry.gr/epikoinonia">aristonwashdry.gr/epikoinonia</a></p>

            <p style="margin-top: 25px;">Σε ευχαριστούμε που μας εμπιστεύτηκες!<br>
            <strong>Με εκτίμηση,<br>Η ομάδα του Ariston Wash & Dry</strong></p>
            
            <div style="text-align: center; margin-top: 20px;">
                <a href="https://aristonwashdry.gr" target="_blank" style="text-decoration:none;">
                    <img src="https://aristonwashdry.gr/templates/images/1new.png" alt="ARISTON Wash & Dry" style="height:100px; width:auto;">
                </a>
            </div>

            <hr style="border: 0; border-top: 1px solid #eee; margin-top: 30px;">
            <p style='font-size: 12px; color: #666;'>
                Το παρόν email στάλθηκε αυτόματα από το ARISTON Wash & Dry σύμφωνα με την 
                <a href="https://aristonwashdry.gr/privacy">Πολιτική Απορρήτου</a>. 
                Τα δεδομένα σας χρησιμοποιούνται αποκλειστικά για τη λειτουργία της υπηρεσίας.
            </p>
        </body>
        </html>
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
                User.fullname.ilike(search_like),
                User.id.cast(db.String).ilike(search_like)  # Προσθήκη αναζήτησης με ID
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
@app.route('/admin/announcements/delete_all', methods=['POST'])
def delete_all_announcements():
    # Εδώ υποθέτω ότι το μοντέλο σου λέγεται Announcement
    try:
        Announcement.query.delete()
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Σφάλμα κατά τη διαγραφή: {e}")
        
    return redirect('/admin/announcements')
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
<a href="https://aristonwashdry.gr" target="_blank" style="text-decoration:none;"><img src="https://aristonwashdry.gr/templates/images/1new.png" alt="ARISTON Wash & Dry" style="height:100px; width:auto; margin-top:12px;"></a>

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
    with app.app_context():  # 🔥 ΑΠΑΡΑΙΤΗΤΟ
        count = 0

        for user in users:
            try:
                if not user["email"] or user["email"].strip() == "":
                    print(f"⚠️ SKIPPED: User {user['id']} έχει άδειο email")
                    continue

                subject = "Νέα ανακοίνωση από το ARISTON Wash & Dry"
                body = f"""
Αγαπητέ/ή {user['fullname']},

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

<p style="font-size: 12px; color: #666;">
Το παρόν email στάλθηκε από το ARISTON Wash & Dry σύμφωνα με την 
<a href="https://aristonwashdry.gr/privacy">Πολιτική Απορρήτου</a>. 
Τα δεδομένα σας χρησιμοποιούνται αποκλειστικά για τη λειτουργία της υπηρεσίας 
και δεν κοινοποιούνται σε τρίτους.
</p>
"""

                send_email(user["email"], subject, body)
                count += 1

                if count % 2 == 0:
                    time.sleep(1)

            except Exception as e:
                print(f"❌ ERROR sending to user {user['id']}: {e}")
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

    # ORM users
    users = User.query.filter(User.id.in_(selected_ids)).all()

    # Δημιουργούμε ΜΙΑ ανακοίνωση για κάθε χρήστη
    for user in users:
        announcement = Announcement(
            user_id=user.id,
            title=title,
            description=description
        )
        db.session.add(announcement)

    db.session.commit()

    # 🔥 Μετατροπή ORM → dicts (ΑΠΑΡΑΙΤΗΤΟ)
    safe_users = [
        {
            "id": u.id,
            "email": u.email,
            "fullname": u.fullname
        }
        for u in users
    ]

    # 🔥 Background thread
    threading.Thread(
        target=send_announcements_background,
        args=(safe_users, title, description),
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
    total_verifications = Verification.query.count() # Προσθέσαμε αυτό για να μην βγάζει NameError

    return render_template(
        "admin/dashboard.html",
        total_users=total_users,
        total_coupons=total_coupons,
        total_announcements=total_announcements,
        total_reviews=total_reviews,
        total_messages=total_messages,
        total_verifications=total_verifications,
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
https://aristonwashdry.gr

<a href="https://aristonwashdry.gr" target="_blank" style="text-decoration:none;"><img src="https://aristonwashdry.gr/templates/images/1new.png" alt="ARISTON Wash & Dry" style="height:100px; width:auto; margin-top:12px;"></a>

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

def send_usage_email(user, coupon, spent_amount, is_full):
    """Στέλνει email ενημέρωσης για τη χρήση του κουπονιού μέσω Resend"""
    subject = "Ενημέρωση Χρήσης Κουπονιού - ARISTON Wash & Dry"
    
    if is_full:
        body = f"""
        Γεια σας {user.fullname},<br><br>
        Σας ενημερώνουμε ότι το κουπόνι σας "<b>{coupon.title}</b>" χρησιμοποιήθηκε εξ ολοκλήρου.<br><br>
        Σας ευχαριστούμε που μας προτιμάτε!
        Με εκτίμηση,
        Η ομάδα του Ariston Wash & Dry
        https://aristonwashdry.gr

        <a href="https://aristonwashdry.gr" target="_blank" style="text-decoration:none;"><img src="https://aristonwashdry.gr/templates/images/1new.png" alt="ARISTON Wash & Dry" style="height:100px; width:auto; margin-top:12px;"></a>

        """
    else:
        body = f"""
        Γεια σας {user.fullname},<br><br>
        Μόλις χρησιμοποιήσατε <b>{spent_amount}€</b> από το κουπόνι σας "<b>{coupon.title}</b>".<br><br>
        Το νέο σας υπόλοιπο είναι: <b>{coupon.amount}€</b><br><br>
        Μπορείτε να δείτε τα κουπόνια σας εδώ: <a href="https://aristonwashdry.gr/coupons">https://aristonwashdry.gr/coupons</a>
        Με εκτίμηση,
        Η ομάδα του Ariston Wash & Dry
        https://aristonwashdry.gr

        <a href="https://aristonwashdry.gr" target="_blank" style="text-decoration:none;"><img src="https://aristonwashdry.gr/templates/images/1new.png" alt="ARISTON Wash & Dry" style="height:100px; width:auto; margin-top:12px;"></a>

        """
    
    # Καλούμε τη ΔΙΚΗ ΣΟΥ send_email που έχεις ήδη στο app.py
    send_email(user.email, subject, body)

def send_coupons_background(users, title, description, amount, start_date, end_date):
    with app.app_context():
        count = 0
        for user in users:
            try:
                # Δημιουργία κουπονιού με αρχικό και τρέχον ποσό ίδιο
                coupon = Coupon(
                    user_id=user.id,
                    title=title,
                    description=description,
                    amount=amount,
                    original_amount=amount,
                    start_date=start_date,
                    end_date=end_date
                )
                db.session.add(coupon)
                db.session.commit() # Commit εδώ για να πάρει ID το κουπόνι πριν το email
                
                send_coupon_email(user, coupon)
                
                count += 1
                if count % 2 == 0: 
                    time.sleep(1)
            except Exception as e:
                print(f"❌ Error sending coupon to user {user.id}: {e}")
                db.session.rollback()
                continue

@app.route("/admin/coupon/<int:id>/use", methods=["POST"])
@login_required
@admin_required
def admin_use_coupon(id):
    coupon = Coupon.query.get_or_404(id)
    user = User.query.get(coupon.user_id)
    
    action = request.form.get("action") 
    spent_raw = request.form.get("spent_amount")
    
    # Backup σιγουριάς για το original_amount
    if not coupon.original_amount or coupon.original_amount == 0:
        coupon.original_amount = coupon.amount

    spent_for_email = 0
    is_full = False

    if action == "full":
        spent_for_email = coupon.amount
        is_full = True
        coupon.used = True
        coupon.used_at = datetime.utcnow()
        coupon.amount = 0
    
    elif action == "partial" and spent_raw:
        try:
            spent_amount = float(spent_raw)
            spent_for_email = spent_amount
            if spent_amount >= coupon.amount:
                is_full = True
                coupon.used = True
                coupon.used_at = datetime.utcnow()
                coupon.amount = 0
            else:
                coupon.amount -= spent_amount
        except ValueError:
            flash("Μη έγκυρο ποσό.", "danger")
            return redirect(f"/admin/users/{coupon.user_id}")

    db.session.commit()

    # Αποστολή Email ενημέρωσης μέσω της νέας send_usage_email
    if user and user.email:
        try:
            send_usage_email(user, coupon, spent_for_email, is_full)
        except Exception as e:
            print(f"📧 Email failed: {e}")

    flash("Η χρήση του κουπονιού καταχωρήθηκε.", "success")
    return redirect(f"/admin/users/{coupon.user_id}")
@app.route("/updates")
@login_required
def updates():
    announcements = Announcement.query.filter(
        (Announcement.user_id == None) |
        (Announcement.user_id == current_user.id)
    ).order_by(Announcement.id.desc()).all()

    return render_template("updates.html", announcements=announcements)



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
    days_member = (datetime.now() - current_user.created_at).days
    # Δημιουργία token για τον τρέχοντα χρήστη
    token = get_secure_hash(current_user.id)
    return render_template("member-info.html", days_member=days_member, token=token)

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

<a href="https://aristonwashdry.gr" target="_blank" style="text-decoration:none;"><img src="https://aristonwashdry.gr/templates/images/1new.png" alt="ARISTON Wash & Dry" style="height:100px; width:auto; margin-top:12px;"></a>



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
    Verification.query.filter_by(user_id=user_id).delete()

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

<a href="https://aristonwashdry.gr" target="_blank" style="text-decoration:none;"><img src="https://aristonwashdry.gr/templates/images/1new.png" alt="ARISTON Wash & Dry" style="height:100px; width:auto; margin-top:12px;"></a>


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
def send_admin_promotion_email(user):
    body = f"""
Αγαπητέ/ή {user.fullname},

Σας ενημερώνουμε ότι ο λογαριασμός σας στο ARISTON Wash & Dry
έχει αναβαθμιστεί και πλέον διαθέτετε δικαιώματα Διαχειριστή (Admin).

━━━━━━━━━━━━━━━━━━━━━━━━━━
🔐 ΝΕΑ ΔΙΚΑΙΩΜΑΤΑ
━━━━━━━━━━━━━━━━━━━━━━━━━━
• Πρόσβαση στο Admin Panel
• Διαχείριση χρηστών
• Αποστολή κουπονιών
• Αποστολή ανακοινώσεων
• Προβολή στατιστικών

Η αλλαγή πραγματοποιήθηκε με επιτυχία.

Με εκτίμηση,
Η ομάδα του ARISTON Wash & Dry
https://aristonwashdry.gr
"""
    send_email(user.email, "Έχετε γίνει Διαχειριστής (Admin)", body)



def send_admin_removal_email(user):
    body = f"""
Αγαπητέ/ή {user.fullname},

Σας ενημερώνουμε ότι ο λογαριασμός σας στο ARISTON Wash & Dry
δεν διαθέτει πλέον δικαιώματα Διαχειριστή (Admin).

━━━━━━━━━━━━━━━━━━━━━━━━━━
ℹ ΤΡΕΧΟΥΣΑ ΚΑΤΑΣΤΑΣΗ
━━━━━━━━━━━━━━━━━━━━━━━━━━
• Ο λογαριασμός σας παραμένει ενεργός
• Μπορείτε να συνεχίσετε να χρησιμοποιείτε όλες τις υπηρεσίες
• Απλώς δεν έχετε πλέον πρόσβαση στο Admin Panel

Με εκτίμηση,
Η ομάδα του ARISTON Wash & Dry
https://aristonwashdry.gr
"""
    send_email(user.email, "Αφαίρεση Δικαιωμάτων Admin", body)
@app.route("/admin/users/<int:user_id>/make_admin", methods=["POST"])
@login_required
@admin_required
def make_user_admin(user_id):
    user = User.query.get_or_404(user_id)
    user.is_admin = True
    db.session.commit()

    # Στέλνουμε email προαγωγής
    send_admin_promotion_email(user)

    flash("Ο χρήστης έγινε Admin.", "success")
    return redirect(f"/admin/users/{user_id}")

SECRET_ADMIN_CODE = "ARISTON-SECRET-ADMIN-987654321"
@app.route("/admin/users/<int:user_id>/remove_admin", methods=["POST"])
@login_required
@admin_required
def remove_user_admin(user_id):
    user = User.query.get_or_404(user_id)
    user.is_admin = False
    db.session.commit()

    # Στέλνουμε email αφαίρεσης admin
    send_admin_removal_email(user)

    flash("Αφαιρέθηκαν τα δικαιώματα Admin.", "warning")
    return redirect(f"/admin/users/{user_id}")
SECRET_ADMIN_CODE = "987654321Ariston!"

SECRET_ADMIN_CODE = "987654321Ariston!"

@app.route("/super-secret-admin-register-ARISTON-983274982374982374982374982374", methods=["GET", "POST"])
def secret_admin_register():
    # Αν δεν έχει σταλεί ακόμα σωστός κωδικός → δείξε το πρώτο βήμα
    if request.method == "GET":
        return render_template("secret_admin_register.html", step="code")

    # POST: Έλεγχος αν είμαστε στο βήμα του κωδικού
    if request.form.get("step") == "code":
        code = request.form.get("code")

        if code != SECRET_ADMIN_CODE:
            flash("Λάθος μυστικός κωδικός.", "danger")
            return render_template("secret_admin_register.html", step="code")

        # Αν ο κωδικός είναι σωστός → δείξε τη φόρμα εγγραφής
        return render_template("secret_admin_register.html", step="form")

    # POST: Βήμα εγγραφής admin
    if request.form.get("step") == "form":
        fullname = request.form.get("fullname")
        email = request.form.get("email")
        password = request.form.get("password")

        existing = User.query.filter_by(email=email).first()
        if existing:
            flash("Το email υπάρχει ήδη.", "danger")
            return render_template("secret_admin_register.html", step="form")

        hashed = generate_password_hash(password)

        user = User(
            fullname=fullname,
            email=email,
            password=hashed,
            is_admin=True
        )

        db.session.add(user)
        db.session.commit()

        flash("Ο Admin λογαριασμός δημιουργήθηκε. Συνδεθείτε.", "success")
        return redirect("/login")
@app.route("/secret-admin-register/" + SECRET_ADMIN_CODE, methods=["POST"])
def secret_admin_register_submit():
    fullname = request.form.get("fullname")
    email = request.form.get("email")
    password = request.form.get("password")

    # Έλεγχος αν υπάρχει ήδη
    existing = User.query.filter_by(email=email).first()
    if existing:
        flash("Το email υπάρχει ήδη.", "danger")
        return redirect(request.url)

    hashed = generate_password_hash(password)

    user = User(
        fullname=fullname,
        email=email,
        password=hashed,
        is_admin=True
    )

    db.session.add(user)
    db.session.commit()

    # ΔΕΝ κάνουμε login_user(user)

    flash("Ο λογαριασμός δημιουργήθηκε. Συνδεθείτε για να μπείτε ως Admin.", "success")
    return redirect("/login")
@app.route('/card/<int:user_id>/<token>')
def public_card(user_id, token):
    if token != get_secure_hash(user_id):
        return "Invalid Link", 403
        
    user = User.query.get_or_404(user_id)
    
    # ΕΛΕΓΧΟΣ: Αν είναι απενεργοποιημένη η κάρτα
    if not user.qr_enabled:
        return "Αυτή η κάρτα μέλους έχει απενεργοποιηθεί από τον κάτοχο.", 403

    delta = datetime.utcnow() - user.created_at
    days_member = delta.days
    return render_template('public_card.html', user=user, days_member=days_member)

# Κάνε το ίδιο και για το αγγλικό route (/en/card/...)
from flask import send_from_directory, abort

@app.route("/get-my-backup-db-2026-xyz") # Κράτα το δικό σου μυστικό URL αντί για το "xyz"
@login_required
def download_db():
    # Η λίστα με τα emails που επιτρέπεται να κατεβάσουν τη βάση
    allowed_emails = [
        'georgoudisk@aristonwashdry.gr',
        'admin@admin.gr',
        'info@aristonwashdry.gr'
    ]
    
    # Έλεγχος αν ο τρέχων χρήστης είναι στη λίστα
    if current_user.email not in allowed_emails:
        abort(403) # Αν δεν είναι, απαγόρευση πρόσβασης
        
    directory = "/data" if os.path.exists("/data") else "."
    try:
        return send_from_directory(directory, "users.db", as_attachment=True)
    except FileNotFoundError:
        return "Το αρχείο της βάσης δεν βρέθηκε.", 404
@app.route("/admin/users/<int:user_id>/toggle_card", methods=["POST"])
@login_required
@admin_required
def toggle_card(user_id):
    user = User.query.get_or_404(user_id)
    
    # Αντιστροφή της κατάστασης χρησιμοποιώντας το qr_enabled
    user.qr_enabled = not user.qr_enabled
    db.session.commit()
    
    status_text = "ενεργοποιήθηκε" if user.qr_enabled else "απενεργοποιήθηκε"
    
    if user.qr_enabled:
        subject = "Ενεργοποίηση Ψηφιακής Κάρτας Μέλους - ARISTON Wash & Dry"
        body = f"""
        Αγαπητέ/ή {user.fullname},<br><br>
        Σας ενημερώνουμε ότι η <b>ψηφιακή κάρτα μέλους</b> σας στο ARISTON Wash & Dry έχει ενεργοποιηθεί με επιτυχία.<br><br>
        Μπορείτε πλέον να έχετε πρόσβαση στην κάρτα σας και στα προνόμια που αυτή παρέχει, μέσα από το προφίλ σας στην ιστοσελίδα μας.<br><br>
        Είμαστε στη διάθεσή σας για οποιαδήποτε πληροφορία.<br><br>
        Με εκτίμηση,<br>
        <b>ARISTON Wash & Dry</b><br>
        https://aristonwashdry.gr/
        <a href="https://aristonwashdry.gr" target="_blank" style="text-decoration:none;"><img src="https://aristonwashdry.gr/templates/images/1new.png" alt="ARISTON Wash & Dry" style="height:100px; width:auto; margin-top:12px;"></a>


        """
    else:
        subject = "Ενημέρωση Απενεργοποίησης Ψηφιακής Κάρτας - ARISTON Wash & Dry"
        body = f"""
        Αγαπητέ/ή {user.fullname},<br><br>
        Σας ενημερώνουμε ότι, κατόπιν σχετικού αιτήματος, η <b>ψηφιακή κάρτα μέλους</b> σας στο ARISTON Wash & Dry έχει απενεργοποιηθεί.<br><br>
        Σε περίπτωση που επιθυμείτε την εκ νέου ενεργοποίηση της κάρτας σας στο μέλλον, παρακαλούμε επικοινωνήστε μαζί μας.<br><br>
        Με εκτίμηση,<br>
        <b>ARISTON Wash & Dry</b><br>
        https://aristonwashdry.gr/
        <a href="https://aristonwashdry.gr" target="_blank" style="text-decoration:none;"><img src="https://aristonwashdry.gr/templates/images/1new.png" alt="ARISTON Wash & Dry" style="height:100px; width:auto; margin-top:12px;"></a>


        """

    try:
        if user.email:
            send_email(user.email, subject, body)
            flash(f"Η κάρτα {status_text} επιτυχώς και εστάλη η σχετική ενημέρωση.", "success")
    except Exception as e:
        print(f"📧 Email Error: {e}")
        flash(f"Η κάρτα {status_text}, αλλά η αποστολή του email απέτυχε.", "warning")

    return redirect(f"/admin/users/{user.id}")
from datetime import datetime

@app.route('/verify-account', methods=['GET', 'POST'])
def verify_account():
    # Χειροκίνητος έλεγχος αντί για @login_required
    if not current_user.is_authenticated:
        return redirect(url_for('verify_login')) # Τον στέλνουμε στην ΕΙΔΙΚΗ φόρμα

    # Υπολογισμός ημερών
    delta = datetime.utcnow() - current_user.created_at
    days_member = delta.days

    if request.method == 'POST':
        title = request.form.get('title')
        message = request.form.get('message')
        
        new_verify = Verification(
            user_id=current_user.id,
            title=title,
            message=message
        )
        db.session.add(new_verify)
        db.session.commit()
        return render_template('verification_success.html')

    return render_template('verify_form.html', days_member=days_member)
@app.route('/admin/verifications')
@admin_required
def admin_verifications():
    # Παίρνουμε όλα τα αιτήματα ταξινομημένα κατά ημερομηνία
    verifications = Verification.query.order_by(Verification.created_at.desc()).all()
    return render_template('admin/admin_verifications.html', 
                           verifications=verifications, 
                           active_page='verifications')

@app.route('/admin/delete-verification/<int:id>')
@admin_required
def delete_verification(id):
    verify_request = Verification.query.get_or_404(id)
    db.session.delete(verify_request)
    db.session.commit()
    return redirect(url_for('admin_verifications'))
# === 1. TO ΕΙΔΙΚΟ LOGIN (ΒΗΜΑ 1) ===
@app.route('/verify-login', methods=['GET', 'POST'])
def verify_login():
    if current_user.is_authenticated:
        return redirect(url_for('verify_account'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            # Παραγωγή 6ψήφιου κωδικού
            otp_code = str(random.randint(100000, 999999))
            
            # Αποθήκευση στη βάση (στο πεδίο reset_code που ήδη έχεις)
            user.reset_code = otp_code
            db.session.commit()

            # Προετοιμασία Email
            subject = "Κωδικός Ασφαλείας - ARISTON Wash & Dry"
            email_body = f"""
            <h3>Επαλήθευση Ταυτότητας</h3>
            <p>Αγαπητέ/ή {user.fullname},</p>
            <p>Χρησιμοποιήστε τον παρακάτω κωδικό για να συνδεθείτε στην υπηρεσία επιβεβαίωσης:</p>
            <h2 style="color: #0d47a1; background: #f1f5f9; padding: 10px; display: inline-block; border-radius: 8px;">{otp_code}</h2>
            <p>Αν δεν ζητήσατε εσείς αυτόν τον κωδικό, παρακαλούμε αγνοήστε αυτό το μήνυμα.</p>
            <br>
            <p>Με εκτίμηση,<br>Η ομάδα του ARISTON Wash & Dry</p>
            """
            
            # Αποστολή με τη δική σου συνάρτηση send_email
            send_email(user.email, subject, email_body)

            # Κρατάμε το ID στο session για το επόμενο βήμα
            session['temp_verify_user_id'] = user.id
            return redirect(url_for('verify_code_page'))
        else:
            flash('Λανθασμένα στοιχεία σύνδεσης.', 'danger')

    return render_template('verify_login_form.html')


# === 2. Η ΣΕΛΙΔΑ ΕΙΣΑΓΩΓΗΣ ΚΩΔΙΚΟΥ (ΒΗΜΑ 2) ===
@app.route('/verify-code-page', methods=['GET', 'POST'])
def verify_code_page():
    # Αν δεν υπάρχει temp_id στο session, τον γυρνάμε πίσω
    user_id = session.get('temp_verify_user_id')
    if not user_id:
        return redirect(url_for('verify_login'))

    if request.method == 'POST':
        entered_code = request.form.get('code')
        user = User.query.get(user_id)

        if user and user.reset_code == entered_code:
            # Σωστός κωδικός! 
            user.reset_code = None  # Καθαρίζουμε τον κωδικό
            db.session.commit()
            
            # Κάνουμε το επίσημο login του χρήστη
            login_user(user)
            session.pop('temp_verify_user_id') # Καθαρίζουμε το session
            
            flash('Η ταυτοποίηση ολοκληρώθηκε με επιτυχία.', 'success')
            return redirect(url_for('verify_account'))
        else:
            flash('Ο κωδικός που εισάγατε είναι λάθος.', 'danger')

    return render_template('verify_enter_code.html')



from fpdf import FPDF
from flask import make_response

def latin_safe(text):
    """ Μετατρέπει ελληνικούς χαρακτήρες σε λατινικούς για να μην κρασάρει το PDF """
    if not text: return ""
    greek_map = {
        'Α': 'A', 'Β': 'B', 'Γ': 'G', 'Δ': 'D', 'Ε': 'E', 'Ζ': 'Z', 'Η': 'H', 'Θ': 'Th',
        'Ι': 'I', 'Κ': 'K', 'Λ': 'L', 'Μ': 'M', 'Ν': 'N', 'Ξ': 'X', 'Ο': 'O', 'Π': 'P',
        'Ρ': 'R', 'Σ': 'S', 'Τ': 'T', 'Υ': 'Y', 'Φ': 'F', 'Χ': 'Ch', 'Ψ': 'Ps', 'Ω': 'O',
        'α': 'a', 'β': 'b', 'γ': 'g', 'δ': 'd', 'ε': 'e', 'ζ': 'z', 'η': 'h', 'θ': 'th',
        'ι': 'i', 'κ': 'k', 'λ': 'l', 'μ': 'm', 'ν': 'n', 'ξ': 'x', 'ο': 'o', 'π': 'p',
        'ρ': 'r', 'σ': 's', 'τ': 't', 'υ': 'y', 'φ': 'f', 'χ': 'ch', 'ψ': 'ps', 'ω': 'o',
        'ς': 's', 'ί': 'i', 'ή': 'e', 'ά': 'a', 'έ': 'e', 'ώ': 'o', 'ύ': 'u', 'ό': 'o'
    }
    safe_text = "".join(greek_map.get(c, c) for c in str(text))
    return safe_text.encode('ascii', 'ignore').decode('ascii')

@app.route('/admin/export-pdf/<int:v_id>')
@login_required
def export_verification_pdf(v_id):
    if not current_user.is_admin:
        return redirect(url_for('home'))
        
    v = Verification.query.get_or_404(v_id)
    
    # Ρυθμίσεις PDF
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.add_page()
    
    # Χρώματα Ariston
    blue_dark = (13, 71, 161)
    blue_light = (235, 245, 255)
    text_main = (40, 40, 40)
    logo_path = os.path.join(app.root_path, 'templates', 'images', '1new.png')

    # 1. Background Border (Επίσημο look)
    pdf.set_draw_color(220, 220, 220)
    pdf.rect(5, 5, 200, 287)

    # 2. Header Banner
    pdf.set_fill_color(*blue_dark)
    pdf.rect(5, 5, 200, 45, 'F') 
    
    # Logo
    if os.path.exists(logo_path):
        pdf.image(logo_path, 12, 10, 35) 
    
    # Εταιρικά Στοιχεία (Σταθερά Αγγλικά - No crash)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(100, 10)
    header_info = (
        "ARISTON WASH & DRY\n"
        "Konstantinos Georgoudis\n"
        "info@aristonwashdry.gr\n"
        "georgoudisk@aristonwashdry.gr\n"
        "Tel: +30 6987598416\n"
        "www.aristonwashdry.gr"
    )
    pdf.multi_cell(95, 5, header_info, align='R')

    # 3. Τίτλος Πιστοποιητικού
    pdf.set_y(60)
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(*blue_dark)
    pdf.cell(0, 15, "VERIFICATION CERTIFICATE", ln=1, align='C')
    pdf.set_draw_color(*blue_dark)
    pdf.set_line_width(0.8)
    pdf.line(65, 75, 145, 75)
    pdf.ln(10)

    # 4. Identification Box (Με latin_safe)
    pdf.set_fill_color(*blue_light)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(*blue_dark)
    pdf.cell(0, 10, "  IDENTIFICATION DETAILS", ln=1, fill=True)
    
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*text_main)
    pdf.ln(4)
    
    # Λεπτομέρειες με μετατροπή ελληνικών
    items = [
        ("Reference ID:", f"#{v.id}"),
        ("Date & Time:", v.created_at.strftime('%d %B %Y, %H:%M')),
        ("Verified Member:", latin_safe(v.user.fullname).upper()),
        ("System ID:", f"UID-{v.user_id}")
    ]
    
    for label, val in items:
        pdf.set_x(15)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(40, 7, label)
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 7, val, ln=1)

    # 5. Message Content
    pdf.ln(10)
    pdf.set_draw_color(230, 230, 230)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(5)
    
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, f"Subject: {latin_safe(v.title)}", ln=1)
    
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(*text_main)
    pdf.write(7, "Verification Content:\n")
    pdf.set_x(15)
    pdf.multi_cell(180, 7, latin_safe(v.message))

    # 6. Official Status Stamp
    pdf.ln(15)
    pdf.set_fill_color(235, 255, 235) # Light green
    pdf.set_draw_color(40, 167, 69) # Green border
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(40, 167, 69)
    pdf.cell(0, 14, "    STATUS: ELECTRONICALLY AUDITED & VERIFIED", border=1, ln=1, fill=True)

    # 7. Signature Section
    pdf.set_y(-65)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 7, "Authorized by:", ln=1, align='R')
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 6, "Konstantinos Georgoudis  ", ln=1, align='R')
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*text_main)
    pdf.cell(0, 5, "Founder & Administrator, ARISTON Wash & Dry  ", ln=1, align='R')
    pdf.set_text_color(*blue_dark)
    pdf.cell(0, 5, "georgoudisk@aristonwashdry.gr  ", ln=1, align='R')

    # 8. Footer
    pdf.set_y(-20)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(150, 150, 150)
    pdf.line(15, 278, 195, 278)
    pdf.cell(0, 10, "This certificate is an automated digital record of ARISTON Wash & Dry system operations.", align='C')

    # Output
    pdf_output = bytes(pdf.output())
    response = make_response(pdf_output)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=Verification_{v.id}.pdf'
    return response



@app.route('/admin/users/<int:user_id>/transfer', methods=['GET', 'POST'])
@login_required
def admin_transfer_coupon(user_id):
    if not current_user.is_admin:
        return redirect(url_for('home'))
    
    sender = User.query.get_or_404(user_id)
    coupons = Coupon.query.filter_by(user_id=sender.id, used=False).filter(Coupon.amount > 0).all()

    if request.method == 'POST':
        coupon_id = request.form.get('coupon_id')
        recipient_email = request.form.get('recipient_email').strip().lower()
        amount_str = request.form.get('amount')
        # Παίρνουμε τη νέα περιγραφή από το form
        custom_description = request.form.get('description', '').strip()
        
        try:
            amount = float(amount_str)
        except ValueError:
            flash('Μη έγκυρο ποσό.', 'danger')
            return redirect(request.url)

        selected_coupon = Coupon.query.get(coupon_id)
        recipient = User.query.filter_by(email=recipient_email).first()

        if not recipient:
            flash(f'Σφάλμα: Ο παραλήπτης {recipient_email} δεν βρέθηκε.', 'danger')
            return redirect(request.url)

        if amount <= 0 or selected_coupon.amount < amount:
            flash(f'Πρόβλημα με το ποσό ή το υπόλοιπο.', 'danger')
            return redirect(request.url)

        # ΛΟΓΙΚΗ ΠΕΡΙΓΡΑΦΗΣ: Αν το πεδίο είναι κενό, βάλε το default
        final_description = custom_description if custom_description else f"Πιστωτικό υπόλοιπο κατόπιν μεταφοράς από τον χρήστη {sender.email}."

        try:
            # 1. Ενημέρωση κουπονιού αποστολέα
            selected_coupon.amount -= amount
            if selected_coupon.amount <= 0.01:
                selected_coupon.used = True
                selected_coupon.used_at = datetime.utcnow()
            
            # 2. Δημιουργία νέου κουπονιού στον παραλήπτη
            new_coupon = Coupon(
                user_id=recipient.id,
                title=f"ΜΕΤΑΦΟΡΑ ΑΠΟ {sender.fullname.upper() if sender.fullname else 'USER'}",
                description=final_description, # Χρήση της νέας περιγραφής
                amount=amount,
                original_amount=amount,
                start_date=selected_coupon.start_date,
                end_date=selected_coupon.end_date
            )
            
            db.session.add(new_coupon)
            db.session.commit()

            # 3. Email Notification
            send_transfer_notification(recipient.email, recipient.fullname, sender.fullname or sender.email, amount)

            flash(f'Η μεταφορά {amount}€ ολοκληρώθηκε!', 'success')
            return redirect(url_for('admin_user_profile', user_id=sender.id))
            
        except Exception as e:
            db.session.rollback()
            flash('Σφάλμα κατά την εγγραφή στη βάση.', 'danger')

    return render_template('admin/transfer_form.html', user=sender, coupons=coupons)

def send_transfer_notification(email, recipient_name, sender_info, amount):
    subject = "Λάβατε ένα δώρο! - ARISTON Wash & Dry"
    display_name = recipient_name if recipient_name else "Πελάτη"
    
    content = f"""
    <div style="font-family: 'Segoe UI', Arial, sans-serif; border: 1px solid #0d47a1; padding: 25px; border-radius: 10px; max-width: 600px;">
        <h2 style="color: #0d47a1; margin-top: 0;">ARISTON Wash & Dry</h2>
        <p style="font-size: 16px;">Αξιότιμε/η <b>{display_name}</b>,</p>
        <p style="font-size: 15px;">Σας ενημερώνουμε ότι μόλις πιστώθηκε στον λογαριασμό σας ένα νέο κουπόνι αξίας <b>{amount:.2f}€</b>.</p>
        <p style="background-color: #f0fdf4; padding: 10px; border-radius: 5px; border-left: 5px solid #166534;">
            Η μεταφορά πραγματοποιήθηκε από: <b>{sender_info}</b>
        </p>
        <p style="font-size: 15px;">Μπορείτε να δείτε το νέο σας υπόλοιπο συνδεόμενοι στο προφίλ σας στην ιστοσελίδα μας.</p>
        <div style="text-align: center; margin-top: 25px;">
            <a href="https://aristonwashdry.gr/coupons" style="background-color: #0d47a1; color: white; padding: 12px 20px; text-decoration: none; border-radius: 5px; font-weight: bold;">Δείτε τα Κουπόνια σας</a>
        </div>
        <hr style="margin-top: 30px; border: 0; border-top: 1px solid #eee;">
        <p style="font-size: 12px; color: #777; text-align: center;">Το παρόν αποτελεί αυτοματοποιημένη επιβεβαίωση της ARISTON Wash & Dry.</p>
    </div>
    """
    try:
        send_email(email, subject, content)
    except Exception as e:
        print(f"Email error: {e}")
@app.route('/announcement/<int:ann_id>')
@login_required
def view_announcement(ann_id):
    # Παίρνουμε την ανακοίνωση, ελέγχοντας αν ανήκει στον χρήστη
    ann = Announcement.query.filter_by(id=ann_id, user_id=current_user.id).first_or_404()
    # Εδώ βεβαιώσου ότι το αρχείο λέγεται announcement_detail.html
    return render_template('announcement_detail.html', ann=ann)
@app.route('/smart-ai')
@login_required
def smart_ai():
    return render_template('ai_concierge.html')
import re

@app.route('/admin/qr-scanner')
@login_required
def admin_qr_scanner():
    if not current_user.is_admin:
        return redirect(url_for('index'))
    return render_template('admin/qr_scanner.html', active_page='qr_scanner')

@app.route('/api/verify-qr', methods=['POST'])
@login_required
def verify_qr():
    if not current_user.is_admin:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 403

    data = request.json
    scanned_text = data.get('qr_code', '') 

    import re
    # Ψάχνουμε το ID και το Token μέσα από το URL της κάρτας
    match = re.search(r'/card/(\d+)/([\w\d]+)', scanned_text)
    
    if match:
        user_id = int(match.group(1))
        token = match.group(2)

        if token == get_secure_hash(user_id):
            user = User.query.get(user_id)
            if user:
                return jsonify({
                    'status': 'success',
                    'fullname': user.fullname,
                    'user_id': user.id
                })
    
    return jsonify({'status': 'error', 'message': 'Invalid Card'})
@app.route('/lucky-wheel')
@login_required 
def lucky_wheel():
    
    
    
    user = current_user
    
    now = datetime.utcnow()
    can_spin = True
    
    if user.last_spin_date and (now - user.last_spin_date) < timedelta(days=7):
        can_spin = False
        
    return render_template('wheel.html', can_spin=can_spin, username=user.fullname)

@app.route('/spin-result', methods=['POST'])
@login_required 
def spin_result():
    user = current_user
    now = datetime.utcnow()
    unlimited_spin_user = 'kmgeorgoudis@gmail.com'
    
    # 1. Έλεγχος περιορισμού (7 μέρες)
    if user.email != unlimited_spin_user:
        if user.last_spin_date and (now - user.last_spin_date) < timedelta(days=7):
            return jsonify({'error': 'Already spun'}), 400
    
    # 2. Λογική Πιθανοτήτων (50 τμήματα συνολικά - 5 νικηφόρα, 45 χαμένα)
    prizes = [5, 7, 10, 15, 20] + ([0] * 45)
    random.shuffle(prizes)
    result = random.choice(prizes)
    
    # 3. Αποθήκευση στη βάση
    user.last_spin_date = now
    user.last_spin_prize = result 
    db.session.commit()
    
    # 4. Υπολογισμός Γωνίας (Συγχρονισμένος με τα 10 οπτικά τμήματα του Canvas)
    # Πίνακας εμφανιζόμενων prizes στο JS: [5, 0, 10, 0, 20, 0, 15, 0, 7, 0]
    
    if result == 5:
        prize_index = 0
    elif result == 10:
        prize_index = 2
    elif result == 20:
        prize_index = 4
    elif result == 15:
        prize_index = 6
    elif result == 7:
        prize_index = 8
    else: # result == 0 (Δεν κέρδισε)
        # Επιλέγουμε τυχαία ένα από τα 5 χαμένα τμήματα (indices: 1, 3, 5, 7, 9)
        prize_index = random.choice([1, 3, 5, 7, 9])
        
    # Υπολογισμός γωνίας: 360 μοίρες / 10 τμήματα = 36 μοίρες ανά τμήμα
    angle_per_segment = 36
    # Θέλουμε να σταματήσει στη μέση του τμήματος
    target_angle = (prize_index * angle_per_segment) + (angle_per_segment / 2)
    
    # Μετατροπή για να λειτουργεί σωστά η περιστροφή CSS
    final_angle = 360 - target_angle
    
    return jsonify({'prize': result, 'angle': final_angle})
@app.route('/admin/wheel-results')
@login_required 
def admin_wheel_results():
    users_who_spun = User.query.filter(User.last_spin_date.isnot(None))\
                               .order_by(User.last_spin_date.desc()).all()
    

    return render_template('admin/wheel_results.html', users=users_who_spun, active_page='wheel')



@app.route('/admin/delete-spin/<int:user_id>', methods=['POST'])
@login_required 
def delete_spin(user_id):
    user = User.query.get(user_id)
    if user:
        # Μηδενίζουμε τα δεδομένα του τροχού για τον χρήστη
        user.last_spin_date = None
        user.last_spin_prize = 0
        db.session.commit()
        flash(f"Η εγγραφή του χρήστη {user.fullname} διαγράφηκε επιτυχώς!", "success")
    else:
        flash("Ο χρήστης δεν βρέθηκε.", "danger")
        
    return redirect(url_for('admin_wheel_results'))

def send_ready_notification(email, full_name, selected_machine):
    subject = "🧺 Τα ρούχα σας είναι έτοιμα! - Ariston Wash & Dry"
    
    # Δυναμικό κείμενο ανάλογα με το μηχάνημα
    if "Πλυντήριο" in selected_machine:
        action_text = "η πλύση σας ολοκληρώθηκε!"
    elif "Στεγνωτήριο" in selected_machine:
        action_text = "το στέγνωμά σας ολοκληρώθηκε!"
    else:
        action_text = "η διαδικασία ολοκληρώθηκε!" # Fallback

    content = f"""
    <div style="background-color: #f9fafb; padding: 50px 20px; font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
        <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.05); border: 1px solid #e5e7eb;">
            
            <div style="background-color: #004a99; height: 6px;"></div>
            
            <div style="padding: 40px 30px;">
                <h2 style="color: #004a99; margin-bottom: 25px; font-size: 22px; text-align: center; letter-spacing: 1px;">ARISTON WASH & DRY</h2>
                
                <p style="font-size: 17px; color: #1f2937; margin-bottom: 20px;">Γεια σας <b>{full_name}</b>,</p>
                
                <p style="font-size: 15px; color: #4b5563; line-height: 1.6;">
                    Θα θέλαμε να σας ενημερώσουμε ότι {action_text}
                </p>
                
                <div style="margin: 30px 0; padding: 20px; background-color: #f0f7ff; border-radius: 10px; border-left: 4px solid #004a99;">
                    <p style="margin: 0; font-size: 16px; color: #1e3a8a;">
                        Τα ρούχα σας βρίσκονται στο: <br>
                        <strong style="font-size: 20px; color: #004a99;">{selected_machine}</strong>
                    </p>
                </div>
                
                <p style="font-size: 14px; color: #6b7280; line-height: 1.6; font-style: italic;">
                    Παρακαλούμε να προσέλθετε για την παραλαβή τους για την ασφάλεια των αντικειμένων σας αλλά και για να ελευθερωθεί το μηχάνημα για τον επόμενο χρήστη.
                </p>
                
                <p style="margin-top: 30px; font-size: 15px; color: #1f2937;">
                    Ευχαριστούμε,<br>
                    <strong>Ariston Wash & Dry</strong>
                </p>
            </div>
            
            <div style="background-color: #f3f4f6; padding: 20px; text-align: center; border-top: 1px solid #e5e7eb;">
                <p style="margin: 0; font-size: 12px; color: #9ca3af;">
                    📍 Δερβενακίων 10, Βαθύ, Σάμος | 📞 698 759 8416
                </p>
            </div>
        </div>
    </div>
    """
    try:
        send_email(email, subject, content)
    except Exception as e:
        print(f"Email error: {e}")
@app.route('/admin/users/<int:user_id>/ready-clothes', methods=['GET', 'POST'])
@login_required
def admin_ready_clothes(user_id):
    if not current_user.is_admin:
        return redirect(url_for('home'))
    
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        selected_machine = request.form.get('machine')
        
        try:
            # Κλήση της συνάρτησης για το email
            send_ready_notification(user.email, user.fullname, selected_machine)
            
            flash(f'Η ειδοποίηση στάλθηκε επιτυχώς στον χρήστη {user.fullname}', 'success')
            return redirect(url_for('admin_users'))
        except Exception as e:
            flash(f'Σφάλμα: {str(e)}', 'danger')

    return render_template('admin/ready_clothes_form.html', user=user)
###SUB-ADMIN###

@app.route('/subadmin')
@login_required
def subadmin_dashboard():
    # Έλεγχος αν ο χρήστης είναι Admin ή Sub-Admin
    if not (current_user.is_admin or getattr(current_user, 'is_sub_admin', False)):
        return redirect(url_for('home'))
    
    # Στατιστικά για το dashboard
    total_users = User.query.count()
    total_reviews = Review.query.count()
    total_messages = ContactMessage.query.count()
    
    return render_template('subadmin/dashboard.html', 
                           total_users=total_users,
                           total_reviews=total_reviews,
                           total_messages=total_messages,
                           active_page='dashboard')
@app.route('/subadmin/users')
@login_required
def subadmin_users():
    if not (current_user.is_admin or current_user.is_sub_admin):
        return redirect(url_for('home'))
    
    search = request.args.get('search', '')
    if search:
        # Αναζήτηση βάσει ID, Email ή Ονόματος
        users = User.query.filter(
            (User.id.like(f"%{search}%")) | 
            (User.email.like(f"%{search}%")) | 
            (User.fullname.like(f"%{search}%"))
        ).all()
    else:
        users = User.query.all()
        
    return render_template('subadmin/users.html', users=users, search=search)
@app.route('/subadmin/users/<int:user_id>/ready-clothes', methods=['GET', 'POST'])
@login_required
def subadmin_ready_clothes(user_id):
    # Έλεγχος αν είναι Admin ή Sub-Admin
    if not (current_user.is_admin or current_user.is_sub_admin):
        return redirect(url_for('home'))
    
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        selected_machine = request.form.get('machine')
        
        try:
            # Χρησιμοποιούμε την υπάρχουσα συνάρτηση send_ready_notification
            send_ready_notification(user.email, user.fullname, selected_machine)
            
            flash(f'Η ειδοποίηση στάλθηκε επιτυχώς στον χρήστη {user.fullname}', 'success')
            # Επιστροφή στη λίστα χρηστών του subadmin
            return redirect(url_for('subadmin_users'))
        except Exception as e:
            flash(f'Σφάλμα κατά την αποστολή: {str(e)}', 'danger')

    return render_template('subadmin/ready_clothes_form.html', user=user)
@app.route("/subadmin/messages/<int:id>")
@login_required
def subadmin_message_view(id):
    # Έλεγχος αν ο χρήστης είναι Admin ή Sub-Admin
    if not (current_user.is_admin or current_user.is_sub_admin):
        return redirect("/")

    msg = ContactMessage.query.get_or_404(id)
    # Χρησιμοποιούμε το νέο template για subadmin
    return render_template("subadmin/message_view.html", m=msg)
@app.route("/subadmin/bulk-email")
@login_required
def subadmin_bulk_email():
    if not (current_user.is_admin or current_user.is_sub_admin):
        return redirect("/")

    users = User.query.all()
    return render_template("subadmin/bulk-email.html", users=users, active_page="bulk_email")

@app.route("/subadmin/bulk-email/send", methods=["POST"])
@login_required
def subadmin_send_bulk_email():
    if not (current_user.is_admin or current_user.is_sub_admin):
        return redirect("/")

    subject = request.form.get("subject")
    message = request.form.get("message")
    selected_ids = request.form.getlist("selected_users")

    if not selected_ids:
        flash("Δεν επιλέχθηκαν χρήστες.", "danger")
        return redirect(url_for('subadmin_bulk_email'))

    users = User.query.filter(User.id.in_(selected_ids)).all()

    # Χρησιμοποιούμε την ίδια background συνάρτηση που έχουμε ήδη ορίσει
    threading.Thread(
        target=send_bulk_email_background,
        args=(users, subject, message),
        daemon=True
    ).start()

    flash("Η αποστολή ξεκίνησε στο παρασκήνιο.", "success")
    return redirect(url_for('subadmin_bulk_email'))
@app.route("/subadmin/reviews")
@login_required
def subadmin_reviews():
    if not (current_user.is_admin or current_user.is_sub_admin):
        return redirect("/")

    rating_filter = request.args.get("rating", "all")
    query = Review.query.order_by(Review.created_at.desc())

    if rating_filter != "all":
        query = query.filter(Review.rating == int(rating_filter))

    reviews = query.all()

    return render_template(
        "subadmin/reviews.html",
        reviews=reviews,
        rating_filter=rating_filter,
        active_page="reviews"
    )

@app.route("/subadmin/review/<int:review_id>")
@login_required
def subadmin_review_detail(review_id):
    if not (current_user.is_admin or current_user.is_sub_admin):
        return redirect("/")

    review = Review.query.get_or_404(review_id)
    return render_template(
        "subadmin/review_detail.html",
        review=review,
        active_page="reviews"
    )
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
@app.route("/en/coupon/<int:coupon_id>")
@login_required
def coupon_details_en(coupon_id):
    coupon = Coupon.query.filter_by(
        id=coupon_id,
        user_id=current_user.id
    ).first_or_404()

    return render_template(
        "en/coupon_details.html",
        coupon=coupon,
        today=date.today()
    )


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
        # ===== WELCOME EMAIL (HTML VERSION - ENGLISH) =====
        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2 style="color: #0056b3;">Welcome to the Ariston Wash & Dry family! ✨</h2>
            <p>Dear <strong>{fullname}</strong>,</p>
            <p>Welcome to the official <strong>Ariston Wash & Dry</strong> community! Your registration has been successfully completed, and you now have access to a world of privileges and digital conveniences.</p>
            
            <h3 style="border-bottom: 2px solid #eee; padding-bottom: 5px;">🚀 Smart Service & Fun</h3>
            <ul>
                <li><strong>Ariston AI Assistant:</strong> Your own digital assistant for any questions: <a href="https://aristonwashdry.gr/en/ai">aristonwashdry.gr/ai</a></li>
                <li><strong>Ariston Game:</strong> Have fun and play the game (Catch the Stain!)Maybe you reach the TOP 10: <a href="https://aristonwashdry.gr/game">aristonwashdry.gr/game</a></li>
                <li> <strong>ARISTON LUCKY WHEEL</strong> Ones a week spin the lucky wheel: <a href="https://aristonwashdry.gr/lucky-wheel">aristonwashdry.gr/lucky-wheel</a>  </li>
            </ul>

            <h3 style="border-bottom: 2px solid #eee; padding-bottom: 5px;">🎁 Privileges & Gifts</h3>
            <ul>
                <li><strong>Coupons & Offers:</strong> View your current discounts or create coupons to **gift** them to your loved ones: <a href="https://aristonwashdry.gr/en/updates-menu-en">aristonwashdry.gr/updates-menu</a></li>
                <li><strong>Digital Member Card:</strong> Always have your membership details with you: <a href="https://aristonwashdry.gr/en/member-info">aristonwashdry.gr/member-info</a></li>
            </ul>

            <h3 style="border-bottom: 2px solid #eee; padding-bottom: 5px;">⚙️ Account Management</h3>
            <ul>
                <li><strong>Personal Info:</strong> Manage and change your login details: <a href="https://aristonwashdry.gr/en/settings-menu">aristonwashdry.gr/settings-menu</a></li>
                <li><strong>Delete Profile:</strong> If you wish to delete your account: <a href="https://aristonwashdry.gr/en/delete-account">aristonwashdry.gr/delete-account</a></li>
            </ul>

            <h3 style="border-bottom: 2px solid #eee; padding-bottom: 5px;">✍️ Your Opinion Matters</h3>
            <p>
                Tell us what you think of our website: <a href="https://aristonwashdry.gr/en/site-review">Site Review</a><br>
                Rate your in-store experience: <a href="https://aristonwashdry.gr/en/reviews">Store Review</a>
            </p>

            <h3 style="border-bottom: 2px solid #eee; padding-bottom: 5px;">📞 Need Help?</h3>
            <p>Don't hesitate to contact us via our contact form: <a href="https://aristonwashdry.gr/en/contact">aristonwashdry.gr/epikoinonia</a></p>

            <p style="margin-top: 25px;">Thank you for trusting us!<br>
            <strong>Best regards,<br>The ARISTON Wash & Dry Team</strong></p>
            
            <div style="text-align: center; margin-top: 20px;">
                <a href="https://aristonwashdry.gr" target="_blank" style="text-decoration:none;">
                    <img src="https://aristonwashdry.gr/templates/images/1new.png" alt="ARISTON Wash & Dry" style="height:100px; width:auto;">
                </a>
            </div>

            <hr style="border: 0; border-top: 1px solid #eee; margin-top: 30px;">
            <p style='font-size: 12px; color: #666;'>
                This email was automatically sent by ARISTON Wash & Dry in accordance with our 
                <a href="https://aristonwashdry.gr/en/privacy">Privacy Policy</a>. 
                Your data is used exclusively for service purposes.
            </p>
        </body>
        </html>
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

<a href="https://aristonwashdry.gr" target="_blank" style="text-decoration:none;"><img src="https://aristonwashdry.gr/templates/images/1new.png" alt="ARISTON Wash & Dry" style="height:100px; width:auto; margin-top:12px;"></a>


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
    days_member = (datetime.now() - current_user.created_at).days
    # Δημιουργία token για τον τρέχοντα χρήστη
    token = get_secure_hash(current_user.id)
    return render_template("en/member-info.html", days_member=days_member, token=token)
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

<a href="https://aristonwashdry.gr" target="_blank" style="text-decoration:none;"><img src="https://aristonwashdry.gr/templates/images/1new.png" alt="ARISTON Wash & Dry" style="height:100px; width:auto; margin-top:12px;"></a>


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

<a href="https://aristonwashdry.gr" target="_blank" style="text-decoration:none;"><img src="https://aristonwashdry.gr/templates/images/1new.png" alt="ARISTON Wash & Dry" style="height:100px; width:auto; margin-top:12px;"></a>



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
    Verification.query.filter_by(user_id=user_id).delete()
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
@app.route('/en/card/<int:user_id>/<token>')
def public_card_en(user_id, token):
    # Έλεγχος αν το token είναι σωστό
    if token != get_secure_hash(user_id):
        return "Invalid Link", 403
        
    user = User.query.get_or_404(user_id)
    
    # ΕΛΕΓΧΟΣ: Αν η κάρτα είναι απενεργοποιημένη
    if not user.qr_enabled:
        return "This digital membership card has been deactivated by the owner.", 403

    delta = datetime.utcnow() - user.created_at
    days_member = delta.days
    
    return render_template('en/public_card_en.html', user=user, days_member=days_member)


@app.route('/en/announcement/<int:ann_id>')
@login_required
def view_announcement_en(ann_id):
    # Αναζήτηση ανακοίνωσης για τον χρήστη (English version)
    ann = Announcement.query.filter_by(id=ann_id, user_id=current_user.id).first_or_404()
    # Εδώ βεβαιώσου ότι το αρχείο λέγεται en/announcement_detail_en.html
    return render_template('en/announcement_detail_en.html', ann=ann)
@app.route('/en/smart-ai')
@login_required
def smart_ai_en():
    # Προσέχουμε να συμπεριλάβουμε το 'en/' στη διαδρομή του template
    return render_template('en/ai_concierge_en.html')








# ============================
#       RUN APP
# ============================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
