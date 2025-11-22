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

@app.route('/prompt', methods=['POST'])
def handle_prompt():
    """Zpracování přirozeného jazyka od uživatele"""
    data = request.get_json()
    user_message = data.get("message", "")
    
    if not user_message:
        return jsonify({"error": "Prázdná zpráva"}), 400
        
    # 1. Interpretace záměru pomocí AI
    intent = interpret_intent(user_message)
    
    if not intent:
        # Fallback: Pokud se nepodaří zjistit záměr, předpokládáme dotaz na analýzu
        intent = {"command": "ANALYZE_WITH_PROMPT", "parameters": {}}
        
    command = intent.get("command")
    params = intent.get("parameters", {})
    
    response_msg = ""
    
    # 2. Vykonání akce
    if command == "UPDATE_CONFIG":
        if "location" in params:
            config["LOCATION"] = params["location"]
        if "min_area" in params:
            config["MIN_AREA"] = int(params["min_area"])
        if "interval" in params:
            config["INTERVAL"] = int(params["interval"])
        response_msg = f"Konfigurace aktualizována: {config['LOCATION']}, min {config['MIN_AREA']}m2."
        
    elif command == "RUN_ONCE":
        # Spustit jedno hledání s parametry (nebo defaultními) - standardní cyklus s emailem
        threading.Thread(target=run_cycle, kwargs={"overrides": params}).start()
        response_msg = f"Spouštím jednorázové hledání pro {params.get('location', config['LOCATION'])} (výsledky přijdou e-mailem)."
        
    elif command == "START":
        config["RUNNING"] = True
        response_msg = "Agent byl spuštěn."
        
    elif command == "STOP":
        config["RUNNING"] = False
        response_msg = "Agent byl pozastaven."

    elif command == "ANALYZE_WITH_PROMPT":
        # Synchronní zpracování dotazu - vrátí odpověď přímo sem
        loc = params.get("location", config["LOCATION"])
        
        # Získání dat
        listings = scrape_listings_with_params(loc)
        
        if not listings:
            response_msg = f"Pro lokalitu {loc} nebyly nalezeny žádné nabídky, takže nemohu odpovědět na dotaz."
        else:
            # AI Analýza s dotazem uživatele
            response_msg = analyze_custom_query(listings, user_message, loc)
        
    else:
        response_msg = f"Neznámý příkaz: {command}"
        
    return jsonify({"message": response_msg, "intent": intent})

def interpret_intent(user_message):
    """Převod přirozeného jazyka na strukturovaný příkaz pomocí AI"""
    system_prompt = """Jsi řídicí systém pro realitního agenta. Tvým úkolem je převést přání uživatele na JSON příkaz.
Dostupné příkazy:
- UPDATE_CONFIG: Trvalá změna nastavení (lokalita, plocha, interval).
- RUN_ONCE: Jednorázové spuštění standardního cyklu (např. "pošli mi nabídky", "udělej sken").
- START: Spustit agenta.
- STOP: Zastavit agenta.
- ANALYZE_WITH_PROMPT: Uživatel se ptá na informace o trhu, chce shrnutí, nebo dává specifický pokyn pro analýzu dat (např. "jak vypadá trh?", "vypiš mi...", "jsou tam nějaké levné byty?", "co si myslíš o...").

Parametry: location (string), min_area (int), interval (int).

Příklad 1: "Hledej v Brně byty od 60m2" -> {"command": "UPDATE_CONFIG", "parameters": {"location": "Brno", "min_area": 60}}
Příklad 2: "Pošli mi teď nabídky z Prahy" -> {"command": "RUN_ONCE", "parameters": {"location": "Praha"}}
Příklad 3: "Vypiš mi krátké shrnutí jak vypadá trh" -> {"command": "ANALYZE_WITH_PROMPT", "parameters": {}}
Příklad 4: "Jsou v Ostravě nějaké byty do 15000?" -> {"command": "ANALYZE_WITH_PROMPT", "parameters": {"location": "Ostrava"}}

Vrať POUZE validní JSON bez dalšího textu."""

    try:
        response = requests.post(
            f"{AI_ANALYZER_URL}/analyze",
            json={
                "prompt": f"Uživatel říká: '{user_message}'",
                "context": system_prompt,
                "model": "gpt-4o",
                "temperature": 0.1
            },
            timeout=10
        )
        
        if response.status_code == 200:
            content = response.json().get("analysis", "")
            # Očištění od markdownu, pokud tam je
            content = content.replace("```json", "").replace("```", "").strip()
            import json
            return json.loads(content)
    except Exception as e:
        print(f"Chyba při interpretaci záměru: {e}")
        return None

