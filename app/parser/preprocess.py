import pandas as pd
import numpy as np
import re
from app.utils.logger import get_logger

logger = get_logger(__name__)


def clean_amount(value) -> float:
    """Convert various IDR amount formats to float."""
    if pd.isna(value):
        return 0.0
    s = str(value).strip()
    s = re.sub(r'[Rp\s]', '', s)
    # Strip trailing non-numeric junk (e.g. backslash in "720.000\")
    s = re.sub(r'[^\d.,]+$', '', s)

    dot_count = s.count('.')
    comma_count = s.count(',')

    if dot_count > 1:
        s = s.replace('.', '').replace(',', '.')
    elif dot_count == 1 and comma_count == 1:
        if s.index(',') < s.index('.'):
            s = s.replace(',', '')
        else:
            s = s.replace('.', '').replace(',', '.')
    elif comma_count >= 1 and dot_count == 0:
        parts = s.split(',')
        if len(parts) > 2 or (len(parts) == 2 and len(parts[-1]) == 3):
            s = s.replace(',', '')
        else:
            s = s.replace(',', '.')
    elif dot_count == 1 and comma_count == 0:
        parts = s.split('.')
        after_dot = re.sub(r'[^\d]', '', parts[1]) if len(parts) > 1 else ''
        if len(after_dot) == 3:
            s = re.sub(r'[^\d]', '', s)

    s = re.sub(r'[^\d.]', '', s)
    parts = s.split('.')
    if len(parts) > 2:
        s = ''.join(parts[:-1]) + '.' + parts[-1]

    try:
        return float(s) if s else 0.0
    except ValueError:
        logger.warning(f"Could not parse amount: '{value}' -> '{s}'")
        return 0.0


def normalize_date(value) -> pd.Timestamp:
    """Parse various date formats to pandas Timestamp."""
    if pd.isna(value):
        return pd.NaT
    if isinstance(value, pd.Timestamp):
        return value
    if isinstance(value, (int, float)):
        try:
            return pd.Timestamp('1899-12-30') + pd.Timedelta(days=int(value))
        except Exception:
            pass
    s = str(value).strip()
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%m/%d/%Y', '%d %B %Y', '%d %b %Y'):
        try:
            return pd.to_datetime(s, format=fmt)
        except Exception:
            continue
    try:
        return pd.to_datetime(s, dayfirst=True)
    except Exception:
        logger.warning(f"Could not parse date: {value!r}")
        return pd.NaT


def normalize_text(value) -> str:
    """Lowercase, strip, remove extra spaces."""
    if not isinstance(value, str):
        value = str(value) if not pd.isna(value) else ''
    return re.sub(r'\s+', ' ', value.lower().strip())


def normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure standard schema and clean all columns."""
    df = df.copy()
    if 'date' in df.columns:
        df['date'] = df['date'].apply(normalize_date)
    if 'amount' in df.columns:
        df['amount'] = df['amount'].apply(clean_amount)
    if 'description' in df.columns:
        df['description'] = df['description'].apply(normalize_text)
    df = df.dropna(subset=['date', 'amount'], how='all')
    df = df[df['amount'] > 0]
    df = df.reset_index(drop=True)
    return df
