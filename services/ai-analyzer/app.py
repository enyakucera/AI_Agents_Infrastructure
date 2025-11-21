from flask import Flask, request, jsonify
from openai import OpenAI
import os

app = Flask(__name__)

# Inicializace GitHub Models klienta
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
client = OpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=GITHUB_TOKEN
)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "service": "ai-analyzer"}), 200

@app.route('/analyze', methods=['POST'])
def analyze():
    """
    Očekávaný JSON:
    {
        "prompt": "Analyzuj následující nabídky...",
        "context": "dodatečný kontext",
        "model": "gpt-4o",  # volitelné, default gpt-4o
        "temperature": 0.2,  # volitelné
        "max_tokens": 1000   # volitelné
    }
    """
    try:
        data = request.get_json()
        prompt = data.get('prompt')
        context = data.get('context', '')
        model = data.get('model', 'gpt-4o')
        temperature = data.get('temperature', 0.2)
        max_tokens = data.get('max_tokens', 1000)
        
        if not prompt:
            return jsonify({"error": "No prompt provided"}), 400
        
        # Sestavení zprávy
        full_prompt = f"{prompt}\n\n{context}" if context else prompt
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Jsi AI asistent, který pomáhá s analýzou dat a poskytováním informací."},
                {"role": "user", "content": full_prompt}
            ],
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        analysis = response.choices[0].message.content
        
        return jsonify({
            "success": True,
            "analysis": analysis,
            "model": model,
            "tokens_used": response.usage.total_tokens if hasattr(response, 'usage') else None
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=False)
