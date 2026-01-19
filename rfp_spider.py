import scrapy
from sqlalchemy import create_engine, text
import os
import datetime

DATABASE_URL = os.environ.get('DATABASE_URL').replace("postgres://", "postgresql://")

class RfpSpider(scrapy.Spider):
    name = 'rfp_spider'
    start_urls = ['https://example-rfp-site.com']  # Update with actual

    def parse(self, response):
        # Your parsing logic here, yielding dicts like {'company_name': ..., 'province': ..., etc.}
        yield {'company_name': 'Example', 'province': 'BC', 'sector': 'Mining', 'domain': 'https://example.com', 'deadline': '2026-02-01', 'budget': '$100k'}

# Run spider and insert to DB (for Cron)
if __name__ == '__main__':
    from scrapy.crawler import CrawlerProcess
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        conn.execute(text("TRUNCATE TABLE opportunities"))  # Clear old data
    process = CrawlerProcess(settings={'ITEM_PIPELINES': {'__main__.DbPipeline': 1}})
    process.crawl(RfpSpider)
    process.start()

class DbPipeline:
    def __init__(self):
        self.engine = create_engine(DATABASE_URL)

    def process_item(self, item, spider):
        with self.engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO opportunities (company_name, province, sector, domain, deadline, budget)
                VALUES (:company_name, :province, :sector, :domain, :deadline, :budget)
            """), item)
        return item
