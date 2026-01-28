import feedparser
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, Date, DateTime
import os
import datetime
import re
import requests
from bs4 import BeautifulSoup
from dateutil.parser import parse as date_parse  # Add to requirements.txt: python-dateutil==2.9.0

db_url_raw = os.environ.get('DATABASE_URL')
if db_url_raw is None:
    raise ValueError("DATABASE_URL environment variable is not set.")
DATABASE_URL = db_url_raw.replace("postgresql://", "postgresql+psycopg://")
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

def init_db(engine):
    inspector = inspect(engine)
    if not inspector.has_table('opportunities'):
        Base.metadata.create_all(engine)
        print("Created opportunities table")

def extract_deadline(text):
    # Improved: Use dateutil to parse natural language dates
    try:
        parsed_date = date_parse(text, fuzzy=True)
        return parsed_date.strftime('%Y-%m-%d')
    except:
        return ''

def extract_budget(text):
    match = re.search(r'\$(\d+k?)', text)
    return match.group(0) if match else ''

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def fetch_tendersontime(api_key, date='today'):
    try:
        url = f"https://www.tendersontime.com/tenders/api?date={date}"
        headers['Authorization'] = f'Bearer {api_key}'
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        items = []
        for tender in data.get('tenders', []):
            item = {
                'company_name': tender.get('authority', ''),
                'province': tender.get('province', ''),
                'sector': tender.get('sector', ''),
                'domain': tender.get('link', ''),
                'deadline': tender.get('deadline', ''),
                'budget': tender.get('budget', '')
            }
            items.append(item)
        print(f"Fetched {len(items)} from TendersOnTime")
        return items
    except Exception as e:
        print(f"TendersOnTime error: {str(e)}")
        return []

def fetch_rfpmart():
    try:
        url = 'http://feeds.feedburner.com/RFPMart'
        parsed = feedparser.parse(url)
        items = []
        for entry in parsed.entries:
            if any(keyword in entry.title.lower() or keyword in entry.description.lower() for keyword in ['risk', 'compliance', 'audit', 'cybersecurity']):
                item = {
                    'company_name': entry.get('author', entry.get('title', '')).strip(),
                    'province': 'Unknown',
                    'sector': entry.get('category', '').strip() or 'Unknown',
                    'domain': entry.link,
                    'deadline': extract_deadline(entry.description or entry.title or entry.get('published', '')),
                    'budget': extract_budget(entry.description or '')
                }
                items.append(item)
        print(f"Fetched {len(items)} from RFPMart")
        return items
    except Exception as e:
        print(f"RFPMart error: {str(e)}")
        return []

def fetch_rfpdb():
    try:
        url = 'https://www.rfpdb.com/view/all'
        response = requests.get(url, headers=headers, verify=False, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'lxml')
        items = []
        for rfp in soup.select('ul.rfp-list > li'):  # Updated selector based on tool summary (numbered list items)
            text = rfp.text.strip()
            title = rfp.find('a').text.strip() if rfp.find('a') else ''
            link = rfp.find('a').get('href', '') if rfp.find('a') else ''
            item = {
                'company_name': title.split(' - ')[0] if ' - ' in title else title,  # Extract from title
                'province': 'Unknown',
                'sector': re.search(r'\*\*(\w+)\*\*', text).group(1) if re.search(r'\*\*(\w+)\*\*', text) else 'Unknown',  # From **Category**
                'domain': link,
                'deadline': extract_deadline(text),
                'budget': extract_budget(text)
            }
            if item['domain']:
                items.append(item)
        print(f"Fetched {len(items)} from RFPDB")
        return items
    except Exception as e:
        print(f"RFPDB error: {str(e)}")
        return []

# Removed fetch_findrfp() as tool shows no public listings without login

class DbPipeline:
    def __init__(self):
        self.engine = create_engine(DATABASE_URL)

    def process_item(self, item):
        with self.engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO opportunities (company_name, province, sector, domain, deadline, budget)
                VALUES (:company_name, :province, :sector, :domain, :deadline::date, :budget)
            """), item)

def scrape_all():
    items = []
    api_key = os.environ.get('TENDERSONTIME_API_KEY', '')
    if api_key:
        items += fetch_tendersontime(api_key)
    else:
        print("TendersOnTime API key not set - skipping; sign up at tendersontime.com for free key")
    items += fetch_rfpmart()
    items += fetch_rfpdb()
    return items

if __name__ == '__main__':
    init_db(engine)
    with engine.connect() as conn:
        conn.execute(text("TRUNCATE TABLE opportunities"))
    items = scrape_all()
    inserted_count = 0
    pipeline = DbPipeline()
    for item in items:
        if item['deadline']:
            pipeline.process_item(item)
            inserted_count += 1
    print(f"Inserted {inserted_count} opportunities")
