import feedparser
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, Date, DateTime
import os
import datetime
import re  # For basic text extraction/cleaning
import requests  # For API calls

db_url_raw = os.environ.get('DATABASE_URL')
if db_url_raw is None:
    raise ValueError("DATABASE_URL environment variable is not set. Check Render dashboard or yaml configuration.")
DATABASE_URL = db_url_raw.replace("postgresql://", "postgresql+psycopg://")  # Handle Render format
engine = create_engine(DATABASE_URL)

# Define table (same as app.py)
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

# Create table if not exists
def init_db(engine):
    inspector = inspect(engine)
    if not inspector.has_table('opportunities'):
        Base.metadata.create_all(engine)
        print("Created opportunities table")

# Function to extract deadline from text (basic regex; improve as needed)
def extract_deadline(text):
    match = re.search(r'\b(\d{4}-\d{2}-\d{2})\b', text)  # YYYY-MM-DD pattern
    return match.group(1) if match else ''

# Function to extract budget from text (e.g., $XXXk patterns)
def extract_budget(text):
    match = re.search(r'\$(\d+k?)', text)  # Simple $XXXk pattern
    return match.group(0) if match else ''

# Fetch from TendersOnTime API (placeholder - requires API key/subscription; update with your key)
def fetch_tendersontime(api_key, date='today'):
    url = f"https://www.tendersontime.com/tenders/api?date={date}"  # From API docs; adjust params
    headers = {'Authorization': f'Bearer {api_key}'}  # Or as per docs
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        items = []
        for tender in data.get('tenders', []):
            item = {
                'company_name': tender.get('authority', ''),
                'province': tender.get('province', ''),  # Adjust based on API response
                'sector': tender.get('sector', ''),
                'domain': tender.get('link', ''),
                'deadline': tender.get('deadline', ''),
                'budget': tender.get('budget', '')
            }
            items.append(item)
        return items
    else:
        print(f"TendersOnTime API error: {response.status_code}")
        return []

# Fetch from RFPMart RSS feed
def fetch_rfpmart():
    feed_url = 'http://feeds.feedburner.com/RFPMart'  # From results
    parsed = feedparser.parse(feed_url)
    items = []
    for entry in parsed.entries:
        if any(keyword in entry.title.lower() or keyword in entry.description.lower() for keyword in ['risk', 'compliance', 'audit', 'cybersecurity']):
            item = {
                'company_name': entry.get('author', entry.get('title', '')).strip(),
                'province': entry.get('province', ''),  # May need extraction from description
                'sector': entry.get('category', '').strip() or 'Unknown',
                'domain': entry.link,
                'deadline': extract_deadline(entry.description or entry.title),
                'budget': extract_budget(entry.description or '')
            }
            items.append(item)
    return items

# Fetch from RFPDB (no RSS/API; basic scrape placeholder - update selectors)
def fetch_rfpdb():
    url = 'https://www.rfpdb.com/view/all'  # Listings page; may require login
    response = requests.get(url)
    if response.status_code == 200:
        # Use BeautifulSoup or lxml for parsing (add to requirements.txt: beautifulsoup4==4.12.3, lxml==5.3.0)
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.text, 'lxml')
        items = []
        for rfp in soup.select('div.rfp-item'):  # Adjust selector based on site inspection
            item = {
                'company_name': rfp.select_one('.organization').text.strip() if rfp.select_one('.organization') else '',
                'province': 'Unknown',  # Extract from text if available
                'sector': rfp.select_one('.category').text.strip() if rfp.select_one('.category') else '',
                'domain': rfp.select_one('a').get('href', '') if rfp.select_one('a') else '',
                'deadline': extract_deadline(rfp.text),
                'budget': extract_budget(rfp.text)
            }
            items.append(item)
        return items
    else:
        print(f"RFPDB fetch error: {response.status_code}")
        return []

# Fetch from FindRFP (no RSS/API; basic scrape placeholder - update selectors)
def fetch_findrfp():
    url = 'https://www.findrfp.com/service/search.aspx'  # Search page; may need params or login
    response = requests.get(url, params={'keywords': 'risk consulting'})  # Add search params
    if response.status_code == 200:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.text, 'lxml')
        items = []
        for rfp in soup.select('div.rfp-listing'):  # Adjust selector
            item = {
                'company_name': rfp.select_one('.buyer-org').text.strip() if rfp.select_one('.buyer-org') else '',
                'province': 'Unknown',  # Extract if available
                'sector': rfp.select_one('.sector').text.strip() if rfp.select_one('.sector') else '',
                'domain': rfp.select_one('a.details').get('href', '') if rfp.select_one('a.details') else '',
                'deadline': extract_deadline(rfp.text),
                'budget': extract_budget(rfp.text)
            }
            items.append(item)
        return items
    else:
        print(f"FindRFP fetch error: {response.status_code}")
        return []

# Main scraper logic
def scrape_all():
    items = []
    # TendersOnTime API (replace with your API key)
    api_key = os.environ.get('TENDERSONTIME_API_KEY', '')  # Add as GitHub secret
    if api_key:
        items += fetch_tendersontime(api_key)
    else:
        print("TendersOnTime API key not set - skipping")

    # RFPMart RSS
    items += fetch_rfpmart()

    # RFPDB scrape
    items += fetch_rfpdb()

    # FindRFP scrape
    items += fetch_findrfp()

    # Add previous feeds for completeness
    feeds = [
        'https://www.bcbid.gov.bc.ca/rss',
        'https://vendor.purchasingconnection.ca/rss',
        'https://www.canadabuys.gc.ca/rss'
    ]
    for url in feeds:
        parsed = feedparser.parse(url)
        province = 'BC' if 'bc' in url else 'AB' if 'alberta' in url else 'Federal'
        for entry in parsed.entries:
            if any(keyword in entry.title.lower() or keyword in entry.description.lower() for keyword in ['risk', 'compliance', 'audit', 'cybersecurity']):
                item = {
                    'company_name': entry.get('author', entry.get('title', '')).strip(),
                    'province': province,
                    'sector': entry.get('category', '').strip() or 'Unknown',
                    'domain': entry.link,
                    'deadline': extract_deadline(entry.description or entry.title),
                    'budget': extract_budget(entry.description or '')
                }
                items.append(item)
    return items

# Run the scraper
if __name__ == '__main__':
    init_db(engine)  # Create table if needed
    with engine.connect() as conn:
        conn.execute(text("TRUNCATE TABLE opportunities"))  # Clear old data for fresh scrape
    items = scrape_all()
    pipeline = DbPipeline()
    inserted_count = 0
    for item in items:
        if item['deadline']:  # Skip if no deadline
            pipeline.process_item(item)
            inserted_count += 1
    print(f"Inserted {inserted_count} opportunities")
