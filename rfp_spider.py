import scrapy
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, Date, DateTime
import os
import datetime
 
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

class RfpSpider(scrapy.Spider):
    name = 'rfp_spider'
    start_urls = ['https://example-rfp-site.com/bc-procurement', 'https://example-rfp-site.com/ab-procurement']  # Update with real URLs, e.g., https://www.bcbid.gov.bc.ca/ or https://www.albertapurchasingconnection.com/

    def parse(self, response):
        # Custom parsing logic: Extract RFPs from the page (use CSS/XPath selectors based on site structure)
        # Example placeholder - replace with actual selectors
        for rfp in response.css('div.rfp-item'):
            yield {
                'company_name': rfp.css('.company::text').get(default='').strip(),
                'province': rfp.css('.province::text').get(default='').strip(),
                'sector': rfp.css('.sector::text').get(default='').strip(),
                'domain': rfp.css('a::attr(href)').get(default='').strip(),
                'deadline': rfp.css('.deadline::text').get(default='').strip(),  # Assume YYYY-MM-DD format
                'budget': rfp.css('.budget::text').get(default='').strip()
            }

# Run spider and insert to DB (for GitHub Actions cron)
if __name__ == '__main__':
    init_db(engine)  # Create table if needed
    with engine.connect() as conn:
        conn.execute(text("TRUNCATE TABLE opportunities"))  # Clear old data for fresh scrape
    process = scrapy.crawler.CrawlerProcess(settings={'ITEM_PIPELINES': {'__main__.DbPipeline': 1}})
    process.crawl(RfpSpider)
    process.start()

class DbPipeline:
    def __init__(self):
        self.engine = create_engine(DATABASE_URL)

    def process_item(self, item, spider):
        with self.engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO opportunities (company_name, province, sector, domain, deadline, budget)
                VALUES (:company_name, :province, :sector, :domain, :deadline::date, :budget)
            """), item)
        return item
