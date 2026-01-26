from flask import Flask, jsonify, Response
from flask_cors import CORS
from flask_caching import Cache
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, Date, DateTime
import os
import datetime

app = Flask(__name__)

CORS(app, resources={r"/data": {"origins": ["https://risk-opportunities-frontend.onrender.com", "http://localhost"]}})

config = {
    'CACHE_TYPE': 'RedisCache',
    'CACHE_REDIS_URL': os.environ.get('REDIS_URL')
}
cache = Cache(app, config=config)

db_url_raw = os.environ.get('DATABASE_URL')
if db_url_raw is None:
    raise ValueError("DATABASE_URL environment variable is not set. Check Render dashboard or yaml configuration.")
print(f"Raw DB URL (redacted): {db_url_raw[:20]}...")  # Debug log (keep if you added it)
DATABASE_URL = db_url_raw.replace("postgresql://", "postgresql+psycopg://")  # Updated replace to handle Render's format
print(f"Processed DB URL (redacted): {DATABASE_URL[:30]}...")  # Debug log
engine = create_engine(DATABASE_URL)


Base = declarative_base()

class Opportunity(Base):
    __tablename__ = 'opportunities'
    id = Column(Integer, primary_key=True)
    company_name = Column(String(255))
    province = Column(String(2))
    sector = Column(String(100))
    domain = Column(String)
    deadline = Column(Date)
    budget = Column(String(50))
    last_updated = Column(DateTime, default=datetime.datetime.utcnow)

inspector = inspect(engine)
if not inspector.has_table('opportunities'):
    Base.metadata.create_all(engine)
    print("Created opportunities table")

@app.route('/data')
@cache.cached(timeout=300, query_string=True)
def get_data():
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT company_name, province, sector, domain, deadline, budget FROM opportunities ORDER BY deadline ASC"))
            data = [
                {
                    "company": row[0],
                    "province": row[1],
                    "sector": row[2],
                    "url": row[3],
                    "deadline": row[4].isoformat() if row[4] else "",
                    "budget": row[5]
                } for row in result
            ]
        if not data:
            return jsonify({"error": "No data available"}), 404
        return jsonify(data)
    except Exception as e:
        print(f"DB error: {e}")
        return jsonify({"error": "Server error"}), 500

@app.route('/')
def home():
    with engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM opportunities")).scalar()
        last = conn.execute(text("SELECT MAX(last_updated) FROM opportunities")).scalar()
    return f"API live – {count} opportunities, last updated {last or 'N/A'}"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)




