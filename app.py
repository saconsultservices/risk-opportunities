from flask import Flask, jsonify
import csv
from datetime import datetime
import os

app = Flask(__name__)

# Load data from CSV (auto-reload when file changes)
def load_opportunities():
    data = []
    csv_path = "opportunities.csv"
    if os.path.exists(csv_path):
        with open(csv_path, newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader, None)  # skip header
            for row in reader:
                if len(row) >= 5:
                    data.append({
                        "company": row[0],
                        "province": row[1],
                        "sector": row[2],
                        "url": row[3],
                        "deadline": row[4],
                        "budget": row[5] if len(row) > 5 else ""
                    })
    return data

@app.route('/data')
def get_data():
    return jsonify(load_opportunities())

@app.route('/')
def home():
    return "Risk Opportunities API is running! Use /data"

if __name__ == '__main__':
    app.run(debug=True)
