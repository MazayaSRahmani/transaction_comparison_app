"""
Gemini-powered document parser.
Handles PDF (bank mutations) and Excel (finance records) via Gemini API.
Falls back to direct pandas parsing for Excel files.
"""

import io
import json
import base64
import re
import pandas as pd
import google.generativeai as genai

from app.utils.config import GEMINI_API_KEY, GEMINI_MODEL
from app.utils.logger import get_logger
from app.parser.preprocess import normalize_dataframe, clean_amount, normalize_date

logger = get_logger(__name__)

# ── Gemini setup ─────────────────────────────────────────────────────────────

def _get_client():
    if not GEMINI_API_KEY or GEMINI_API_KEY == "your_gemini_api_key_here":
        raise ValueError(
            "GEMINI_API_KEY is not set. "
            "Please add it to your .env file or enter it in the sidebar."
        )
    genai.configure(api_key=GEMINI_API_KEY)
    return genai.GenerativeModel(GEMINI_MODEL)


# ── PDF Parser ────────────────────────────────────────────────────────────────

PDF_PROMPT = """
You are a financial document parser. Extract ALL transactions from this bank mutation statement.

Return ONLY valid JSON (no markdown, no explanation) in this exact format:
{
  "transactions": [
    {
      "date": "YYYY-MM-DD",
      "description": "transaction description",
      "amount": 1234567.00,
      "type": "debit"
    }
  ],
  "account_info": {
    "account_number": "...",
    "account_name": "...",
    "period": "..."
  }
}

Rules:
- "date": ISO format YYYY-MM-DD. If day is invalid (e.g. 32), use the closest valid date.
- "amount": numeric float, no currency symbols or thousand separators
- "type": "debit" if outflow/DB, "credit" if inflow/CR
- "description": clean description text
- Extract EVERY row in the transaction table, including admin fees
- If a field is missing, use null
"""


def parse_pdf_with_gemini(file_bytes: bytes, filename: str = "bank_statement.pdf") -> pd.DataFrame:
    """Parse a bank mutation PDF using Gemini Vision."""
    logger.info(f"Parsing PDF with Gemini: {filename}")
    model = _get_client()

    pdf_part = {
        "mime_type": "application/pdf",
        "data": base64.b64encode(file_bytes).decode("utf-8")
    }

    response = model.generate_content([PDF_PROMPT, pdf_part])
    raw = response.text.strip()
    logger.debug(f"Gemini raw response (first 500 chars): {raw[:500]}")

    # Strip markdown fences if present
    raw = re.sub(r"```json\s*", "", raw)
    raw = re.sub(r"```\s*", "", raw)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {e}\nRaw: {raw[:1000]}")
        raise ValueError(f"Gemini returned invalid JSON for PDF. Error: {e}")

    transactions = data.get("transactions", [])
    if not transactions:
        raise ValueError("No transactions found in PDF. Check the document format.")

    df = pd.DataFrame(transactions)
    df['source'] = 'bank'
    df = normalize_dataframe(df)
    logger.info(f"Parsed {len(df)} transactions from PDF")
    return df


# ── Excel Parser ──────────────────────────────────────────────────────────────

EXCEL_PROMPT = """
You are a financial data extraction assistant. I will provide an Excel file content.
Extract all transaction records and return ONLY valid JSON (no markdown):

{
  "transactions": [
    {
      "date": "YYYY-MM-DD",
      "description": "item/product description or customer name",
      "amount": 1234567.00,
      "type": "credit",
      "invoice": "INV/...",
      "customer": "customer name",
      "status": "Lunas/Piutang/Free/Promo"
    }
  ]
}

Rules:
- "amount": the total transaction value as a plain float
- "type": use "credit" for sales/income, "debit" for expenses/purchases
- Combine product name and customer into description if helpful
- "date": ISO format YYYY-MM-DD
- Include ALL rows
"""


