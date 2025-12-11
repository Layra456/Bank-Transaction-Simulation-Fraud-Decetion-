import numpy as np
import pandas as pd
import os
import random
import datetime

# global setting

np.random.seed(123)
random.seed(123)

OUTPUT_DIR = "Bank_reports"
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)


def generate_customers(n_customers=80):
    first_names = ["Ali", "Ahmed", "Ayesha", "Sara", "Hassan", "Hameed", "Zara", "Bilal", "Mariam", "Umar",
                   "Sana", "Nida", "Faraz", "Khalid", "Iqra", "Asad", "Hira", "Rida", "Fahad", "Noor"]
    last_names = ["Khan", "Ahmed", "Raza", "Malik", "Butt",
                  "Qureshi", "Shah", "Javed", "Siddiqui", "Hashmi"]
    cities = ["Lahore", "Karachi", "Islamabad",
              "Multan", "Faisalabad", "Peshawar", "Quetta"]

    customers = []
    for i in range(1, n_customers + 1):
        name = f"{random.choice(first_names)} {random.choice(last_names)}"
        age = random.randint(18, 75)
        city = random.choice(cities)
        email = f"{name.replace(' ', '.').lower()}{i}@gmail.com"
        customers.append({
            "CustomerID": i,
            "Name": name,
            "Age": age,
            "City": city,
            "Email": email,
        })
    customers_df = pd.DataFrame(customers)
    return customers_df


def generate_accounts(customers_df):
    account_types = ["Saving", "Current", "Salary"]
    accounts = []
    acc_id = 10001
    for idx, row in customers_df.iterrows():

        for _ in range(np.random.choice([1, 1, 2], p=[0.5, 0.3, 0.2])):
            balance = np.random.randint(5000, 500000)
            acc_type = random.choice(account_types)
            opened = datetime.datetime(
                2018 + np.random.randint(0, 4), np.random.randint(1, 13), np.random.randint(1, 28))
            accounts.append({
                "AccountID": acc_id,
                "CustomerID": row["CustomerID"],
                "AccountType": acc_type,
                "Balance": balance,
                "OpenedDate": opened
            })
            acc_id += 1
    accounts_df = pd.DataFrame(accounts)
    return accounts_df


def generate_transactions(accounts_df, n_transactions=2500):
    txn_types = ["DEBIT", "CREDIT"]
    merchants = ["Amazon", "Walmart", "LocalStore", "ElectricBill",
                 "WaterBill", "SalaryCredit", "Transfer", "Restaurant", "MobileTopup"]
    countries = ["PK", "US", "AE", "GB", "CN"]
    transactions = []
    txn_id = 500001
    start_date = datetime.date(2024, 1, 1)
    for _ in range(n_transactions):
        acct = accounts_df.sample(1).iloc[0]
        acct_id = acct["AccountID"]
        cust_id = acct["CustomerID"]
        # more debits than credits
        txn_type = np.random.choice(txn_types, p=[0.6, 0.4])
        amount = int(np.round(np.random.exponential(scale=2000))) + 50
        if txn_type == "CREDIT":
            # credits slightly larger sometimes (salary)
            if np.random.rand() < 0.1:
                amount += np.random.randint(20000, 150000)
        merchant = random.choice(merchants)
        country = random.choice(countries)
        days_offset = np.random.randint(0, 365)
        txn_date = start_date + datetime.timedelta(days=int(days_offset))
        time_hour = np.random.randint(0, 24)
        time_min = np.random.randint(0, 60)
        txn_time = datetime.datetime.combine(
            txn_date, datetime.time(hour=time_hour, minute=time_min))
        # random flag for online/offline
        channel = np.random.choice(["POS", "ATM", "ONLINE", "BRANCH"], p=[
                                   0.3, 0.15, 0.45, 0.1])
        transactions.append({
            "TransactionID": txn_id,
            "AccountID": acct_id,
            "CustomerID": cust_id,
            "Type": txn_type,
            "Amount": amount,
            "Merchant": merchant,
            "Country": country,
            "Datetime": txn_time,
            "Channel": channel
        })
        txn_id += 1

    txns_df = pd.DataFrame(transactions)
    # Shuffle for realism
    txns_df = txns_df.sample(frac=1).reset_index(drop=True)
    return txns_df


