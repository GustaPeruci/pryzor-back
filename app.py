"""
PRYZOR - API Flask Mínima para Railway
=====================================
Versão mínima para resolver problemas de deploy
"""

from flask import Flask, jsonify
from flask_cors import CORS
import os
import sys

# Logging básico
print("🔧 Python version:", sys.version)
print("🔧 Working directory:", os.getcwd())

# Inicialização da aplicação Flask
app = Flask(__name__)
CORS(app)

print("✅ Flask app criado com sucesso")

@app.route('/')
def home():
    """Rota raiz da API"""
    return jsonify({
        "message": "PRYZOR API - Online",
        "version": "1.0-minimal",
        "status": "ok"
    })

@app.route('/health')
def health_check():
    """Health check para Railway"""
    return jsonify({
        "status": "healthy",
        "service": "pryzor-backend"
    })

@app.route('/api/test')
def test_endpoint():
    """Endpoint de teste"""
    return jsonify({
        "success": True,
        "message": "API funcionando corretamente",
        "environment_vars": {
            "PORT": os.environ.get('PORT', 'not_set'),
            "RAILWAY_ENVIRONMENT": os.environ.get('RAILWAY_ENVIRONMENT', 'not_set')
        }
    })

if __name__ == '__main__':
    try:
        # O Railway fornece a porta via variável PORT
        port = int(os.environ.get('PORT', 5000))
        print(f"🚀 Tentando iniciar na porta: {port}")
        print(f"🔧 PORT env var: {os.environ.get('PORT', 'não definida')}")
        
        # Debug das variáveis relacionadas a porta
        for key in sorted(os.environ.keys()):
            if 'PORT' in key.upper():
                print(f"   {key}={os.environ[key]}")
        
        app.run(host='0.0.0.0', port=port, debug=False)
    except Exception as e:
        print(f"❌ Erro ao iniciar aplicação: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
