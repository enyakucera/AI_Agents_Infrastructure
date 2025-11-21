# AI Agents Infrastructure

Multi-agentní systém s mikroslužbami pro automatizaci úloh pomocí AI.

## 🏗️ Architektura

Projekt je rozdělen na **sdílené služby** (infrastruktura) a **specializované agenty**.

```
AI_Agents_Infrastructure/
├── docker-compose.infrastructure.yml  # Sdílené služby
├── services/                          # Mikroslužby (REST API)
│   ├── scraper/                       # Web scraping
│   ├── ai-analyzer/                   # LLM analýza (GitHub Models)
│   ├── email/                         # Odesílání e-mailů
│   └── whatsapp/                      # WhatsApp zprávy (Twilio)
└── agents/                            # Specializované agenty
    └── real-estate/                   # Agent pro nemovitosti
```

### 📦 Sdílené služby (Mikroslužby)

Každá služba běží jako samostatný kontejner s REST API:

| Služba | Port | Popis |
|--------|------|-------|
| **scraper** | 5001 | Web scraping z více URL s filtrováním |
| **ai-analyzer** | 5002 | AI analýza pomocí GitHub Models (GPT-4o) |
| **email** | 5003 | Odesílání e-mailů přes SMTP |
| **whatsapp** | 5004 | Odesílání WhatsApp zpráv přes Twilio |

### 🤖 Agenti

Specializované agenty orchestrují mikroslužby pro konkrétní účel:

- **Real Estate Agent** - Vyhledává a analyzuje nabídky nemovitostí

## 🚀 Rychlý start

### 1️⃣ Příprava prostředí

Vytvořte `.env` soubor v root složce s následující konfigurací:

```bash
# GitHub Models API
GITHUB_TOKEN=your_github_token

# Email konfigurace
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_SENDER=your-email@gmail.com
EMAIL_PASSWORD=your-app-password

# Twilio WhatsApp konfigurace
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_WHATSAPP_NUMBER=+14155238886
```

### 2️⃣ Spuštění infrastruktury

Nejprve spusťte sdílené služby:

```bash
docker-compose -f docker-compose.infrastructure.yml up -d
```

Ověření zdraví služeb:
```bash
curl http://localhost:5001/health  # Scraper
curl http://localhost:5002/health  # AI Analyzer
curl http://localhost:5003/health  # Email
curl http://localhost:5004/health  # WhatsApp
```

### 3️⃣ Spuštění agenta

Přejděte do složky agenta a vytvořte `.env` soubor:

```bash
cd agents/real-estate
cp .env.example .env
# Upravte .env podle vašich potřeb
```

Spusťte agenta:

```bash
docker-compose up -d
```

### 4️⃣ Monitorování

Sledování logů infrastruktury:
```bash
docker-compose -f docker-compose.infrastructure.yml logs -f
```

Sledování logů agenta:
```bash
cd agents/real-estate
docker-compose logs -f
```

## 📋 API dokumentace služeb

### Web Scraper Service (port 5001)

**POST /scrape**
```json
{
  "urls": ["https://example.com", "..."],
  "keywords": ["byt", "pronájem"]
}
```

**Odpověď:**
```json
{
  "success": true,
  "count": 42,
  "listings": [
    {
      "text": "Pronájem bytu 2+kk...",
      "url": "https://...",
      "source": "https://example.com"
    }
  ]
}
```

### AI Analyzer Service (port 5002)

**POST /analyze**
```json
{
  "prompt": "Analyzuj následující nabídky...",
  "context": "dodatečný kontext",
  "model": "gpt-4o",
  "temperature": 0.2,
  "max_tokens": 1000
}
```

**Odpověď:**
```json
{
  "success": true,
  "analysis": "Nejlepší nabídky jsou...",
  "model": "gpt-4o",
  "tokens_used": 450
}
```

### Email Service (port 5003)

**POST /send**
```json
{
  "to": "recipient@example.com",
  "subject": "Předmět zprávy",
  "body": "Text zprávy",
  "html": false
}
```

### WhatsApp Service (port 5004)

**POST /send**
```json
{
  "to": "+420123456789",
  "message": "Text zprávy"
}
```

## 🔧 Vytvoření nového agenta

1. Vytvořte novou složku v `agents/`:
```bash
mkdir -p agents/my-agent
```

2. Vytvořte soubory:
   - `agent.py` - logika agenta (orchestrace služeb)
   - `Dockerfile` - definice kontejneru
   - `docker-compose.yml` - konfigurace
   - `.env.example` - vzorová konfigurace

3. Příklad `docker-compose.yml`:
```yaml
version: '3.8'

networks:
  ai-agents-network:
    external: true

services:
  my-agent:
    build: .
    container_name: agent-my-agent
    restart: unless-stopped
    environment:
      - PYTHONUNBUFFERED=1
      # ... vaše proměnné
    networks:
      - ai-agents-network
```

4. V kódu agenta volejte služby přes HTTP:
```python
import requests

# Volání scraper služby
response = requests.post(
    "http://scraper:5001/scrape",
    json={"urls": [...], "keywords": [...]}
)

# Volání AI analyzer
response = requests.post(
    "http://ai-analyzer:5002/analyze",
    json={"prompt": "..."}
)
```

## 🛠️ Správa systému

### Zastavení všeho

```bash
# Zastavit infrastrukturu
docker-compose -f docker-compose.infrastructure.yml down

# Zastavit konkrétního agenta
cd agents/real-estate
docker-compose down
```

### Restart služby

```bash
# Restart konkrétní služby
docker-compose -f docker-compose.infrastructure.yml restart scraper

# Rebuild po změně kódu
docker-compose -f docker-compose.infrastructure.yml up -d --build scraper
```

### Čištění

```bash
# Odstranit všechny kontejnery a images
docker-compose -f docker-compose.infrastructure.yml down --rmi all
cd agents/real-estate
docker-compose down --rmi all
```

## 🌟 Výhody architektury

✅ **Znovupoužitelnost** - Služby jednou, použití mnohokrát  
✅ **Škálovatelnost** - Každá služba škáluje nezávisle  
✅ **Izolace chyb** - Pád jedné služby neovlivní ostatní  
✅ **Snadná údržba** - Změny jen v jedné službě  
✅ **Flexibilita** - Agenti kombinují služby libovolně  
✅ **Nezávislé nasazení** - Agenti se přidávají/odebírají samostatně  

## 📝 Poznámky

- Všechny kontejnery běží v síti `ai-agents-network`
- Služby komunikují pomocí názvů kontejnerů (DNS)
- Health checks zajišťují spolehlivost
- Logování pomocí `docker-compose logs`

## 🆘 Troubleshooting

**Síť neexistuje:**
```bash
docker network create ai-agents-network
```

**Port konflikty:**
Změňte port mapping v `docker-compose.infrastructure.yml`:
```yaml
ports:
  - "5101:5001"  # Změna z 5001 na 5101
```

**Agent nemůže kontaktovat služby:**
Ujistěte se, že infrastruktura běží:
```bash
docker-compose -f docker-compose.infrastructure.yml ps
```

## Získání tokenů

### GitHub Token
1. Jděte na https://github.com/settings/tokens
2. Vytvořte "Classic token"
3. Zaškrtněte `read:user` scope

### Gmail App Password
1. Zapněte 2FA na Google účtu
2. Jděte na https://myaccount.google.com/apppasswords
3. Vytvořte nový App Password

### Twilio WhatsApp
1. Registrujte se na https://www.twilio.com/
2. Aktivujte WhatsApp Sandbox
3. Zkopírujte Account SID, Auth Token a WhatsApp číslo