def apply_transactions(accounts_df, txns_df):
    accounts = accounts_df.set_index("AccountID").copy()
    accounts["Balance_after"] = accounts["Balance"]
    note_list = []

    # Apply transactions in chronological order per account
    txns_sorted = txns_df.sort_values(by="Datetime")
    running_balances = {}

    for idx, txn in txns_sorted.iterrows():
        acct_id = txn["AccountID"]
        amt = txn["Amount"]
        if acct_id not in running_balances:
            running_balances[acct_id] = accounts.at[acct_id, "Balance_after"]
        if txn["Type"] == "DEBIT":
            running_balances[acct_id] -= amt
            action = "DEBIT"
        else:
            running_balances[acct_id] += amt
            action = "CREDIT"
        # track
        note_list.append({
            "TransactionID": txn["TransactionID"],
            "AccountID": acct_id,
            "BalanceAfter": running_balances[acct_id],
            "AppliedType": action
        })
    # join notes back to transactions
    notes_df = pd.DataFrame(note_list)
    txns_with_bal = txns_sorted.merge(
        notes_df, on=["TransactionID", "AccountID"])
    # final balances
    final_balances = []
    for acct_id, bal in running_balances.items():
        final_balances.append({"AccountID": acct_id, "FinalBalance": bal})
    final_balances_df = pd.DataFrame(final_balances)
    accounts = accounts.reset_index().merge(
        final_balances_df, on="AccountID", how="left")
    accounts["FinalBalance"] = accounts["FinalBalance"].fillna(
        accounts["Balance"])  # if no txns
    return accounts, txns_with_bal


def rule_large_transaction(txns_df, threshold=100000):
    # Rule: Any single debit above threshold is suspicious
    mask = (txns_df["Type"] == "DEBIT") & (txns_df["Amount"] >= threshold)
    suspicious = txns_df[mask].copy()
    suspicious["Rule"] = "LargeTransaction"
    suspicious["Score"] = 0.9
    return suspicious


def rule_many_txns_short_period(txns_df, window_minutes=60, count_threshold=6):
    # Rule: more than count_threshold transactions within window_minutes for same account
    df = txns_df.sort_values(by=["AccountID", "Datetime"])
    suspicious_rows = []
    for acct, group in df.groupby("AccountID"):
        times = list(group["Datetime"])
        ids = list(group["TransactionID"])
        for i in range(len(times)):
            start = times[i]
            end = start + datetime.timedelta(minutes=window_minutes)
            # count transactions in window
            cnt = sum(1 for t in times if start <= t <= end)
            if cnt >= count_threshold:
                # add all transactions in window as suspicious
                for j, t in enumerate(times):
                    if start <= t <= end:
                        suspicious_rows.append({
                            "TransactionID": ids[j],
                            "AccountID": acct,
                            "Datetime": times[j],
                            "Rule": "BurstTransactions",
                            "Score": 0.7
                        })
                # skip ahead
    suspicious = pd.DataFrame(suspicious_rows).drop_duplicates(
        subset=["TransactionID"])
    if not suspicious.empty:
        suspicious = suspicious.merge(
            txns_df, on=["TransactionID", "AccountID", "Datetime"], how="left")
    return suspicious


def rule_foreign_country_high_amount(txns_df, domestic="PK", threshold=20000):
    # Rule: DEBITs from foreign country above threshold suspicious
    mask = (txns_df["Type"] == "DEBIT") & (txns_df["Country"]
                                           != domestic) & (txns_df["Amount"] >= threshold)
    suspicious = txns_df[mask].copy()
    suspicious["Rule"] = "ForeignHighAmount"
    suspicious["Score"] = 0.8
    return suspicious


