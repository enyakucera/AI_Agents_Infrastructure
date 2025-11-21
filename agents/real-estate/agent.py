import os
import time
import requests
import threading
from flask import Flask, request, jsonify

# Načtení konfigurace z prostředí
# Používáme globální proměnné, které budeme moci měnit za běhu
config = {
    "LOCATION": os.getenv("LOCATION", "Praha"),
    "MIN_AREA": int(os.getenv("MIN_AREA", 50)),
    "INTERVAL": int(os.getenv("INTERVAL", 10800)),  # v sekundách (3 hodiny)
    "RUNNING": True  # Stav agenta (běží/zastaven)
}

EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")
USER_WHATSAPP_NUMBER = os.getenv("USER_WHATSAPP_NUMBER")

# URL mikroslužeb (v Docker síti)
SCRAPER_URL = os.getenv("SCRAPER_URL", "http://scraper:5001")
AI_ANALYZER_URL = os.getenv("AI_ANALYZER_URL", "http://ai-analyzer:5002")
EMAIL_URL = os.getenv("EMAIL_URL", "http://email:5003")
WHATSAPP_URL = os.getenv("WHATSAPP_URL", "http://whatsapp:5004")

# Flask aplikace pro ovládání agenta
app = Flask(__name__)

@app.route('/status', methods=['GET'])
def get_status():
    return jsonify({
        "status": "running" if config["RUNNING"] else "stopped",
        "config": {
            "location": config["LOCATION"],
            "min_area": config["MIN_AREA"],
            "interval": config["INTERVAL"]
        }
    })

@app.route('/start', methods=['POST'])
def start_agent():
    config["RUNNING"] = True
    return jsonify({"message": "Agent byl spuštěn."})

@app.route('/stop', methods=['POST'])
def stop_agent():
    config["RUNNING"] = False
    return jsonify({"message": "Agent byl pozastaven."})

@app.route('/config', methods=['POST'])
def update_config():
    data = request.get_json()
    
    if "location" in data:
        config["LOCATION"] = data["location"]
    if "min_area" in data:
        try:
            config["MIN_AREA"] = int(data["min_area"])
        except ValueError:
            return jsonify({"error": "min_area musí být číslo"}), 400
    if "interval" in data:
        try:
            config["INTERVAL"] = int(data["interval"])
        except ValueError:
            return jsonify({"error": "interval musí být číslo"}), 400
            
    return jsonify({
        "message": "Konfigurace aktualizována.",
        "config": {
            "location": config["LOCATION"],
            "min_area": config["MIN_AREA"],
            "interval": config["INTERVAL"]
        }
    })

@app.route('/run-now', methods=['POST'])
def run_now():
    """Okamžité spuštění vyhledávání (v novém vlákně, aby neblokovalo request)"""
    threading.Thread(target=run_cycle).start()
    return jsonify({"message": "Vyhledávání spuštěno na pozadí."})

def run_api_server():
    app.run(host='0.0.0.0', port=5005, debug=False, use_reloader=False)

