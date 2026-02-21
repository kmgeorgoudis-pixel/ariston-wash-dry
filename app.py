import os
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
    """Στέλνει email ενημέρωσης για τη χρήση του κουπονιού"""
    from flask_mail import Message
    subject = "Ενημέρωση Χρήσης Κουπονιού - Ariston Wash & Dry"
    
    if is_full:
        body = f"""
        Γεια σας {user.fullname},
        
        Σας ενημερώνουμε ότι το κουπόνι σας "{coupon.title}" χρησιμοποιήθηκε εξ ολοκλήρου.
        
        Σας ευχαριστούμε που μας προτιμάτε!
        """
    else:
        body = f"""
        Γεια σας {user.fullname},
        
        Μόλις χρησιμοποιήσατε {spent_amount}€ από το κουπόνι σας "{coupon.title}".
        
        Το νέο σας υπόλοιπο είναι: {coupon.amount}€
        
        Μπορείτε να δείτε την κάρτα σας εδώ: https://ariston-wash-dry.onrender.com/card/{user.id}
        """
    
    msg = Message(subject, recipients=[user.email])
    msg.body = body
    mail.send(msg)

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
def admin_use_coupon(id):
    if not current_user.is_admin:
        return redirect("/")

    coupon = Coupon.query.get(id)
    if not coupon:
        return redirect("/admin/users")

    user = User.query.get(coupon.user_id)
    action = request.form.get("action") 
    spent_raw = request.form.get("spent_amount")
    
    # Backup σιγουριάς: αν δεν έχει original_amount, το ορίζουμε τώρα
    if not coupon.original_amount:
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
                # remains used = False
        except ValueError:
            return redirect(f"/admin/users/{coupon.user_id}")

    db.session.commit()

    # Αποστολή Email ενημέρωσης
    if user and user.email:
        try:
            send_usage_email(user, coupon, spent_for_email, is_full)
        except Exception as e:
            print(f"📧 Email failed: {e}")

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

<a href="https://aristonwashdry.gr" target="_blank" style="text-decoration:none;"><img src="https://aristonwashdry.gr/templates/images/1new.png" alt="ARISTON Wash & Dry" style="height:100px; width:auto; margin-top:12px;"></a>



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




# ============================
#       RUN APP
# ============================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
