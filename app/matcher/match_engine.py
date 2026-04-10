"""
Transaction Matching Engine
Implements 3-level matching: Exact → Fuzzy → Unmatched
"""

import pandas as pd
import numpy as np
from app.utils.config import FUZZY_THRESHOLD, AMOUNT_TOLERANCE_PCT
from app.utils.logger import get_logger

logger = get_logger(__name__)

try:
    from rapidfuzz import fuzz as _fuzz
    def _desc_similarity(s1: str, s2: str) -> float:
        return float(_fuzz.token_set_ratio(s1, s2))
except ImportError:
    import difflib
    logger.warning("rapidfuzz not installed — falling back to difflib for string similarity")
    def _desc_similarity(s1: str, s2: str) -> float:
        return difflib.SequenceMatcher(None, s1, s2).ratio() * 100

DATE_TOLERANCE_DAYS = 3


def _amounts_match_exact(a1: float, a2: float) -> bool:
    return abs(a1 - a2) < 0.01


def _amounts_match_fuzzy(a1: float, a2: float, tolerance_pct: float) -> bool:
    if a1 == 0 and a2 == 0:
        return True
    base = max(a1, a2)
    return abs(a1 - a2) / base * 100 <= tolerance_pct


def _dates_match_exact(d1, d2) -> bool:
    if pd.isna(d1) or pd.isna(d2):
        return False
    return d1.normalize() == d2.normalize()


def _dates_match_fuzzy(d1, d2, tolerance_days: int = DATE_TOLERANCE_DAYS) -> bool:
    if pd.isna(d1) or pd.isna(d2):
        return False
    return abs((d1.normalize() - d2.normalize()).days) <= tolerance_days


