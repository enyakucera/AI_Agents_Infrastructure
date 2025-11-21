import os
import time
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
from twilio.rest import Client
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Načtení konfigurace z prostředí
LOCATION=os.getenv("LOCATION")
MIN_AREA=int(os.getenv("MIN_AREA", 50))
INTERVAL=int(os.getenv("INTERVAL", 10800))  # v sekundách (3 hodiny)
SMTP_SERVER=os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT=int(os.getenv("SMTP_PORT", 587))
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")
USER_WHATSAPP_NUMBER = os.getenv("USER_WHATSAPP_NUMBER")

# Inicializace GitHub Models klienta
client = OpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=GITHUB_TOKEN
)

# Funkce pro scraping z více webů
def scrape_listings():
    listings = []
    urls = [
        "https://www.sreality.cz/hledani/pronajem/byty?region=Hostinn%C3%A9",
        "https://www.bezrealitky.cz/vypis/nabidka-pronajem/byt/kralovehradecky-kraj/okres-trutnov/hostinne",
        "https://reality.idnes.cz/s/pronajem/byty/hostinne-okres-trutnov/",
        "https://reality.bazos.cz/inzeraty/hostinne-byt/"
    ]
    for url in urls:
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                # Jednoduchý extraktor titulků a odkazů
                for a in soup.find_all("a", href=True):
                    text = a.get_text(strip=True)
                    href = a["href"]
                    if text and "byt" in text.lower():
                        listings.append(f"{text} - {href}")
        except Exception as e:
            print(f"Chyba při scrapování {url}: {e}")
    return listings

# Funkce pro analýzu nabídek pomocí LLM (GitHub Models)
def analyze_listings(listings):
    try:
        prompt_text = f"""Vyber nejlepší nabídky pronájmu bytů v {LOCATION} z následujícího seznamu:
{chr(10).join(listings)}
Kritéria: plocha alespoň {MIN_AREA} m², vhodné pro dlouhodobý pronájem. Vrať stručný seznam nejlepších nabídek."""
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Jsi AI asistent, který pomáhá s vyhledáváním nemovitostí."},
                {"role": "user", "content": prompt_text}
            ],
            temperature=0.2,
            max_tokens=1000
        )
        
        analysis = response.choices[0].message.content
        return analysis
    except Exception as e:
        error_msg = f"Chyba při analýze nabídek pomocí LLM: {e}\n\nZpracovávám bez AI analýzy..."
        print(error_msg)
        # Vrátit alespoň seznam nalezených nabídek
        return f"Nalezeno {len(listings)} nabídek:\n\n" + "\n".join(listings[:10])

# Funkce pro odeslání e-mailu
def send_email(subject, body):
    msg = MIMEMultipart()
    msg["From"] = EMAIL_SENDER
    msg["To"] = EMAIL_RECEIVER
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, msg.as_string())
        server.quit()
        print("E-mail odeslán.")
    except Exception as e:
        print(f"Chyba při odesílání e-mailu: {e}")

# Funkce pro odeslání zprávy na WhatsApp přes Twilio
def send_whatsapp_message(body):
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        message = client.messages.create(
            from_=f"whatsapp:{TWILIO_WHATSAPP_NUMBER}",
            body=body,
            to=f"whatsapp:{USER_WHATSAPP_NUMBER}"
        )
        print(f"WhatsApp zpráva odeslána: {message.sid}")
    except Exception as e:
        print(f"Chyba při odesílání WhatsApp zprávy: {e}")

# Hlavní smyčka agenta
def run_agent():
    while True:
        print("Spouštím scraping...")
        listings = scrape_listings()
        if listings:
            print(f"Nalezeno {len(listings)} nabídek.")
            analysis = analyze_listings(listings)
            # Odeslat e-mail
            send_email(f"Aktuální nabídky pronájmu v {LOCATION}", analysis)
            # Odeslat WhatsApp zprávu
            send_whatsapp_message(analysis)
        else:
            print("Žádné nabídky nenalezeny.")
        # Spánek podle intervalu z .env
        time.sleep(INTERVAL)

if __name__ == "__main__":
    run_agent()