def rule_unusual_channel(txns_df):
    # Rule: High number of online transactions for an account that usually uses POS/ATM
    df = txns_df.copy()
    # compute dominant channel per account
    dom = df.groupby(["AccountID", "Channel"])[
        "TransactionID"].count().reset_index()
    dom_idx = dom.groupby("AccountID")["TransactionID"].idxmax()
    dom_channel = dom.loc[dom_idx][["AccountID", "Channel"]].rename(
        columns={"Channel": "DominantChannel"})
    df = df.merge(dom_channel, on="AccountID", how="left")
    # if dominant channel not ONLINE but transaction channel is ONLINE and amount>50000 mark suspicious
    mask = (df["DominantChannel"] != "ONLINE") & (
        df["Channel"] == "ONLINE") & (df["Amount"] > 50000)
    suspicious = df[mask].copy()
    suspicious["Rule"] = "UnusualChannel"
    suspicious["Score"] = 0.6
    return suspicious


def apply_all_rules(txns_with_bal):
    rules = []
    r1 = rule_large_transaction(txns_with_bal, threshold=100000)
    if not r1.empty:
        rules.append(r1)
    r2 = rule_many_txns_short_period(
        txns_with_bal, window_minutes=60, count_threshold=6)
    if not r2.empty:
        rules.append(r2)
    r3 = rule_foreign_country_high_amount(
        txns_with_bal, domestic="PK", threshold=20000)
    if not r3.empty:
        rules.append(r3)
    r4 = rule_unusual_channel(txns_with_bal)
    if not r4.empty:
        rules.append(r4)
    if rules:
        suspicious_all = pd.concat(rules, ignore_index=True, sort=False)
        # aggregate scores per transaction (max)
        suspicious_all = suspicious_all.sort_values(
            by=["TransactionID", "Score"], ascending=[True, False])
        suspicious_all = suspicious_all.drop_duplicates(
            subset=["TransactionID"])
        # keep important columns
        cols_keep = ["TransactionID", "AccountID", "CustomerID", "Type",
                     "Amount", "Merchant", "Country", "Datetime", "Channel", "Rule", "Score"]
        intersect = [c for c in cols_keep if c in suspicious_all.columns]
        suspicious_all = suspicious_all[intersect]
        suspicious_all = suspicious_all.sort_values(
            by="Score", ascending=False)
        return suspicious_all
    else:
        return pd.DataFrame(columns=["TransactionID"])


def assign_risk_flags(suspicious_df, score_threshold=0.65):
    df = suspicious_df.copy()
    # transactions above threshold flagged
    df["Flag"] = df["Score"].apply(
        lambda x: "HIGH" if x >= score_threshold else ("MEDIUM" if x >= 0.6 else "LOW"))
    return df


def account_risk_summary(suspicious_df):
    # summarize by account
    if suspicious_df.empty:
        return pd.DataFrame(columns=["AccountID", "NumAlerts", "MaxScore", "AvgScore", "RiskLevel"])
    grp = suspicious_df.groupby("AccountID")["Score"].agg(
        ["count", "max", "mean"]).reset_index()
    grp.columns = ["AccountID", "NumAlerts", "MaxScore", "AvgScore"]

    def risk_level(row):
        if row["MaxScore"] >= 0.85 or row["NumAlerts"] >= 3:
            return "HIGH"
        if row["MaxScore"] >= 0.7:
            return "MEDIUM"
        return "LOW"
    grp["RiskLevel"] = grp.apply(risk_level, axis=1)
    return grp


def export_all_data(customers_df, accounts_df, txns_with_bal, suspicious_df, account_risk_df):
    customers_df.to_csv(os.path.join(OUTPUT_DIR, "customers.csv"), index=False)
    accounts_df.to_csv(os.path.join(OUTPUT_DIR, "accounts.csv"), index=False)
    txns_with_bal.to_csv(os.path.join(
        OUTPUT_DIR, "transactions.csv"), index=False)
    suspicious_df.to_csv(os.path.join(
        OUTPUT_DIR, "suspicious_transactions.csv"), index=False)
    account_risk_df.to_csv(os.path.join(
        OUTPUT_DIR, "account_risk_summary.csv"), index=False)
    print(f"\n✅ All reports exported to folder: {OUTPUT_DIR}")


