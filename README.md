# 🔍 Transaction Comparison AI

Automated reconciliation between **bank mutation documents** and **internal finance records** — powered by Google Gemini AI.

---

## ✨ Features

| Feature | Description |
|---|---|
| 📄 PDF Parsing | Extracts transactions from BCA/bank PDF mutations via Gemini Vision |
| 📊 Excel Parsing | Reads finance records (Tgl Transaksi, Total Penjualan, etc.) directly |
| 🔄 3-Level Matching | Exact → Fuzzy (date/amount/description) → Unmatched |
| 📥 Excel Report | Full comparison table with color-coded match status (3 sheets) |
| 📄 PDF Summary | Professional summary: KPIs, amounts, discrepancy, unmatched list |
| 🎛️ UI Controls | Adjustable fuzzy threshold, amount tolerance, date tolerance |

---

## 🚀 Quick Start

### 1. Clone / extract the project

```bash
cd transaction_comparison_app
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure your API key

```bash
cp .env.example .env
```

Edit `.env` and paste your Gemini API key:

```
GEMINI_API_KEY=AIzaSy...your_key_here
```

> **Get a free Gemini API key:** https://aistudio.google.com/app/apikey

### 4. Run the app

```bash
streamlit run main.py
```

The app opens at **http://localhost:8501**

---

## 📁 Project Structure

```
transaction_comparison_app/
├── main.py                          # Streamlit UI entry point
├── requirements.txt
├── .env.example                     # ← copy to .env and fill in key
│
└── app/
    ├── parser/
    │   ├── gemini_parser.py         # Gemini API calls + Excel fallback
    │   └── preprocess.py            # IDR amount + date normalisation
    │
    ├── matcher/
    │   └── match_engine.py          # 3-level matching engine
    │
    ├── report/
    │   └── generate_report.py       # Excel (xlsxwriter) + PDF (ReportLab)
    │
    └── utils/
        ├── config.py                # Reads .env, exposes settings
        └── logger.py                # Structured logging
```

---

## 📂 Supported File Formats

| Document | Accepted Formats |
|---|---|
| Bank Mutation | `.pdf` (scanned or digital), `.xlsx` |
| Finance Record | `.xlsx`, `.xls` |

### Finance Excel Expected Columns

The parser auto-detects these column names (case-insensitive):

| Column | Detected by keywords |
|---|---|
| Transaction Date | `tgl`, `tanggal`, `date` |
| Amount | `total`, `penjualan`, `amount`, `nilai` |
| Item Name | `nama barang`, `produk`, `item` |
| Invoice No | `invoice`, `no. invoice` |
| Customer | `pelanggan`, `customer` |
| Status | `status` |

---

## 🔧 Match Settings

Adjustable in the sidebar at runtime:

| Setting | Default | Description |
|---|---|---|
| Fuzzy Description Threshold | 85 | Min similarity score (0–100) for description matching |
| Amount Tolerance | 2% | Max % difference for fuzzy amount matching |
| Date Tolerance | 3 days | Max day difference for fuzzy date matching |

---

## 📤 Output Reports

### Excel Report (3 sheets)
- **Summary** — KPI metrics table
- **Full Comparison** — All rows, color-coded (green=exact, yellow=fuzzy, red=unmatched)
- **Unmatched** — Only the transactions needing review

### PDF Summary
- KPI cards (total, exact, fuzzy, unmatched)
- Financial amount summary + discrepancy
- Table of unmatched transactions
- Confidential footer

---

## 🔒 Security Notes

- API key is **never hardcoded** — always read from `.env` or sidebar input
- Add `.env` to `.gitignore` before committing
- The app runs fully **locally** — no data is stored externally beyond the Gemini API call
- Gemini API processes document content per-request only (no persistent storage)

---

## 🐛 Troubleshooting

| Issue | Fix |
|---|---|
| `GEMINI_API_KEY is not set` | Enter key in sidebar or add to `.env` |
| `No transactions found in PDF` | Ensure PDF is not password-protected; try a clearer scan |
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` |
| Date parsing warnings | Dates auto-detected; check your date column format |
| Amount = 0 for some rows | Check for unusual formatting like `720.000\` — fixed in parser |

---

## 📋 Requirements

- Python 3.9+
- Google Gemini API key (free tier available)
- Internet connection (for Gemini API calls)
