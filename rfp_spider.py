import scrapy
from scrapy.crawler import CrawlerProcess
from datetime import datetime
import csv
import re

class RfpSpider(scrapy.Spider):
    name = 'rfp'
    allowed_domains = ['merx.com', 'bcbid.gov.bc.ca', 'purchasingconnection.ca']
    start_urls = [
        'https://www.merx.com/public/solicitations/british-columbia-379',  # BC MERX
        'https://www.merx.com/public/solicitations/alberta-373',           # AB MERX
        'https://bcbid.gov.bc.ca/page.aspx/en/rfp/request_browse_public',  # BC Bid
        'https://www.purchasingconnection.ca/Search.aspx',                 # AB Purchasing (search page)
    ]

    custom_settings = {
        'ROBOTSTXT_OBEY': True,
        'DOWNLOAD_DELAY': 5,  # Respect delays
        'USER_AGENT': 'RiskScraper/1.0 (contact: your@email.com)',
    }

    def __init__(self):
        self.risk_keywords = ['risk', 'compliance', 'audit', 'consulting', 'management']

    def parse(self, response):
        # MERX pattern (adapt for each site)
        if 'merx.com' in response.url:
            for rfp in response.css('.solicitation-item'):  # Adjust selector based on inspection
                title = rfp.css('.title::text').get(default='').lower()
                if any(kw in title for kw in self.risk_keywords):
                    yield {
                        'company_name': rfp.css('.issuer::text').get(default='MERX'),
                        'province': 'BC' if 'british-columbia' in response.url else 'AB',
                        'sector': 'Government',
                        'domain': response.urljoin(rfp.css('a::attr(href)').get()),
                        'deadline': rfp.css('.deadline::text').get(default=datetime.now().strftime('%Y-%m-%d')),
                        'budget': rfp.css('.budget::text').get(default=''),
                    }
        # BC Bid pattern
        elif 'bcbid.gov.bc.ca' in response.url:
            for rfp in response.css('tr[class*="rfp-row"]'):
                title = rfp.css('td.title::text').get(default='').lower()
                if any(kw in title for kw in self.risk_keywords):
                    yield {
                        'company_name': rfp.css('td.issuer::text').get(default='BC Gov'),
                        'province': 'BC',
                        'sector': 'Government',
                        'domain': response.urljoin(rfp.css('a::attr(href)').get()),
                        'deadline': rfp.css('td.deadline::text').get(default=''),
                        'budget': '',
                    }
        # AB Purchasing (form-based—use params)
        elif 'purchasingconnection.ca' in response.url:
            # Simulate search for "risk consulting"
            yield scrapy.FormRequest.from_response(
                response,
                formdata={'keywords': 'risk compliance audit consulting', 'province': 'AB'},
                callback=self.parse_ab,
            )

    def parse_ab(self, response):
        # Parse results (similar to above)
        for rfp in response.css('.opportunity-row'):
            title = rfp.css('.title::text').get(default='').lower()
            if any(kw in title for kw in self.risk_keywords):
                yield {
                    'company_name': rfp.css('.buyer::text').get(default='AB Gov'),
                    'province': 'AB',
                    'sector': 'Government',
                    'domain': response.urljoin(rfp.css('a::attr(href)').get()),
                    'deadline': rfp.css('.closing::text').get(default=''),
                    'budget': '',
                }

# Run and save to CSV
if __name__ == '__main__':
    process = CrawlerProcess(settings={
        'FEEDS': {
            'opportunities.csv': {'format': 'csv', 'overwrite': True},
        },
        'ITEM_PIPELINES': {'scrapy.pipelines.files.FilesPipeline': 1},
    })
    process.crawl(RfpSpider)
    process.start()