def print_summary_stats(customers_df, accounts_df, txns_with_bal):
    print("\n---------------- SUMMARY STATS ----------------")
    print("Customers:", customers_df.shape[0])
    print("Accounts:", accounts_df.shape[0])
    print("Transactions:", txns_with_bal.shape[0])
    print("Date range:", txns_with_bal["Datetime"].min(
    ), "to", txns_with_bal["Datetime"].max())
    print("Total Debited:",
          txns_with_bal[txns_with_bal["Type"] == "DEBIT"]["Amount"].sum())
    print("Total Credited:",
          txns_with_bal[txns_with_bal["Type"] == "CREDIT"]["Amount"].sum())


def monthly_aggregate(txns_with_bal):
    df = txns_with_bal.copy()
    df["Month"] = df["Datetime"].dt.to_period("M")
    monthly = df.groupby(["Month", "Type"])[
        "Amount"].sum().unstack(fill_value=0).reset_index()
    return monthly


def customer_statement(customer_id, txns_with_bal):
    df = txns_with_bal[txns_with_bal["CustomerID"] ==
                       customer_id].sort_values(by="Datetime", ascending=False)
    if df.empty:
        print(f"\nNo transactions found for CustomerID {customer_id}")
        return
    print(f"\n--- Last 10 transactions for CustomerID {customer_id} ---")
    print(df[["Datetime", "AccountID", "Type",
          "Amount", "Merchant", "Channel"]].head(10))


def menu_help():
    print("\n===== BANK ANALYTICS MENU HELP =====")
    print("1  - Show basic summary stats")
    print("2  - Show top N accounts by final balance")
    print("3  - Show monthly aggregates (debit/credit)")
    print("4  - View transactions for an account")
    print("5  - Run fraud detection rules and show suspicious transactions")
    print("6  - Show account risk summary")
    print("7  - Export all reports to CSV")
    print("8  - Show customer statement (last 10 txns)")
    print("9  - Regenerate fresh dataset (new simulation)")
    print("0  - Exit")


def top_accounts(accounts_df, n=10):
    top = accounts_df.sort_values(by="FinalBalance", ascending=False).head(n)
    print(f"\nTop {n} accounts by Final Balance:")
    print(top[["AccountID", "CustomerID", "FinalBalance", "AccountType"]])


def view_account_transactions(acc_id, txns_with_bal):
    df = txns_with_bal[txns_with_bal["AccountID"] ==
                       acc_id].sort_values(by="Datetime", ascending=False)
    if df.empty:
        print(f"\nNo transactions found for AccountID {acc_id}")
        return
    print(f"\n--- Transactions for AccountID {acc_id} ---")
    print(df[["Datetime", "Type", "Amount", "Merchant",
          "Country", "Channel", "BalanceAfter"]].head(20))


