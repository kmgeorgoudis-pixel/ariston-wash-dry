from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()


class Score(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nickname = db.Column(db.String(50), unique=True, nullable=False)
    best_score = db.Column(db.Integer, default=0)
    last_played = db.Column(db.DateTime, default=datetime.utcnow)
    time_played = db.Column(db.Integer, default=0)

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

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship("User", backref="reviews")

    rating = db.Column(db.Integer)
    q2 = db.Column(db.Integer)
    q3 = db.Column(db.Integer)
    q4 = db.Column(db.Integer)
    recommend = db.Column(db.String(20))
    comment_like = db.Column(db.Text)
    comment_improve = db.Column(db.Text)
    name = db.Column(db.String(120))
    want_contact = db.Column(db.String(10))
    contact_info = db.Column(db.String(200))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Coupon(db.Model):
    id = db.Column(db.Integer, primary_key=True)

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


class siteReview(db.Model):
    __tablename__ = "reviews"

    id = db.Column(db.Integer, primary_key=True)

    q1 = db.Column(db.String(120), nullable=False)
    q2 = db.Column(db.String(120), nullable=False)
    q3 = db.Column(db.String(120), nullable=False)
    q4 = db.Column(db.String(120), nullable=False)
    q5 = db.Column(db.String(120), nullable=False)

    t1 = db.Column(db.Text, nullable=True)
    t2 = db.Column(db.Text, nullable=True)
    t3 = db.Column(db.Text, nullable=True)
    t4 = db.Column(db.Text, nullable=True)
    t5 = db.Column(db.Text, nullable=True)

    email = db.Column(db.String(120), nullable=True)
    phone = db.Column(db.String(50), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Review {self.id}>"


def init_db(app):
    db.init_app(app)