# app.py
from flask import Flask, jsonify
from flask_cors import CORS
import csv
import os

app = Flask(__name__)
CORS(app)                     # ← allows *any* origin (good for dev)

def load_opportunities():
    data = []
    csv_path = "opportunities.csv"
    if os.path.exists(csv_path):
        try:
            with open(csv_path, newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    data.append({
                        "company": row.get("company_name", ""),
                        "province": row.get("province", ""),
                        "sector": row.get("sector", ""),
                        "url": row.get("domain", ""),
                        "deadline": row.get("deadline", ""),
                        "budget": row.get("budget", "")
                    })
        except Exception as e:
            print(f"CSV error: {e}")
    else:
        print("CSV not found – returning empty list")
    return data

@app.route('/data')
def get_data():
    return jsonify(load_opportunities())

@app.route('/')
def home():
    return "Risk Opportunities API – use /data for JSON"

# Render requires binding to $PORT
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
