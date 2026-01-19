import scrapy
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import Column, Integer, String, Date, DateTime
import os
import datetime

DATABASE_URL = os.environ.get('DATABASE_URL').replace("postgres://", "postgresql://")

# Define the table schema
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
    start_urls = ['https://example-rfp-site.com']  # Update with actual

    def parse(self, response):
        # Your parsing logic here, yielding dicts like {'company_name': ..., 'province': ..., etc.}
        yield {'company_name': 'Example', 'province': 'BC', 'sector': 'Mining', 'domain': 'https://example.com', 'deadline': '2026-02-01', 'budget': '$100k'}

# Run spider and insert to DB (for Cron)
if __name__ == '__main__':
    engine = create_engine(DATABASE_URL)
    init_db(engine)  # Create table if needed
    with engine.connect() as conn:
        conn.execute(text("TRUNCATE TABLE opportunities"))  # Clear old data
    process = scrapy.crawler.CrawlerProcess(settings={'ITEM_PIPELINES': {'__main__.DbPipeline': 1}})
    process.crawl(RfpSpider)
    process.start()

class DbPipeline:
    def __init__(self):
        self.engine = create_engine(DATABASE_URL)

    def process_item(self, item, spider):
        with self.engine.connect() as conn:
            # Use raw insert, but update deadline to DATE if needed
            conn.execute(text("""
                INSERT INTO opportunities (company_name, province, sector, domain, deadline, budget)
                VALUES (:company_name, :province, :sector, :domain, :deadline::date, :budget)
            """), item)
        return item
