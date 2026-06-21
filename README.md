# Bank Transaction Analytics & Fraud Detection System

## Project Overview
This project simulates a real-world banking transaction system using Python. It generates synthetic customers, accounts, and transactions, then applies rule-based logic to detect and flag potentially fraudulent activity.

## Data Structure

**Customers:** CustomerID, Name, Age, City, Email

**Accounts:** AccountID, CustomerID, AccountType, Balance, OpenedDate

**Transactions:** TransactionID, AccountID, Type (Debit/Credit), Amount, Merchant, Country, Datetime, Channel

A customer can have multiple accounts, and each account can have multiple transactions.

## Fraud Detection Rules

The system uses four rules to identify suspicious transactions:

1. Large Transaction Rule – Flags single debits above a set threshold
2. Burst Transactions Rule – Flags accounts with unusually frequent transactions in a short time
3. Foreign High-Amount Rule – Flags large debits made from foreign countries
4. Unusual Channel Rule – Flags accounts using an unexpected transaction channel

Each flagged transaction is assigned a risk score and classified as High, Medium, or Low risk. An account-level summary highlights the riskiest accounts overall.

## Tools Used
Python, Pandas, NumPy, Datetime

## Features
- Synthetic data generation for customers, accounts, and transactions
- Running balance calculation
- Rule-based fraud detection
- Monthly transaction reports
- Account risk summaries
- CSV export of all reports
- Command-line menu for interaction

## How to Run

1. Clone the repository
2. Install dependencies: pip install pandas numpy
3. Run the program: python main.py
4. Use the menu options to view reports, run fraud detection, or export data

## Output
All reports are saved automatically in the Bank_reports folder, including customer data, account data, transactions, suspicious transactions, and risk summaries.

## Purpose
This project was built to practice data processing and analysis with Python, apply rule-based business logic similar to real banking fraud systems, and serve as a portfolio project for a Data Analyst role.
