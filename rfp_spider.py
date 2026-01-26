import feedparser
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, Date, DateTime
import os
import datetime
import re  # For basic text extraction/cleaning

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

# Main scraper logic using RSS feeds
def scrape_feeds():
    feeds = [
        'https://www.bcbid.gov.bc.ca/rss',  # BC Bid RSS
        'https://vendor.purchasingconnection.ca/rss',  # Alberta Purchasing Connection RSS
        'https://www.canadabuys.gc.ca/rss'  # CanadaBuys (federal, filter for BC/AB)
        # Add more feeds as discovered, e.g., MERX or other aggregators
    ]
    items = []
    for url in feeds:
        parsed = feedparser.parse(url)
        province = 'BC' if 'bc' in url else 'AB' if 'alberta' in url else 'Federal'  # Adjust based on feed
        for entry in parsed.entries:
            # Filter for relevant keywords (risk, compliance, etc.)
            if any(keyword in entry.title.lower() or keyword in entry.description.lower() for keyword in ['risk', 'compliance', 'audit', 'cybersecurity']):
                item = {
                    'company_name': entry.get('author', entry.get('title', '')).strip(),
                    'province': province,
                    'sector': entry.get('category', '').strip() or 'Unknown',  # Use category if available
                    'domain': entry.link,
                    'deadline': extract_deadline(entry.description or entry.title),
                    'budget': extract_budget(entry.description or '')
                }
                items.append(item)
    return items

# Insert items to DB
class DbPipeline:
    def __init__(self):
        self.engine = create_engine(DATABASE_URL)

    def process_item(self, item):
        with self.engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO opportunities (company_name, province, sector, domain, deadline, budget)
                VALUES (:company_name, :province, :sector, :domain, :deadline::date, :budget)
            """), item)

# Run the scraper
if __name__ == '__main__':
    init_db(engine)  # Create table if needed
    with engine.connect() as conn:
        conn.execute(text("TRUNCATE TABLE opportunities"))  # Clear old data for fresh scrape
    items = scrape_feeds()
    pipeline = DbPipeline()
    for item in items:
        if item['deadline']:  # Skip if no deadline extracted
            pipeline.process_item(item)
    print(f"Inserted {len(items)} opportunities")