def analyze_custom_query(listings, user_query, location):
    """Analýza nabídek na základě specifického dotazu uživatele"""
    # Připravit text nabídek
    listings_text = "\n".join([
        f"- {item.get('text', 'N/A')} [{item.get('url', '')}]" 
        for item in listings[:50]
    ])
    
    prompt = f"""Mám následující seznam nabídek pronájmu bytů v lokalitě {location}:

{listings_text}

Uživatel se ptá: "{user_query}"

Odpověz uživateli přímo na jeho otázku na základě poskytnutých dat. Buď stručný a věcný."""

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
            return f"Chyba AI služby: {response.status_code}"
    except Exception as e:
        return f"Chyba při volání AI služby: {e}"

def run_api_server():
    app.run(host='0.0.0.0', port=5005, debug=False, use_reloader=False)

def scrape_listings_with_params(location):
    """Volá scraper service pro získání nabídek (s parametrem)"""
    urls = [
        f"https://www.sreality.cz/hledani/pronajem/byty?region={location}",
        f"https://www.bezrealitky.cz/vypis/nabidka-pronajem/byt/{location}",
        f"https://reality.idnes.cz/s/pronajem/byty/{location}/",
        f"https://reality.bazos.cz/inzeraty/{location}-byt/"
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

def scrape_listings():
    return scrape_listings_with_params(config['LOCATION'])

def analyze_listings_with_params(listings, location, min_area):
    """Volá AI analyzer service pro analýzu nabídek (s parametry)"""
    if not listings:
        return "Žádné nabídky k analýze."
    
    # Připravit text nabídek
    listings_text = "\n".join([
        f"- {item.get('text', 'N/A')} [{item.get('url', '')}]" 
        for item in listings[:50]  # omezit na 50 nabídek
    ])
    
    prompt = f"""Vyber nejlepší nabídky pronájmu bytů v {location} z následujícího seznamu:

{listings_text}

Kritéria: 
- Plocha alespoň {min_area} m²
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

def analyze_listings(listings):
    return analyze_listings_with_params(listings, config['LOCATION'], config['MIN_AREA'])

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

def run_cycle(overrides=None):
    """Jeden cyklus vyhledávání"""
    # Použít overrides nebo globální config
    current_location = overrides.get("location", config["LOCATION"]) if overrides else config["LOCATION"]
    current_min_area = int(overrides.get("min_area", config["MIN_AREA"])) if overrides and "min_area" in overrides else config["MIN_AREA"]
    
    print("\n" + "="*50)
    print(f"Spouštím cyklus vyhledávání pro {current_location} (min {current_min_area} m²)...")
    print("="*50)
    
    # Krok 1: Scraping
    print("1. Scrapování nabídek...")
    # Dočasná úprava scrape_listings pro podporu parametrů
    listings = scrape_listings_with_params(current_location)
    
    if listings:
        print(f"✓ Nalezeno {len(listings)} nabídek.")
        
        # Krok 2: AI Analýza
        print("2. Analýza pomocí AI...")
        analysis = analyze_listings_with_params(listings, current_location, current_min_area)
        print(f"✓ Analýza dokončena.")
        
        # Krok 3: Odeslání e-mailu
        print("3. Odesílání e-mailu...")
        send_email(
            subject=f"Aktuální nabídky pronájmu v {current_location}",
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
