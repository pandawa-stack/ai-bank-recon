# AI Bank Reconciliation Agent

This project is an **AI-assisted bank reconciliation tool**.

It helps compare **bank statements** vs **book records** (general ledger / cashbook) and:
- highlight matched transactions,
- detect unmatched items,
- summarize differences,
- prepare adjustments for reconciliation.

---

## ✨ Key Features

- Upload bank statements (Excel/CSV)
- Upload book records (Excel/CSV)
- Automatic matching by date, amount, and reference
- Tolerance options for date / amount differences
- Summary of:
  - total bank vs total book
  - matched / unmatched counts
  - reconciling items
- Export reconciliation result (to Excel/CSV)
- Built for **real finance workflows**, not demo.

---

## 🛠 Tech Stack

- Python
- Streamlit
- Pandas
- openpyxl / csv
- (optional) simple rules/AI-assisted matching logic

---

## 🚀 Quick Start

1. Create & activate a virtual environment (optional but recommended)
2. Install dependencies:
   ```bash
   pip install -r requirements.txt

---

## 🧪 Sample Data

You can try the app using the sample files in `data_samples/`:

- `bank_statement_example.xlsx`
- `book_record_example.xlsx`
