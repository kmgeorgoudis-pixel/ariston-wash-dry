from database import db, User
from werkzeug.security import generate_password_hash

def register_user(fullname, email, password, confirm):
    if password != confirm:
        return "Οι κωδικοί δεν ταιριάζουν."

    # Έλεγχος αν υπάρχει ήδη email
    existing = User.query.filter_by(email=email).first()
    if existing:
        return "Το email υπάρχει ήδη."

    hashed = generate_password_hash(password)

    # Δημιουργία νέου χρήστη
    user = User(fullname=fullname, email=email, password=hashed)
    db.session.add(user)
    db.session.commit()

    return "OK"