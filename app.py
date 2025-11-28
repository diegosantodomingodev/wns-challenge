import json
import os
import requests
from datetime import datetime, timedelta
from flask import Flask, jsonify, send_file, request

app = Flask(__name__)
DATA_FILE = 'data_warehouse.json'

# --- CONFIGURACIÓN ---
# API pública para obtener cotización USD vs otras monedas por fecha
# Formato: https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@{date}/v1/currencies/usd.json
CURRENCY_API_URL = "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@{date}/v1/currencies/usd.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"prices": {}, "recipes": []}

def get_usd_rate(date_str):
    """
    Obtiene la cotización del USD para una fecha dada (YYYY-MM-DD).
    Retorna cuántos ARS vale 1 USD.
    """
    try:
        url = CURRENCY_API_URL.format(date=date_str)
        print(f"Consultando cotización: {url}")
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            # La API devuelve: { "date": "...", "usd": { "ars": 950.5, ... } }
            # Necesitamos el valor de ARS (cuántos pesos es 1 dólar)
            ars_rate = data.get('usd', {}).get('ars')
            return ars_rate
        else:
            print(f"Error API Divisas: {response.status_code}")
            return None
    except Exception as e:
        print(f"Excepción API Divisas: {e}")
        return None

@app.route('/')
def index():
    return send_file('index.html')

@app.route('/api/calculate')
def calculate():
    # Obtener fecha de los parámetros (query param), default hoy
    target_date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    
    # Validar fecha (simple)
    try:
        datetime.strptime(target_date, '%Y-%m-%d')
    except ValueError:
        return jsonify({"error": "Formato de fecha inválido. Use YYYY-MM-DD"}), 400

    # Obtener cotización
    usd_rate = get_usd_rate(target_date)
    
    data = load_data()
    prices = data.get('prices', {})
    recipes = data.get('recipes', [])
    
    results = []
    
    for r in recipes:
        total_ars = 0
        missing = False
        details = []
        
        for ing in r['ingredients']:
            key = ing['id']
            price_ars_kg = prices.get(key)
            cost_ars = 0
            
            if price_ars_kg:
                # Costo ARS = (gramos / 1000) * precio_kilo
                cost_ars = (ing['qty_g'] / 1000) * price_ars_kg
                total_ars += cost_ars
            else:
                missing = True
                
            details.append({
                "name": ing['name'],
                "qty_g": ing['qty_g'],
                "cost_ars": cost_ars,
                "found": bool(price_ars_kg)
            })
            
        # Calcular costo en USD si tenemos la tasa
        total_usd = total_ars / usd_rate if usd_rate else None
            
        results.append({
            "name": r['name'],
            "total_cost_ars": total_ars,
            "total_cost_usd": total_usd,
            "has_missing": missing,
            "ingredients": details
        })
    
    return jsonify({
        "date": target_date,
        "usd_rate": usd_rate,
        "recipes": results
    })

if __name__ == '__main__':
    print("Servidor corriendo en http://127.0.0.1:5000")
    app.run(debug=True, port=5000)
