from app import app
from database import db, User

email_to_delete = "kmgeorgoudis@outlook.com.gr"

with app.app_context():
    user = User.query.filter_by(email=email_to_delete).first()
    if user:
        db.session.delete(user)
        db.session.commit()
        print(f"Ο χρήστης {email_to_delete} διαγράφηκε.")
    else:
        print("Δεν βρέθηκε χρήστης με αυτό το email.")