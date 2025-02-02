#!/usr/bin/env python

import json
import logging
import sys
from pathlib import Path

from beancount import loader
from beancount.core import data
from beancount.parser import version
from beancount.utils import misc_utils

account_map: dict[str, int] = {}
document_path: Path
sql_statements = []
category_map: dict[str, int] = {}

def generate_truncate_sql():
    sql_statements.extend([
        'DELETE FROM document;',
        'DELETE FROM posting;',
        'DELETE FROM transaction_link;',
        'DELETE FROM transaction_tag;',
        'DELETE FROM link;',
        'DELETE FROM tag;',
        'DELETE FROM "transaction";',
        'DELETE FROM price;',
        'DELETE FROM "assertion";',
        'DELETE FROM account_currency;',
        'DELETE FROM account;',
        'DELETE FROM account_category;',
        'DELETE FROM commodity;'
    ])

def get_account_type_and_categories(account_name):
    """Extract account type and category name from account name."""
    parts = account_name.split(':')
    account_type = parts[0]  # 例如 "Equity"
    # 只取分类名称部分，不包含账户类型
    category = parts[1] if len(parts) > 1 else None
    return account_type, category

def ensure_account_category(account_name):
    """Ensure account category exists and return its id."""
    account_type, category = get_account_type_and_categories(account_name)
    
    # 添加调试信息
    print(f"Processing account: {account_name}")
    print(f"Account type: {account_type}")
    print(f"Category: {category}")
    
    if not category:
        print("No category found, returning None")
        return None
        
    category_key = f"{account_type}:{category}"
    print(f"Category key: {category_key}")
    print(f"Current category_map: {category_map}")
    
    if category_key not in category_map:
        next_category_id = len(category_map) + 1  # 从1开始
        sql = f"""INSERT INTO account_category (id, name, parent_id, account_type)
                 VALUES ({next_category_id}, '{escape_sql(category)}', NULL, 
                 '{escape_sql(account_type)}');"""
        sql_statements.append(sql)
        category_map[category_key] = next_category_id
        print(f"Created new category with id: {next_category_id}")
        return next_category_id
    
    category_id = category_map[category_key]
    print(f"Found existing category with id: {category_id}")
    return category_id

def import_accounts(entries):
    for eid, entry in enumerate(entries):
        if isinstance(entry, data.Open):
            account_type, _ = get_account_type_and_categories(entry.account)
            category_id = ensure_account_category(entry.account)
            print(f"Got category_id: {category_id} for account: {entry.account}")
            meta = get_meta_json(entry.meta)
            
            # 使用更明确的条件判断
            category_id_sql = 'NULL' if category_id is None else str(category_id)
            
            sql = f"""INSERT INTO account (id, name, account_type, account_category_id, 
                     open_date, meta) 
                     VALUES ({eid + 1}, '{escape_sql(entry.account)}',  -- 从1开始
                     '{escape_sql(account_type)}',
                     {category_id_sql}, '{entry.date}',
                     '{escape_sql(meta)}');"""
            sql_statements.append(sql)
            account_map[entry.account] = eid + 1  # 更新account_map使用新的ID
            
            if entry.currencies:
                for currency in entry.currencies:
                    sql = f"""INSERT INTO account_currency (account_id, currency)
                             VALUES ({eid + 1}, '{escape_sql(currency)}');"""
                    sql_statements.append(sql)

    for entry in entries:
        if isinstance(entry, data.Close):
            sql = f"""UPDATE account SET close_date = '{entry.date}' 
                     WHERE name = '{escape_sql(entry.account)}';"""
            sql_statements.append(sql)

