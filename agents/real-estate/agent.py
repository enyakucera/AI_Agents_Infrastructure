import os
import time
import requests

# Načtení konfigurace z prostředí
LOCATION = os.getenv("LOCATION")
MIN_AREA = int(os.getenv("MIN_AREA", 50))
INTERVAL = int(os.getenv("INTERVAL", 10800))  # v sekundách (3 hodiny)
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")
USER_WHATSAPP_NUMBER = os.getenv("USER_WHATSAPP_NUMBER")

# URL mikroslužeb (v Docker síti)
SCRAPER_URL = os.getenv("SCRAPER_URL", "http://scraper:5001")
AI_ANALYZER_URL = os.getenv("AI_ANALYZER_URL", "http://ai-analyzer:5002")
EMAIL_URL = os.getenv("EMAIL_URL", "http://email:5003")
WHATSAPP_URL = os.getenv("WHATSAPP_URL", "http://whatsapp:5004")

def scrape_listings():
    """Volá scraper service pro získání nabídek"""
    urls = [
        "https://www.sreality.cz/hledani/pronajem/byty?region=Hostinn%C3%A9",
        "https://www.bezrealitky.cz/vypis/nabidka-pronajem/byt/kralovehradecky-kraj/okres-trutnov/hostinne",
        "https://reality.idnes.cz/s/pronajem/byty/hostinne-okres-trutnov/",
        "https://reality.bazos.cz/inzeraty/hostinne-byt/"
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
    
    prompt = f"""Vyber nejlepší nabídky pronájmu bytů v {LOCATION} z následujícího seznamu:

{listings_text}

Kritéria: 
- Plocha alespoň {MIN_AREA} m²
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

def run_agent():
    """Hlavní smyčka agenta - orchestrace mikroslužeb"""
    print(f"Real Estate Agent spuštěn pro lokaci: {LOCATION}")
    print(f"Minimální plocha: {MIN_AREA} m²")
    print(f"Kontrolní interval: {INTERVAL} sekund")
    
    while True:
        print("\n" + "="*50)
        print("Spouštím nový cyklus vyhledávání...")
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
                subject=f"Aktuální nabídky pronájmu v {LOCATION}",
                body=analysis
            )
            
            # Krok 4: Odeslání WhatsApp zprávy
            print("4. Odesílání WhatsApp zprávy...")
            send_whatsapp_message(analysis)
            
            print("✓ Cyklus dokončen.")
        else:
            print("✗ Žádné nabídky nenalezeny.")
        
        # Spánek podle intervalu
        print(f"\nČekám {INTERVAL} sekund do dalšího cyklu...")
        time.sleep(INTERVAL)

if __name__ == "__main__":
    run_agent()
