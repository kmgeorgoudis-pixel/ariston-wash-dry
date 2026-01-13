import os
from datetime import datetime, date
import requests

from app import app  # ΑΝ ΤΟ ΚΥΡΙΟ ΑΡΧΕΙΟ ΣΟΥ ΔΕΝ ΛΕΓΕΤΑΙ app.py, ΑΛΛΑΞΕ ΤΟ ΑΥΤΟ
from models import db, User


# ==============================
# ΡΥΘΜΙΣΕΙΣ BREVO / EMAIL
# ==============================

BREVO_API_KEY = os.getenv("BREVO_API_KEY")  # Βάλε το στο Render Environment
FROM_EMAIL = os.getenv("FROM_EMAIL", "info@aristonwashdry.gr")
FROM_NAME = os.getenv("FROM_NAME", "ARISTON Wash & Dry")
SITE_URL = "https://aristonwashdry.gr/"


def send_email(to_email, to_name, subject, html_content):
    """
    Στέλνει email μέσω Brevo API.
    """
    if not BREVO_API_KEY:
        print("❌ BREVO_API_KEY δεν είναι ρυθμισμένο. Δεν στάλθηκε email.")
        return

    url = "https://api.brevo.com/v3/smtp/email"

    payload = {
        "sender": {
            "name": FROM_NAME,
            "email": FROM_EMAIL,
        },
        "to": [
            {
                "email": to_email,
                "name": to_name or "",
            }
        ],
        "subject": subject,
        "htmlContent": html_content,
    }

    headers = {
        "accept": "application/json",
        "api-key": BREVO_API_KEY,
        "content-type": "application/json",
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        if response.status_code >= 200 and response.status_code < 300:
            print(f"✅ Email στάλθηκε σε {to_email} με θέμα: {subject}")
        else:
            print(f"❌ Σφάλμα αποστολής email σε {to_email}: {response.status_code} {response.text}")
    except Exception as e:
        print(f"❌ Εξαίρεση κατά την αποστολή email σε {to_email}: {e}")


# ==============================
# EMAIL TEMPLATES ΜΕ ΤΟ LINK + INFO ΚΟΥΠΟΝΙΩΝ
# ==============================

def footer_html():
    return f"""
<br><br>
Μπορείς να επισκεφθείς το site μας εδώ:<br>
<a href="{SITE_URL}">{SITE_URL}</a><br><br>
Τα κουπόνια ισχύουν για 15 ημέρες από τη στιγμή που προστέθηκαν στην πλατφόρμα.<br><br>
Με εκτίμηση,<br>
Η ομάδα του ARISTON Wash & Dry
"""


def email_15_days(fullname):
    subject = "15 μέρες μαζί – σε ευχαριστούμε που μας εμπιστεύεσαι!"
    html = f"""
Αγαπητέ/ή {fullname},<br><br>
Πριν από 15 ημέρες έκανες την εγγραφή σου στο ARISTON Wash & Dry και θέλουμε να σε ευχαριστήσουμε θερμά για την εμπιστοσύνη σου.<br><br>
Στόχος μας είναι κάθε πλύσιμο και κάθε επίσκεψη στο κατάστημά μας να είναι όσο πιο εύκολη, γρήγορη και αξιόπιστη γίνεται. Η παρουσία σου ως μέλος μάς δίνει δύναμη να γινόμαστε συνεχώς καλύτεροι.<br><br>
Σε ευχαριστούμε που επέλεξες το ARISTON Wash & Dry.
{footer_html()}
"""
    return subject, html


def email_30_days(fullname):
    subject = "30 μέρες μαζί – η εμπιστοσύνη σου σημαίνει πολλά για εμάς"
    html = f"""
Αγαπητέ/ή {fullname},<br><br>
Συμπληρώθηκε ένας μήνας από τότε που έγινες μέλος του ARISTON Wash & Dry και θέλουμε να σου εκφράσουμε ένα μεγάλο ευχαριστώ.<br><br>
Η επιλογή σου να μας εμπιστεύεσαι για τη φροντίδα των ρούχων σου είναι τιμή για εμάς. Κάθε μέρα προσπαθούμε να προσφέρουμε υπηρεσίες υψηλής ποιότητας, με συνέπεια, καθαριότητα και επαγγελματισμό.<br><br>
Σε ευχαριστούμε που είσαι μέρος της οικογένειας του ARISTON Wash & Dry.
{footer_html()}
"""
    return subject, html


def email_60_days(fullname):
    subject = "60 μέρες στο ARISTON – συνεχίζουμε μαζί με την ίδια φροντίδα"
    html = f"""
Αγαπητέ/ή {fullname},<br><br>
Έχουν περάσει 60 ημέρες από τότε που έγινες μέλος του ARISTON Wash & Dry και θέλουμε να σου πούμε ένα ειλικρινές ευχαριστώ για την εμπιστοσύνη σου.<br><br>
Η σταθερή παρουσία σου μάς δείχνει ότι κάνουμε σωστά τη δουλειά μας και μας δίνει κίνητρο να συνεχίσουμε να βελτιωνόμαστε καθημερινά.<br><br>
Σε ευχαριστούμε που μας επιλέγεις.
{footer_html()}
"""
    return subject, html


def email_100_days(fullname):
    subject = "100 μέρες μαζί – ένα δώρο από εμάς για εσένα"
    html = f"""
Αγαπητέ/ή {fullname},<br><br>
Σήμερα συμπληρώνεις 100 ημέρες ως μέλος του ARISTON Wash & Dry και θέλουμε να σου εκφράσουμε ένα μεγάλο ευχαριστώ για την εμπιστοσύνη και τη σταθερή προτίμησή σου.<br><br>
Ως ένδειξη εκτίμησης, σου προσφέρουμε:<br><br>
• 1 δωρεάν πλύσιμο στο πλυντήριο 10kg<br>
• 1 δωρεάν στέγνωμα στο στεγνωτήριο 14kg<br><br>
Για να εξαργυρώσεις το δώρο σου, απλώς δείξε αυτό το email στο κατάστημα.<br><br>
Σε ευχαριστούμε που είσαι μέρος της οικογένειας του ARISTON Wash & Dry.
{footer_html()}
"""
    return subject, html


def email_365_days(fullname):
    subject = "1 χρόνος στο ARISTON – ένα μεγάλο ευχαριστώ από εμάς"
    html = f"""
Αγαπητέ/ή {fullname},<br><br>
Σήμερα συμπληρώνεις έναν ολόκληρο χρόνο ως μέλος του ARISTON Wash & Dry και θέλουμε να σου εκφράσουμε την πιο θερμή μας ευγνωμοσύνη.<br><br>
Ως ένδειξη εκτίμησης για τη στήριξή σου, σου προσφέρουμε:<br><br>
• 2 δωρεάν πλύσεις στο πλυντήριο 10kg<br>
• 2 δωρεάν στεγνώματα στο στεγνωτήριο 14kg<br>
• 1 επιπλέον δωρεάν στέγνωμα<br><br>
Για να εξαργυρώσεις τα δώρα σου, απλώς δείξε αυτό το email στο κατάστημα.<br><br>
Σε ευχαριστούμε που είσαι μέρος της οικογένειας του ARISTON Wash & Dry.
{footer_html()}
"""
    return subject, html


# ==============================
# ΥΠΟΛΟΓΙΣΜΟΣ ΗΜΕΡΩΝ & MILESTONES
# ==============================

def calculate_days_member(created_at):
    """
    Υπολογίζει πόσες μέρες είναι μέλος ο χρήστης.
    """
    if not created_at:
        return None

    # Αν created_at είναι datetime, παίρνουμε μόνο την ημερομηνία
    if isinstance(created_at, datetime):
        created_date = created_at.date()
    elif isinstance(created_at, date):
        created_date = created_at
    else:
        return None

    today = date.today()
    delta = today - created_date
    return delta.days


def process_user_milestones(user):
    """
    Ελέγχει τα milestones για έναν συγκεκριμένο χρήστη και στέλνει email αν χρειάζεται.
    """
    days_member = calculate_days_member(user.created_at)
    if days_member is None:
        return

    fullname = user.fullname or user.name or user.email

    # 15 μέρες
    if days_member == 15 and not user.milestone_15_sent:
        subject, html = email_15_days(fullname)
        send_email(user.email, fullname, subject, html)
        user.milestone_15_sent = True
        print(f"🔔 15 days milestone για {user.email}")

    # 30 μέρες
    if days_member == 30 and not user.milestone_30_sent:
        subject, html = email_30_days(fullname)
        send_email(user.email, fullname, subject, html)
        user.milestone_30_sent = True
        print(f"🔔 30 days milestone για {user.email}")

    # 60 μέρες
    if days_member == 60 and not user.milestone_60_sent:
        subject, html = email_60_days(fullname)
        send_email(user.email, fullname, subject, html)
        user.milestone_60_sent = True
        print(f"🔔 60 days milestone για {user.email}")

    # 100 μέρες
    if days_member == 100 and not user.milestone_100_sent:
        subject, html = email_100_days(fullname)
        send_email(user.email, fullname, subject, html)
        user.milestone_100_sent = True
        print(f"🎁 100 days milestone (με δώρα) για {user.email}")

    # 365 μέρες
    if days_member == 365 and not user.milestone_365_sent:
        subject, html = email_365_days(fullname)
        send_email(user.email, fullname, subject, html)
        user.milestone_365_sent = True
        print(f"🎁 365 days milestone (με μεγάλα δώρα) για {user.email}")


def run_milestone_worker():
    """
    Κύρια συνάρτηση: τρέχει μία φορά, ελέγχει όλους τους χρήστες και ενημερώνει milestones.
    Αυτή θα καλέσει το Render Cron Job 1 φορά την ημέρα.
    """
    with app.app_context():
        print("🚀 Ξεκίνησε ο milestone worker...")
        users = User.query.all()
        print(f"Βρέθηκαν {len(users)} χρήστες στη βάση.")

        for user in users:
            try:
                process_user_milestones(user)
            except Exception as e:
                print(f"❌ Σφάλμα σε χρήστη {user.email}: {e}")

        try:
            db.session.commit()
            print("✅ Τα milestones αποθηκεύτηκαν στη βάση.")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Σφάλμα στο commit της βάσης: {e}")

        print("🏁 Ο milestone worker ολοκλήρωσε.")


if __name__ == "__main__":
    run_milestone_worker()