this repo is a fork of [beanpost](https://github.com/gerdemb/beanpost)

I'm using sqlite instead of postgresql, and the schema is slightly different.

## How Does It Work?

The project has three main components:

1. A SQLite schema `schema.sqlite.sql`
2. An import command `beanpost-import.py` to convert a beancount file into the sqlite sql file
3. example.beancount is a beancount file that I'm using for testing
4. output.sql is the sqlite sql file that is created by the import file

## How Do I Try This?

To get started with beanpost, follow these steps:

please install the requirements first:

`pip install -r requirements.txt`

1. Create the schema in your SQLite database with schema.sqlite.sql

2. convert a beancount file into the sqlite sql file:

`./beanpost-import.py example.beancount output.sql`

## What's Missing? (from beanpost)

Although beanpost is fairly comprehensive, some features are currently missing:

- _Some beancount data types are not imported_: While the common directives are supported, some more obscure feature aren't. These could likely be added easily.
  1. `Notes` and `Events` directives
  2. Flags on postings
- _Validation_: should be straightforward to add most of these.
  1.  Check for transactions occurring after an account has been closed
  2.  Check that transactions match with specified account currencies
  3.  Check that inventory reductions have the same currency as the augmentation (lot) they are reducing from
  4.  Check that inventory reductions don't reduce lot amounts below zero
  5.  For strict cost-basis, all reductions should have matching augmentation lots
  6.  Check that date of inventory reduction is after date of augmentation
- _Plugins_
- _Importing statements_: This might be out of scope for this project. Since the data is stored in a PostgreSQL database, any client that can insert data into the database could be written in any language.

## What is Different from beancount? (from beanpost)

- _Transaction dates_: Each posting can have its own date, allowing transactions to balance even if individual postings have different dates. This helps with common issues when transferring money between accounts where withdrawal and deposit dates differ.
- _Pad directives_: Converted to regular Transaction directives with a fixed amount instead of "padded" adjustable amounts.
- _Tolerances_: Decimal places for commodities are defined explicitly in the commodity table decimal_places column, not derived automatically like in beancount. Tolerances are calculated as if the option `infer_tolerance_from_cost` is true.
- _Documents_: Stored as byte data inside the database, with support for import and export.
- _Balance directive name_: Beancount `Balance` directives are stored in the assertion table for clarity.
- _Lot matching_: The logic for matching lots for cost basis has not been tested thoroughly and may not match lots in the exact same way as beancount does.

## Conclusions (from beanpost)

Implementing most of beancount's core functionality with PostgreSQL was surprisingly straightforward. While some features are missing, adding them shouldn't be a major challenge. The main advantage of PostgreSQL is the ability to easily query and manipulate data, which can sometimes be difficult with simple text files. However, simple text files have the benefit of being more accessible and user-friendly, a front-end will be required to make this a truely useful project.

I have tested this with a personal beancount file containing about 10,000 entries, spanning four years, with transactions in multiple currencies and various accounts. So far, I haven't found any discrepancies between the original beancount file and the exported data from beanpost. I'd love to hear about your experiences with beanpost—please drop me a line!

# beancount-sqlite
