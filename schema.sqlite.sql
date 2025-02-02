-- SQLite schema for beancount database
-- Custom types are not supported in SQLite, we'll use TEXT to store JSON-like strings
-- for complex types like amount, lot etc.
-- Account type table (如: Equity, Assets, Liabilities, Income, Expenses)
CREATE TABLE account_type (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

-- Account category table (支持层级结构)
CREATE TABLE account_category (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    parent_id INTEGER,
    account_type TEXT NOT NULL CHECK(
        account_type IN (
            'Assets',
            'Liabilities',
            'Equity',
            'Income',
            'Expenses'
        )
    ),
    FOREIGN KEY (parent_id) REFERENCES account_category(id),
    UNIQUE (name, parent_id, account_type)
);

-- Modified account table
CREATE TABLE account (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    account_type TEXT NOT NULL CHECK(
        account_type IN (
            'Assets',
            'Liabilities',
            'Equity',
            'Income',
            'Expenses'
        )
    ),
    account_category_id INTEGER NOT NULL,
    open_date DATE NOT NULL,
    close_date DATE,
    meta TEXT DEFAULT '{}' NOT NULL,
    -- JSON object
    FOREIGN KEY (account_category_id) REFERENCES account_category(id)
);

-- Account currencies table (replaces currencies array)
CREATE TABLE account_currency (
    account_id INTEGER NOT NULL,
    currency TEXT NOT NULL,
    PRIMARY KEY (account_id, currency),
    FOREIGN KEY (account_id) REFERENCES account(id)
);

-- Transaction table
CREATE TABLE "transaction" (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    flag TEXT NOT NULL,
    payee TEXT NOT NULL,
    narration TEXT NOT NULL
);

-- Tags table
CREATE TABLE tag (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

-- Transaction tags junction table
CREATE TABLE transaction_tag (
    transaction_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,
    PRIMARY KEY (transaction_id, tag_id),
    FOREIGN KEY (transaction_id) REFERENCES "transaction"(id),
    FOREIGN KEY (tag_id) REFERENCES tag(id)
);

-- Links table
CREATE TABLE link (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

-- Transaction links junction table
CREATE TABLE transaction_link (
    transaction_id INTEGER NOT NULL,
    link_id INTEGER NOT NULL,
    PRIMARY KEY (transaction_id, link_id),
    FOREIGN KEY (transaction_id) REFERENCES "transaction"(id),
    FOREIGN KEY (link_id) REFERENCES link(id)
);

-- Posting table
-- For amount type: {number: DECIMAL, currency: TEXT}
CREATE TABLE posting (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL,
    account_id INTEGER NOT NULL,
    transaction_id INTEGER NOT NULL,
    flag TEXT,
    -- amount fields (required)
    amount_number DECIMAL NOT NULL,
    amount_currency TEXT NOT NULL,
    -- price fields (optional)
    price_number DECIMAL,
    price_currency TEXT,
    -- cost fields (optional)
    cost_number DECIMAL,
    cost_currency TEXT,
    cost_date DATE,
    cost_label TEXT,
    matching_lot_id INTEGER,
    FOREIGN KEY (account_id) REFERENCES account(id),
    FOREIGN KEY (transaction_id) REFERENCES "transaction"(id),
    FOREIGN KEY (matching_lot_id) REFERENCES posting(id)
);

-- Create indexes for posting table
CREATE INDEX posting_account_id_date_id_idx ON posting(account_id, date, id);

CREATE INDEX posting_transaction_id_idx ON posting(transaction_id);

-- Commodity table
CREATE TABLE commodity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL,
    currency TEXT NOT NULL UNIQUE,
    meta TEXT DEFAULT '{}' NOT NULL,
    -- JSON object
    decimal_places INTEGER NOT NULL,
    CHECK (currency != '')
);

-- Price table
CREATE TABLE price (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL,
    currency TEXT NOT NULL,
    amount_number DECIMAL NOT NULL,
    amount_currency TEXT NOT NULL
);

-- Assertion table (previously called balance)
CREATE TABLE assertion (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL,
    account_id INTEGER NOT NULL,
    amount_number DECIMAL NOT NULL,
    amount_currency TEXT NOT NULL,
    FOREIGN KEY (account_id) REFERENCES account(id)
);

-- Document table
CREATE TABLE document (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL,
    account_id INTEGER NOT NULL,
    data BLOB NOT NULL,
    filename TEXT NOT NULL,
    FOREIGN KEY (account_id) REFERENCES account(id)
);

-- Note: The following PostgreSQL features are not directly supported in SQLite:
-- 1. Schemas
-- 2. Complex functions and aggregates
-- 3. Views with complex queries
-- 4. Many of the PostgreSQL specific functions
-- Key changes from PostgreSQL schema:
-- 1. Custom type 'amount' is split into number and currency columns
-- 2. Using SQLite's built-in DATE type for dates
-- 3. Using DECIMAL for numeric values
-- 4. Arrays are converted to junction tables
-- 5. Complex objects are stored as JSON strings