def scrape_listings():
    """Volá scraper service pro získání nabídek"""
    urls = [
        f"https://www.sreality.cz/hledani/pronajem/byty?region={config['LOCATION']}",
        f"https://www.bezrealitky.cz/vypis/nabidka-pronajem/byt/{config['LOCATION']}",
        f"https://reality.idnes.cz/s/pronajem/byty/{config['LOCATION']}/",
        f"https://reality.bazos.cz/inzeraty/{config['LOCATION']}-byt/"
    ]
    
    try:
        response = requests.post(
            f"{SCRAPER_URL}/scrape",
            json={
                "urls": urls,
                "keywords": ["byt"]
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get("listings", [])
        else:
            print(f"Scraper error: {response.status_code}")
            return []
    except Exception as e:
        print(f"Error calling scraper service: {e}")
        return []

def analyze_listings(listings):
    """Volá AI analyzer service pro analýzu nabídek"""
    if not listings:
        return "Žádné nabídky k analýze."
    
    # Připravit text nabídek
    listings_text = "\n".join([
        f"- {item.get('text', 'N/A')} [{item.get('url', '')}]" 
        for item in listings[:50]  # omezit na 50 nabídek
    ])
    
    prompt = f"""Vyber nejlepší nabídky pronájmu bytů v {config['LOCATION']} z následujícího seznamu:

{listings_text}

Kritéria: 
- Plocha alespoň {config['MIN_AREA']} m²
- Vhodné pro dlouhodobý pronájem
- Přijatelná cena

Vrať stručný seznam TOP 5 nejlepších nabídek s odůvodněním."""
    
    try:
        response = requests.post(
            f"{AI_ANALYZER_URL}/analyze",
            json={
                "prompt": prompt,
                "model": "gpt-4o",
                "temperature": 0.2,
                "max_tokens": 1000
            },
            timeout=120
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get("analysis", "Analýza selhala.")
        else:
            print(f"AI Analyzer error: {response.status_code}")
            return f"Nalezeno {len(listings)} nabídek, ale analýza selhala."
    except Exception as e:
        print(f"Error calling AI analyzer service: {e}")
        return f"Nalezeno {len(listings)} nabídek:\n\n{listings_text[:1000]}"

def send_email(subject, body):
    """Volá email service pro odeslání e-mailu"""
    try:
        response = requests.post(
            f"{EMAIL_URL}/send",
            json={
                "to": EMAIL_RECEIVER,
                "subject": subject,
                "body": body
            },
            timeout=30
        )
        
        if response.status_code == 200:
            print("E-mail odeslán.")
        else:
            print(f"Email service error: {response.status_code}")
    except Exception as e:
        print(f"Error calling email service: {e}")

def send_whatsapp_message(body):
    """Volá WhatsApp service pro odeslání zprávy"""
    try:
        response = requests.post(
            f"{WHATSAPP_URL}/send",
            json={
                "to": USER_WHATSAPP_NUMBER,
                "message": body
            },
            timeout=30
        )
        
        if response.status_code == 200:
            print("WhatsApp zpráva odeslána.")
        else:
            print(f"WhatsApp service error: {response.status_code}")
    except Exception as e:
        print(f"Error calling WhatsApp service: {e}")

def run_cycle():
    """Jeden cyklus vyhledávání"""
    print("\n" + "="*50)
    print(f"Spouštím cyklus vyhledávání pro {config['LOCATION']} (min {config['MIN_AREA']} m²)...")
    print("="*50)
    
    # Krok 1: Scraping
    print("1. Scrapování nabídek...")
    listings = scrape_listings()
    
    if listings:
        print(f"✓ Nalezeno {len(listings)} nabídek.")
        
        # Krok 2: AI Analýza
        print("2. Analýza pomocí AI...")
        analysis = analyze_listings(listings)
        print(f"✓ Analýza dokončena.")
        
        # Krok 3: Odeslání e-mailu
        print("3. Odesílání e-mailu...")
        send_email(
            subject=f"Aktuální nabídky pronájmu v {config['LOCATION']}",
            body=analysis
        )
        
        # Krok 4: Odeslání WhatsApp zprávy
        print("4. Odesílání WhatsApp zprávy...")
        send_whatsapp_message(analysis)
        
        print("✓ Cyklus dokončen.")
    else:
        print("✗ Žádné nabídky nenalezeny.")

def run_agent():
    """Hlavní smyčka agenta - orchestrace mikroslužeb"""
    print(f"Real Estate Agent spuštěn.")
    print(f"API server běží na portu 5005")
    
    # Spuštění API serveru v samostatném vlákně
    api_thread = threading.Thread(target=run_api_server)
    api_thread.daemon = True
    api_thread.start()
    
    while True:
        if config["RUNNING"]:
            run_cycle()
        else:
            print("Agent je pozastaven.")
        
        # Spánek podle intervalu
        print(f"\nČekám {config['INTERVAL']} sekund do dalšího cyklu...")
        time.sleep(config['INTERVAL'])

if __name__ == "__main__":
    run_agent()
