from flask import Flask, request, jsonify
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

app = Flask(__name__)

# Konfigurace z prostředí
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "service": "email"}), 200

@app.route('/send', methods=['POST'])
def send_email():
    """
    Očekávaný JSON:
    {
        "to": "recipient@example.com",
        "subject": "Předmět zprávy",
        "body": "Text zprávy",
        "html": false  # volitelné, pokud true, body bude HTML
    }
    """
    try:
        data = request.get_json()
        recipient = data.get('to')
        subject = data.get('subject')
        body = data.get('body')
        is_html = data.get('html', False)
        
        if not all([recipient, subject, body]):
            return jsonify({"error": "Missing required fields: to, subject, body"}), 400
        
        if not EMAIL_SENDER or not EMAIL_PASSWORD:
            return jsonify({"error": "Email service not configured (missing credentials)"}), 500
        
        msg = MIMEMultipart()
        msg["From"] = EMAIL_SENDER
        msg["To"] = recipient
        msg["Subject"] = subject
        
        mime_type = "html" if is_html else "plain"
        msg.attach(MIMEText(body, mime_type))
        
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, recipient, msg.as_string())
        server.quit()
        
        return jsonify({
            "success": True,
            "message": "Email sent successfully",
            "to": recipient
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5003, debug=False)
