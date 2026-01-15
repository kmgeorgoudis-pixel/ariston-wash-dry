from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()
class Score(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nickname = db.Column(db.String(50), unique=True, nullable=False)
    best_score = db.Column(db.Integer, default=0)
    last_played = db.Column(db.DateTime, default=datetime.utcnow)
    def __repr__(self):
        return f"<Score {self.nickname} - {self.best_score}>"
class ContactMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)

    name = db.Column(db.String(120), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    subject = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref="contact_messages", lazy=True)


class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    # Σύνδεση με User
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship("User", backref="reviews")

    # Ερώτηση 1
    rating = db.Column(db.Integer)

    # Ερώτηση 2
    q2 = db.Column(db.Integer)

    # Ερώτηση 3
    q3 = db.Column(db.Integer)

    # Ερώτηση 4
    q4 = db.Column(db.Integer)

    # Ερώτηση 5
    recommend = db.Column(db.String(20))

    # Ερώτηση 6
    comment_like = db.Column(db.Text)

    # Ερώτηση 7
    comment_improve = db.Column(db.Text)

    # Ερώτηση 8
    name = db.Column(db.String(120))

    # Ερώτηση 9
    want_contact = db.Column(db.String(10))

    # Ερώτηση 10
    contact_info = db.Column(db.String(200))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Coupon(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    # ΜΟΝΟ ΜΙΑ ΦΟΡΑ το user_id
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    title = db.Column(db.String(100))
    description = db.Column(db.Text)
    amount = db.Column(db.Float)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    used = db.Column(db.Boolean, default=False)
    used_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Announcement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref="announcements")


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    fullname = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    reset_code = db.Column(db.String(6), nullable=True)
    is_admin = db.Column(db.Boolean, default=False)
    name = db.Column(db.String(120))
    


def init_db(app):
    db.init_app(app)