def match_transactions(
    bank_df: pd.DataFrame,
    finance_df: pd.DataFrame,
    fuzzy_threshold: float = FUZZY_THRESHOLD,
    amount_tolerance_pct: float = AMOUNT_TOLERANCE_PCT,
) -> pd.DataFrame:
    """
    Compare bank and finance DataFrames.
    Returns merged DataFrame with match_status, match_confidence, notes.
    """
    logger.info(f"Matching {len(bank_df)} bank vs {len(finance_df)} finance transactions")
    results = []
    used_finance_indices = set()

    for b_idx, b_row in bank_df.iterrows():
        b_date = b_row['date']
        b_amount = b_row['amount']
        b_desc = str(b_row.get('description', ''))

        best_match = None
        best_confidence = 0.0
        best_status = 'unmatched'
        best_notes = 'No matching transaction found in finance records'
        best_f_idx = None

        for f_idx, f_row in finance_df.iterrows():
            if f_idx in used_finance_indices:
                continue

            f_date = f_row['date']
            f_amount = f_row['amount']
            f_desc = str(f_row.get('description', ''))

            date_exact = _dates_match_exact(b_date, f_date)
            date_fuzzy = _dates_match_fuzzy(b_date, f_date)
            amt_exact = _amounts_match_exact(b_amount, f_amount)
            amt_fuzzy = _amounts_match_fuzzy(b_amount, f_amount, amount_tolerance_pct)
            desc_score = _desc_similarity(b_desc, f_desc)

            # ── Level 1: Exact ───────────────────────────────────────────
            if date_exact and amt_exact:
                confidence = min(1.0, 0.70 + desc_score / 300)
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_match = f_row
                    best_status = 'exact'
                    best_notes = f'Date and amount match exactly (desc similarity: {desc_score:.0f}%)'
                    best_f_idx = f_idx

            # ── Level 2: Fuzzy ───────────────────────────────────────────
            elif best_status != 'exact':
                if date_fuzzy and amt_exact:
                    day_diff = abs((b_date.normalize() - f_date.normalize()).days) if not (pd.isna(b_date) or pd.isna(f_date)) else 99
                    confidence = max(0.4, 0.80 - day_diff * 0.05 + desc_score / 400)
                    confidence = min(confidence, 0.89)
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_match = f_row
                        best_status = 'fuzzy'
                        best_notes = f'Amount matches exactly; date off by {day_diff} day(s)'
                        best_f_idx = f_idx

                elif date_exact and amt_fuzzy and not amt_exact:
                    pct_diff = abs(b_amount - f_amount) / max(b_amount, f_amount) * 100 if max(b_amount, f_amount) > 0 else 100
                    confidence = max(0.4, 0.85 - pct_diff / 10)
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_match = f_row
                        best_status = 'fuzzy'
                        best_notes = f'Date matches; amount differs by {pct_diff:.1f}%'
                        best_f_idx = f_idx

                elif date_fuzzy and amt_fuzzy and desc_score >= fuzzy_threshold:
                    pct_diff = abs(b_amount - f_amount) / max(b_amount, f_amount) * 100 if max(b_amount, f_amount) > 0 else 100
                    day_diff = abs((b_date.normalize() - f_date.normalize()).days) if not (pd.isna(b_date) or pd.isna(f_date)) else 99
                    confidence = max(0.3, desc_score / 100 * 0.6 - pct_diff / 50 - day_diff * 0.02)
                    if confidence > 0.35 and confidence > best_confidence:
                        best_confidence = confidence
                        best_match = f_row
                        best_status = 'fuzzy'
                        best_notes = f'Partial: date±{day_diff}d, amount±{pct_diff:.1f}%, desc~{desc_score:.0f}%'
                        best_f_idx = f_idx

        row = {
            'bank_date': b_date,
            'bank_description': b_desc,
            'bank_amount': b_amount,
            'bank_type': b_row.get('type', ''),
            'finance_date': best_match['date'] if best_match is not None else pd.NaT,
            'finance_description': best_match.get('description', '') if best_match is not None else '',
            'finance_amount': best_match['amount'] if best_match is not None else 0.0,
            'finance_invoice': best_match.get('invoice', '') if best_match is not None else '',
            'finance_customer': best_match.get('customer', '') if best_match is not None else '',
            'finance_status': best_match.get('status', '') if best_match is not None else '',
            'match_status': best_status,
            'match_confidence': round(best_confidence, 3),
            'notes': best_notes,
        }
        results.append(row)
        if best_f_idx is not None and best_status in ('exact', 'fuzzy'):
            used_finance_indices.add(best_f_idx)

    # Finance-only unmatched
    for f_idx, f_row in finance_df.iterrows():
        if f_idx not in used_finance_indices:
            results.append({
                'bank_date': pd.NaT,
                'bank_description': '',
                'bank_amount': 0.0,
                'bank_type': '',
                'finance_date': f_row['date'],
                'finance_description': f_row.get('description', ''),
                'finance_amount': f_row['amount'],
                'finance_invoice': f_row.get('invoice', ''),
                'finance_customer': f_row.get('customer', ''),
                'finance_status': f_row.get('status', ''),
                'match_status': 'unmatched_finance',
                'match_confidence': 0.0,
                'notes': 'Transaction in finance records not found in bank statement',
            })

    result_df = pd.DataFrame(results)
    counts = result_df['match_status'].value_counts().to_dict()
    logger.info(f"Done: {counts}")
    return result_df


def get_summary_stats(result_df: pd.DataFrame) -> dict:
    """Compute summary statistics."""
    total = len(result_df)
    exact = len(result_df[result_df['match_status'] == 'exact'])
    fuzzy = len(result_df[result_df['match_status'] == 'fuzzy'])
    unmatched_bank = len(result_df[result_df['match_status'] == 'unmatched'])
    unmatched_finance = len(result_df[result_df['match_status'] == 'unmatched_finance'])
    matched = exact + fuzzy
    return {
        'total_records': total,
        'exact_matches': exact,
        'fuzzy_matches': fuzzy,
        'unmatched_bank': unmatched_bank,
        'unmatched_finance': unmatched_finance,
        'match_rate_pct': round(matched / total * 100, 1) if total > 0 else 0,
        'exact_rate_pct': round(exact / total * 100, 1) if total > 0 else 0,
        'total_bank_amount': result_df['bank_amount'].sum(),
        'total_finance_amount': result_df['finance_amount'].sum(),
        'amount_discrepancy': abs(result_df['bank_amount'].sum() - result_df['finance_amount'].sum()),
    }