def import_transactions(entries):
    for eid, entry in enumerate(entries):
        if isinstance(entry, data.Transaction):
            # Insert transaction
            sql = f"""INSERT INTO "transaction" (id, flag, payee, narration)
                     VALUES ({eid + 1}, '{escape_sql(entry.flag or "")}', 
                     '{escape_sql(entry.payee or "")}', 
                     '{escape_sql(entry.narration or "")}');"""
            sql_statements.append(sql)
            
            # Insert tags
            if entry.tags:
                for tag in entry.tags:
                    sql = f"""INSERT OR IGNORE INTO tag (name) VALUES ('{escape_sql(tag)}');"""
                    sql_statements.append(sql)
                    sql = f"""INSERT INTO transaction_tag (transaction_id, tag_id)
                             SELECT {eid + 1}, id FROM tag WHERE name = '{escape_sql(tag)}';"""
                    sql_statements.append(sql)
            
            # Insert links
            if entry.links:
                for link in entry.links:
                    sql = f"""INSERT OR IGNORE INTO link (name) VALUES ('{escape_sql(link)}');"""
                    sql_statements.append(sql)
                    sql = f"""INSERT INTO transaction_link (transaction_id, link_id)
                             SELECT {eid + 1}, id FROM link WHERE name = '{escape_sql(link)}';"""
                    sql_statements.append(sql)

            for pid, posting in enumerate(entry.postings):
                amount = get_amount(posting.units)
                cost = get_amount(posting.cost)
                price = get_amount(posting.price)
                account_id = account_map[posting.account]
                
                sql = f"""INSERT INTO posting (id, date, account_id, transaction_id, flag, 
                         amount_number, amount_currency, 
                         price_number, price_currency,
                         cost_number, cost_currency, cost_date, cost_label)
                         VALUES ({(eid + 1) * 1000 + pid + 1}, '{entry.date}', {account_id}, {eid + 1}, 
                         '{escape_sql(posting.flag or "")}',
                         {amount[0]}, '{escape_sql(amount[1])}',
                         {price[0] if price else 'NULL'}, 
                         {f"'{escape_sql(price[1])}'" if price else 'NULL'},
                         {cost[0] if cost else 'NULL'}, 
                         {f"'{escape_sql(cost[1])}'" if cost else 'NULL'},
                         {f"'{posting.cost.date}'" if posting.cost and posting.cost.date else 'NULL'},
                         {f"'{escape_sql(posting.cost.label)}'" if posting.cost and posting.cost.label else 'NULL'});"""
                sql_statements.append(sql)

def import_balances(entries):
    for eid, entry in enumerate(entries):
        if isinstance(entry, data.Balance):
            account_id = account_map[entry.account]
            amount = get_amount(entry.amount)
            sql = f"""INSERT INTO "assertion" (id, date, account_id, amount_number, amount_currency)
                     VALUES ({eid}, '{entry.date}', {account_id}, {amount[0]}, '{amount[1]}');"""
            sql_statements.append(sql)

def import_prices(entries):
    for eid, entry in enumerate(entries):
        if isinstance(entry, data.Price):
            amount = get_amount(entry.amount)
            sql = f"""INSERT INTO price (id, date, currency, amount_number, amount_currency)
                     VALUES ({eid}, '{entry.date}', '{entry.currency}', 
                     {amount[0]}, '{amount[1]}');"""
            sql_statements.append(sql)

def import_commodities(entries):
    for eid, entry in enumerate(entries):
        if isinstance(entry, data.Commodity):
            decimal_places = entry.meta.pop("decimal_places", 0)
            meta = get_meta_json(entry.meta)
            sql = f"""INSERT INTO commodity (id, date, currency, decimal_places, meta)
                     VALUES ({eid}, '{entry.date}', '{entry.currency}', 
                     {decimal_places}, '{meta}');"""
            sql_statements.append(sql)

def import_documents(entries):
    if document_path is None:
        return

    for eid, entry in enumerate(entries):
        if isinstance(entry, data.Document):
            account_id = account_map[entry.account]
            filename = str(Path(entry.filename).relative_to(document_path))
            with open(entry.filename, "rb") as f:
                file_data = f.read()
            
            hex_data = ''.join([f'{x:02x}' for x in file_data])
            sql = f"""INSERT INTO document (id, date, account_id, filename, data)
                     VALUES ({eid}, '{entry.date}', {account_id}, '{filename}', X'{hex_data}');"""
            sql_statements.append(sql)

def get_amount(amount):
    return (amount.number, amount.currency) if amount is not None else None

def get_meta_json(meta):
    keys_to_remove = {"filename", "lineno"}
    filtered_meta = {
        key: value for key, value in meta.items() if key not in keys_to_remove
    }

    return json.dumps(filtered_meta)

def escape_sql(s):
    """Escape single quotes in SQL strings."""
    if s is None:
        return ""
    return str(s).replace("'", "''")

def save_sql_file(filename):
    with open(filename, 'w', encoding='utf-8') as f:
        for statement in sql_statements:
            f.write(statement + '\n')

def main():
    global document_path

    parser = version.ArgumentParser(description=__doc__)
    parser.add_argument("filename", help="Beancount input filename")
    parser.add_argument("output", help="Output SQL filename")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)-8s: %(message)s")

    entries, errors, options_map = loader.load_file(
        args.filename, log_timings=logging.info, log_errors=sys.stderr
    )

    if len(options_map["documents"]) > 0:
        document_path = Path(args.filename).parent / options_map["documents"][0]
    else:
        document_path = None

    for function in [
        generate_truncate_sql,
        lambda: import_accounts(entries),
        lambda: import_transactions(entries),
        lambda: import_balances(entries),
        lambda: import_prices(entries),
        lambda: import_commodities(entries),
        lambda: import_documents(entries),
    ]:
        step_name = getattr(function, "__name__", function.__class__.__name__)
        with misc_utils.log_time(step_name, logging.info):
            function()

    save_sql_file(args.output)

if __name__ == "__main__":
    main()
