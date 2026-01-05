import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_welcome_email(fullname, user_email):
    sender_email = "aristonwashing@gmail.com"
    sender_password = "nrzgbngtczrfgmfi"

    subject = "Καλωσόρισες στο Ariston Wash & Dry!"

    body = f"""
Αγαπητέ/ή {fullname},

Καλωσόρισες στην οικογένεια του Ariston Wash & Dry!

Η εγγραφή σου ολοκληρώθηκε με επιτυχία και πλέον είσαι επίσημα μέλος της υπηρεσίας μας.
Από σήμερα θα λαμβάνεις αποκλειστικές προσφορές, κουπόνια, εκπτώσεις και ενημερώσεις για νέες υπηρεσίες που ετοιμάζουμε για τα μέλη μας.

Στόχος μας είναι να κάνουμε το πλύσιμο και το στέγνωμα των ρούχων σου πιο εύκολα, πιο γρήγορα και πιο οικονομικά από ποτέ.

Σε ευχαριστούμε που μας εμπιστεύτηκες.
Αν χρειαστείς οτιδήποτε, είμαστε πάντα δίπλα σου.

Με εκτίμηση,
Η ομάδα του Ariston Wash & Dry
"""

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = user_email
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, user_email, msg.as_string())
        server.quit()
        print("Email sent successfully!")
    except Exception as e:
        print("Error sending email:", e)