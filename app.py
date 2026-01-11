from flask import Flask, render_template, request, redirect, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from email.header import Header
from database import db, init_db

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
Για να δείτε όλα τα κουπόνια σας, συνδεθείτε στον λογαριασμό σας:
https://aristonwashdry.gr/coupons
━━━━━━━━━━━━━━━━━━━━━━━━━━

Με εκτίμηση,
Η ομάδα του ARISTON Wash & Dry

<a href="https://aristonwashdry.gr" target="_blank" style="text-decoration:none;">
  <img src="https://aristonwashdry.gr/templates/images/1new.png"
       alt="ARISTON Wash & Dry"
       style="height:100px; width:auto; margin-top:12px;">
</a>
    """

    send_email(user.email, "Νέο Κουπόνι από το ARISTON Wash & Dry", body)


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
@app.route("/")
def home():
    return render_template("index.html")
@app.route("/check_nickname", methods=["POST"])
def check_nickname():
    data = request.get_json()
    nickname = data.get("nickname", "").strip()

    if not nickname:
        return {"ok": False, "error": "Empty nickname"}

    exists = Score.query.filter_by(nickname=nickname).first()
    return {"exists": bool(exists)}
@app.route("/submit_score", methods=["POST"])
def submit_score():
    data = request.get_json()
    nickname = data.get("nickname", "").strip()
    score = int(data.get("score", 0))

    if not nickname:
        return {"ok": False, "error": "No nickname"}

    entry = Score.query.filter_by(nickname=nickname).first()

    if entry:
        if score > entry.best_score:
            entry.best_score = score
            entry.last_played = datetime.utcnow()
            db.session.commit()
    else:
        new_entry = Score(
            nickname=nickname,
            best_score=score,
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
@app.route("/ai")
def ai_page():
    return render_template("ai/ai.html")
@app.route("/game")
def game():
    return render_template("game.html")
@app.route("/timokatalogos")
def timokatalogos():
    return render_template("timokatalogos.html")
@app.route("/coupon/<int:coupon_id>")
@login_required
def coupon_details(coupon_id):
    coupon = Coupon.query.filter_by(id=coupon_id, user_id=current_user.id).first_or_404()
    return render_template("coupon_details.html", coupon=coupon)
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
        body = (
            f"Αγαπητέ/ή {fullname},\n\n"
            "Καλωσόρισες στην οικογένεια του Ariston Wash & Dry!\n\n"
            "Η εγγραφή σου ολοκληρώθηκε με επιτυχία και πλέον είσαι επίσημα μέλος της υπηρεσίας μας.\n"
            "Από σήμερα θα λαμβάνεις αποκλειστικές προσφορές, κουπόνια, εκπτώσεις και ενημερώσεις "
            "για νέες υπηρεσίες που ετοιμάζουμε για τα μέλη μας.\n\n"
            "Στόχος μας είναι να κάνουμε το πλύσιμο και το στέγνωμα των ρούχων σου πιο εύκολα, "
            "πιο γρήγορα και πιο οικονομικά από ποτέ.\n\n"
            "Σε ευχαριστούμε που μας εμπιστεύτηκες.\n"
            "Αν χρειαστείς οτιδήποτε, είμαστε πάντα δίπλα σου.\n\n"
            "Με εκτίμηση,\n"
            "Η ομάδα του Ariston Wash & Dry\n\n"
            '<a href="https://aristonwashdry.gr" target="_blank" style="text-decoration:none;">'
            '<img src="https://aristonwashdry.gr/templates/images/1new.png" '
            'alt="ARISTON Wash & Dry" style="height:100px; width:auto; margin-top:12px;">'
            "</a>"
        )

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

@app.route("/admin/coupons/send", methods=["POST"])
@login_required
def admin_send_coupons_selected():
    if not current_user.is_admin:
        return redirect("/")

    title = request.form.get("title")
    description = request.form.get("description")

    # Μετατροπή από string -> Python date
    start_date = datetime.strptime(request.form.get("start_date"), "%Y-%m-%d").date()
    end_date = datetime.strptime(request.form.get("end_date"), "%Y-%m-%d").date()

    # Ποσό κουπονιού
    amount_raw = request.form.get("amount")
    amount = float(amount_raw) if amount_raw else 0.0

    selected_users = request.form.getlist("selected_users")

    for user_id in selected_users:
        user = User.query.get(user_id)

        coupon = Coupon(
            user_id=user_id,
            title=title,
            description=description,
            amount=amount,
            start_date=start_date,
            end_date=end_date
        )

        db.session.add(coupon)
        db.session.flush()  # παίρνει ID πριν το commit

        send_coupon_email(user, coupon)

    db.session.commit()

    flash("Τα κουπόνια στάλθηκαν επιτυχώς.", "success")
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
Δες τις ανακοινώσεις σου απο εδώ: https://aristonwashdry.gr/updates 

Σε ευχαριστούμε που είσαι μέλος της οικογένειας ARISTON.

Με εκτίμηση,
ARISTON Wash & Dry
https://aristonwashdry.gr/

<a href="https://aristonwashdry.gr" target="_blank" style="text-decoration:none;">
  <img src="https://aristonwashdry.gr/templates/images/1new.png"
       alt="ARISTON Wash & Dry"
       style="height:100px; width:auto; margin-top:12px;">
</a>
"""

    # Χρήση της send_email που ήδη δουλεύει
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
@app.route("/admin/announcements/send", methods=["POST"])
@login_required
def admin_send_announcements():
    if not current_user.is_admin:
        return redirect("/")

    title = request.form.get("title")
    description = request.form.get("description")

    # 1 ανακοίνωση στη βάση για όλους
    announcement = Announcement(
        user_id=None,   # 🔥 ΑΝΑΚΟΙΝΩΣΗ ΓΙΑ ΟΛΟΥΣ
        title=title,
        description=description
    )
    db.session.add(announcement)
    db.session.commit()

    # Email σε όλους τους χρήστες
    users = User.query.all()
    for user in users:
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

