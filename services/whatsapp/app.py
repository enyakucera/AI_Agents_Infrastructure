from flask import Flask, request, jsonify
from twilio.rest import Client
import os

app = Flask(__name__)

# Konfigurace Twilio z prostředí
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "service": "whatsapp"}), 200

@app.route('/send', methods=['POST'])
def send_whatsapp():
    """
    Očekávaný JSON:
    {
        "to": "+420123456789",  # musí začínat +
        "message": "Text zprávy"
    }
    """
    try:
        data = request.get_json()
        recipient = data.get('to')
        message = data.get('message')
        
        if not all([recipient, message]):
            return jsonify({"error": "Missing required fields: to, message"}), 400
        
        if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_NUMBER]):
            return jsonify({"error": "WhatsApp service not configured (missing Twilio credentials)"}), 500
        
        # Přidání whatsapp: prefixu pokud chybí
        if not recipient.startswith("whatsapp:"):
            recipient = f"whatsapp:{recipient}"
        
        twilio_from = TWILIO_WHATSAPP_NUMBER
        if not twilio_from.startswith("whatsapp:"):
            twilio_from = f"whatsapp:{twilio_from}"
        
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        msg = client.messages.create(
            from_=twilio_from,
            body=message,
            to=recipient
        )
        
        return jsonify({
            "success": True,
            "message": "WhatsApp message sent successfully",
            "message_sid": msg.sid,
            "to": recipient
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5004, debug=False)
