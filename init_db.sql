CREATE TABLE opportunities (
    id SERIAL PRIMARY KEY,
    company_name VARCHAR(255),
    province VARCHAR(2),
    sector VARCHAR(100),
    domain TEXT,
    deadline DATE,
    budget VARCHAR(50),
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