def parse_excel_direct(file_bytes: bytes) -> pd.DataFrame:
    """
    Direct pandas parsing of the finance Excel file.
    Handles the known schema: Tgl Transaksi, Nama Barang, Total Penjualan (Rp), etc.
    """
    logger.info("Parsing Excel with direct pandas parser")
    xls = pd.read_excel(io.BytesIO(file_bytes), sheet_name=None)

    all_dfs = []
    for sheet_name, df in xls.items():
        logger.info(f"Processing sheet: {sheet_name}, columns: {list(df.columns)}")

        # Map known column names (flexible)
        col_map = {}
        for col in df.columns:
            cl = str(col).lower().strip()
            if any(k in cl for k in ['tgl', 'tanggal', 'date']):
                col_map['date'] = col
            elif any(k in cl for k in ['total', 'amount', 'nilai', 'harga total', 'penjualan']):
                col_map['amount'] = col
            elif any(k in cl for k in ['nama barang', 'item', 'produk', 'keterangan', 'description']):
                col_map['description'] = col
            elif any(k in cl for k in ['invoice', 'no. invoice', 'no invoice']):
                col_map['invoice'] = col
            elif any(k in cl for k in ['pelanggan', 'customer', 'nama pelanggan']):
                col_map['customer'] = col
            elif any(k in cl for k in ['status']):
                col_map['status'] = col

        if 'date' not in col_map or 'amount' not in col_map:
            logger.warning(f"Sheet '{sheet_name}' missing required columns, skipping.")
            continue

        sheet_df = pd.DataFrame()
        sheet_df['date'] = df[col_map['date']].apply(normalize_date)
        sheet_df['amount'] = df[col_map['amount']].apply(clean_amount)

        # Build description
        desc_parts = []
        if 'description' in col_map:
            desc_parts.append(df[col_map['description']].astype(str))
        if 'customer' in col_map:
            desc_parts.append(df[col_map['customer']].astype(str))
        if desc_parts:
            sheet_df['description'] = desc_parts[0] if len(desc_parts) == 1 else desc_parts[0] + ' - ' + desc_parts[1]
        else:
            sheet_df['description'] = 'finance record'

        sheet_df['type'] = 'credit'  # sales records
        sheet_df['invoice'] = df[col_map['invoice']].astype(str) if 'invoice' in col_map else ''
        sheet_df['customer'] = df[col_map['customer']].astype(str) if 'customer' in col_map else ''
        sheet_df['status'] = df[col_map['status']].astype(str) if 'status' in col_map else ''
        sheet_df['source'] = 'finance'
        all_dfs.append(sheet_df)

    if not all_dfs:
        raise ValueError("No valid sheets found in Excel file.")

    result = pd.concat(all_dfs, ignore_index=True)
    result = normalize_dataframe(result)
    logger.info(f"Parsed {len(result)} transactions from Excel (direct)")
    return result


def parse_excel_with_gemini(file_bytes: bytes, filename: str = "finance.xlsx") -> pd.DataFrame:
    """Try Gemini first for Excel; fall back to direct pandas if needed."""
    logger.info(f"Parsing Excel with Gemini: {filename}")
    try:
        model = _get_client()
        # Read sheets as text for Gemini context
        xls = pd.read_excel(io.BytesIO(file_bytes), sheet_name=None)
        sheet_texts = []
        for sheet_name, df in xls.items():
            sheet_texts.append(f"Sheet: {sheet_name}\n{df.to_csv(index=False)}")
        combined_text = "\n\n".join(sheet_texts)

        prompt = EXCEL_PROMPT + f"\n\nHere is the Excel content as CSV:\n\n{combined_text}"
        response = model.generate_content(prompt)
        raw = response.text.strip()
        raw = re.sub(r"```json\s*", "", raw)
        raw = re.sub(r"```\s*", "", raw)

        data = json.loads(raw)
        transactions = data.get("transactions", [])
        if not transactions:
            raise ValueError("Empty transactions from Gemini")

        df = pd.DataFrame(transactions)
        df['source'] = 'finance'
        if 'status' not in df.columns:
            df['status'] = ''
        if 'invoice' not in df.columns:
            df['invoice'] = ''
        if 'customer' not in df.columns:
            df['customer'] = ''
        df = normalize_dataframe(df)
        logger.info(f"Parsed {len(df)} transactions from Excel via Gemini")
        return df

    except Exception as e:
        logger.warning(f"Gemini Excel parse failed ({e}), falling back to direct parser")
        return parse_excel_direct(file_bytes)


# ── Dispatch ──────────────────────────────────────────────────────────────────

def parse_document(file_bytes: bytes, filename: str, doc_type: str) -> pd.DataFrame:
    """
    Main entry point.
    doc_type: 'bank' (PDF/Excel bank statement) or 'finance' (Excel finance record)
    """
    ext = filename.lower().split('.')[-1]

    if doc_type == 'bank':
        if ext == 'pdf':
            return parse_pdf_with_gemini(file_bytes, filename)
        else:
            # Bank Excel: use Gemini with fallback
            df = parse_excel_with_gemini(file_bytes, filename)
            df['source'] = 'bank'
            return df
    else:  # finance
        return parse_excel_with_gemini(file_bytes, filename)
