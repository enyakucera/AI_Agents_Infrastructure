from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "service": "scraper"}), 200

@app.route('/scrape', methods=['POST'])
def scrape():
    """
    Očekávaný JSON:
    {
        "urls": ["https://example.com", ...],
        "keywords": ["byt", "pronájem"]  # volitelné
    }
    """
    try:
        data = request.get_json()
        urls = data.get('urls', [])
        keywords = data.get('keywords', [])
        
        if not urls:
            return jsonify({"error": "No URLs provided"}), 400
        
        all_listings = []
        
        for url in urls:
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, "html.parser")
                    
                    # Extraktor odkazů s textem
                    for a in soup.find_all("a", href=True):
                        text = a.get_text(strip=True)
                        href = a["href"]
                        
                        # Filtrování podle klíčových slov (pokud jsou zadána)
                        if keywords:
                            if text and any(keyword.lower() in text.lower() for keyword in keywords):
                                all_listings.append({
                                    "text": text,
                                    "url": href,
                                    "source": url
                                })
                        else:
                            if text:
                                all_listings.append({
                                    "text": text,
                                    "url": href,
                                    "source": url
                                })
            except Exception as e:
                print(f"Error scraping {url}: {e}")
                all_listings.append({
                    "error": str(e),
                    "source": url
                })
        
        return jsonify({
            "success": True,
            "count": len(all_listings),
            "listings": all_listings
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=False)