def run_simulation_and_menu():
    print("Starting Bank Transaction Simulation...")
    customers_df = generate_customers(n_customers=120)
    print("Generated customers:", customers_df.shape[0])
    accounts_df = generate_accounts(customers_df)
    print("Generated accounts:", accounts_df.shape[0])
    txns_df = generate_transactions(accounts_df, n_transactions=4500)
    print("Generated transactions:", txns_df.shape[0])
    accounts_with_bal, txns_with_bal = apply_transactions(accounts_df, txns_df)
    # ensure Datetime is datetime64
    txns_with_bal["Datetime"] = pd.to_datetime(txns_with_bal["Datetime"])
    print("Applied transactions and computed running balances.")
    suspicious_df = pd.DataFrame()
    account_risk_df = pd.DataFrame()

    while True:
        print("\n================= BANK ANALYTICS SYSTEM =================")
        print("1. Summary Stats")
        print("2. Top Accounts (Final Balance)")
        print("3. Monthly Aggregates")
        print("4. View Account Transactions")
        print("5. Run Fraud Detection Rules")
        print("6. Account Risk Summary")
        print("7. Export Reports")
        print("8. Customer Statement")
        print("9. Regenerate Dataset (Fresh Simulation)")
        print("0. Exit")
        choice = input("Enter choice: ").strip()

        if choice == "1":
            print_summary_stats(customers_df, accounts_with_bal, txns_with_bal)

        elif choice == "2":
            try:
                n = int(input("How many top accounts to show? (default 10): ") or 10)
            except:
                n = 10
            top_accounts(accounts_with_bal, n=n)

        elif choice == "3":
            monthly = monthly_aggregate(txns_with_bal)
            print("\nMonthly aggregates (Debit & Credit):")
            print(monthly)
            # save monthly for quick view
            monthly.to_csv(os.path.join(
                OUTPUT_DIR, "monthly_aggregates.csv"), index=False)
            print(
                f"Saved monthly aggregates to {os.path.join(OUTPUT_DIR, 'monthly_aggregates.csv')}")

        elif choice == "4":
            try:
                aid = int(input("Enter AccountID: ").strip())
                view_account_transactions(aid, txns_with_bal)
            except ValueError:
                print("Please enter valid integer AccountID.")

        elif choice == "5":
            print("\nRunning fraud detection rules...")
            suspicious_df = apply_all_rules(txns_with_bal)
            if suspicious_df.empty:
                print("No suspicious transactions detected by current rules.")
            else:
                suspicious_df = assign_risk_flags(
                    suspicious_df, score_threshold=0.65)
                print(
                    f"Suspicious transactions found: {suspicious_df.shape[0]}")
                # print top 20
                print(suspicious_df.sort_values(
                    by="Score", ascending=False).head(20))
                suspicious_df.to_csv(os.path.join(
                    OUTPUT_DIR, "suspicious_transactions_temp.csv"), index=False)
                print(
                    f"Saved suspicious transactions preview to {os.path.join(OUTPUT_DIR, 'suspicious_transactions_temp.csv')}")

        elif choice == "6":
            if suspicious_df.empty:
                print("No suspicious transactions available. Run option 5 first.")
            else:
                account_risk_df = account_risk_summary(suspicious_df)
                print("\nAccount Risk Summary:")
                print(account_risk_df.sort_values(
                    by=["RiskLevel", "NumAlerts"], ascending=[False, False]).head(50))
                account_risk_df.to_csv(os.path.join(
                    OUTPUT_DIR, "account_risk_summary.csv"), index=False)
                print(
                    f"Saved account risk summary to {os.path.join(OUTPUT_DIR, 'account_risk_summary.csv')}")

        elif choice == "7":
            export_all_data(customers_df, accounts_with_bal,
                            txns_with_bal, suspicious_df, account_risk_df)

        elif choice == "8":
            try:
                cid = int(input("Enter CustomerID: ").strip())
                customer_statement(cid, txns_with_bal)
            except ValueError:
                print("Enter valid integer CustomerID.")

        elif choice == "9":
            print("\nRegenerating fresh dataset...")
            customers_df = generate_customers(n_customers=120)
            accounts_df = generate_accounts(customers_df)
            txns_df = generate_transactions(accounts_df, n_transactions=4500)
            accounts_with_bal, txns_with_bal = apply_transactions(
                accounts_df, txns_df)
            txns_with_bal["Datetime"] = pd.to_datetime(
                txns_with_bal["Datetime"])
            suspicious_df = pd.DataFrame()
            account_risk_df = pd.DataFrame()
            print("Fresh simulation ready.")

        elif choice == "0":
            print("\nExiting. Goodbye!")
            break

        else:
            print("Invalid choice. Type a number from 0-9.")


# -----------------------------
# ENTRY POINT
# -----------------------------
if __name__ == "__main__":
    run_simulation_and_menu()