<a href="https://aristonwashdry.gr" target="_blank" style="text-decoration:none;">
  <img src="https://aristonwashdry.gr/templates/images/1new.png"
       alt="ARISTON Wash & Dry"
       style="height:100px; width:auto; margin-top:12px;">
</a>
"""

        # Αποστολή email μέσω Resend
        send_email(
            user.email,
            subject,
            body
        )

    flash("Η ανακοίνωση στάλθηκε σε όλους.", "success")
    return redirect("/admin/announcements")
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

        body = (
            f"Αγαπητέ/ή {user.fullname},\n\n"
            "Λάβαμε αίτημα για επαναφορά του κωδικού πρόσβασής σας στο ARISTON Wash & Dry.\n"
            "Για να συνεχίσετε, χρησιμοποιήστε τον παρακάτω 6ψήφιο κωδικό επαλήθευσης:\n\n"
            f"{code}\n\n"
            "Ο κωδικός ισχύει για περιορισμένο χρονικό διάστημα.\n\n"
            "Αν δεν ζητήσατε εσείς την επαναφορά, μπορείτε να αγνοήσετε αυτό το μήνυμα.\n\n"
            "Με εκτίμηση,\n"
            "Η ομάδα του ARISTON Wash & Dry"
            "   https://aristonwashdry.gr/\n\n"
            '<a href="https://aristonwashdry.gr" target="_blank" style="text-decoration:none;">'
            '<img src="https://aristonwashdry.gr/templates/images/1new.png" '
            'alt="ARISTON Wash & Dry" style="height:100px; width:auto; margin-top:12px;">'
            "</a>"
        )

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
    send_email(
        to=current_user.email,
        subject="Επιβεβαίωση Διαγραφής Λογαριασμού - ARISTON Wash & Dry",
        body=(
            f"Αγαπητέ/ή {current_user.fullname},\n\n"
            "Ο λογαριασμός σας στο ARISTON Wash & Dry διαγράφηκε οριστικά.\n"
            "Όλα τα προσωπικά σας δεδομένα, οι ρυθμίσεις και το ιστορικό χρήσης "
            "έχουν αφαιρεθεί από το σύστημά μας σύμφωνα με την πολιτική απορρήτου.\n\n"
            "Δεν είστε πλέον μέλος της υπηρεσίας.\n\n"
            "Ευχαριστούμε που χρησιμοποιήσατε το ARISTON Wash & Dry."
            "https://aristonwashdry.gr/\n\n"
            '<a href="https://aristonwashdry.gr" target="_blank" style="text-decoration:none;">'
            '<img src="https://aristonwashdry.gr/templates/images/1new.png" '
            'alt="ARISTON Wash & Dry" style="height:100px; width:auto; margin-top:12px;">'
            "</a>"
        )
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

        flash("Ο κωδικός ενημερώθηκε επιτυχώς.", "success")
        return redirect("/change-password")   # ⭐ ΕΔΩ Η ΑΛΛΑΓΗ

    return render_template("change-password.html")


# ============================
#       RUN APP
# ============================

if __name__ == "__main__":
    app.run(debug=True)