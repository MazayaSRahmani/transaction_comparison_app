"""
Report generation: Excel/CSV + PDF summary
"""

import io
import pandas as pd
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph,
    Spacer, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from app.utils.logger import get_logger

logger = get_logger(__name__)

# ── Color palette ─────────────────────────────────────────────────────────────
C_PRIMARY    = colors.HexColor('#1a1f36')
C_ACCENT     = colors.HexColor('#0066ff')
C_SUCCESS    = colors.HexColor('#00b386')
C_WARNING    = colors.HexColor('#f5a623')
C_DANGER     = colors.HexColor('#e63946')
C_LIGHT      = colors.HexColor('#f4f6fb')
C_MID        = colors.HexColor('#e2e8f0')
C_WHITE      = colors.white
C_TEXT       = colors.HexColor('#2d3748')


def _fmt_idr(value: float) -> str:
    return f"Rp {value:,.0f}"


def generate_excel_report(result_df: pd.DataFrame, stats: dict) -> bytes:
    """Generate Excel comparison report with multiple sheets."""
    output = io.BytesIO()

    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book

        # ── Formats ────────────────────────────────────────────────────────
        hdr_fmt = workbook.add_format({
            'bold': True, 'bg_color': '#1a1f36', 'font_color': 'white',
            'border': 1, 'align': 'center', 'valign': 'vcenter',
            'text_wrap': True, 'font_size': 10
        })
        exact_fmt = workbook.add_format({'bg_color': '#d4edda', 'border': 1, 'font_size': 9})
        fuzzy_fmt = workbook.add_format({'bg_color': '#fff3cd', 'border': 1, 'font_size': 9})
        unmatch_fmt = workbook.add_format({'bg_color': '#f8d7da', 'border': 1, 'font_size': 9})
        num_fmt = workbook.add_format({'num_format': '#,##0', 'border': 1, 'font_size': 9})
        date_fmt = workbook.add_format({'num_format': 'DD/MM/YYYY', 'border': 1, 'font_size': 9})
        title_fmt = workbook.add_format({'bold': True, 'font_size': 14, 'font_color': '#1a1f36'})
        stat_label_fmt = workbook.add_format({'bold': True, 'font_size': 11, 'bg_color': '#f4f6fb', 'border': 1})
        stat_val_fmt = workbook.add_format({'font_size': 11, 'border': 1, 'align': 'right'})

        # ── Sheet 1: Summary ───────────────────────────────────────────────
        ws = workbook.add_worksheet('Summary')
        ws.set_column('A:A', 35)
        ws.set_column('B:B', 25)
        ws.write('A1', 'TRANSACTION COMPARISON REPORT', title_fmt)
        ws.write('A2', f'Generated: {datetime.now().strftime("%d %B %Y %H:%M")}')
        ws.write_row('A4', ['Metric', 'Value'], hdr_fmt)
        summary_rows = [
            ('Total Records Processed', stats['total_records']),
            ('Exact Matches', stats['exact_matches']),
            ('Fuzzy Matches', stats['fuzzy_matches']),
            ('Unmatched (Bank only)', stats['unmatched_bank']),
            ('Unmatched (Finance only)', stats['unmatched_finance']),
            ('Match Rate', f"{stats['match_rate_pct']}%"),
            ('Total Bank Amount (IDR)', _fmt_idr(stats['total_bank_amount'])),
            ('Total Finance Amount (IDR)', _fmt_idr(stats['total_finance_amount'])),
            ('Amount Discrepancy (IDR)', _fmt_idr(stats['amount_discrepancy'])),
        ]
        for i, (label, val) in enumerate(summary_rows, start=4):
            ws.write(i, 0, label, stat_label_fmt)
            ws.write(i, 1, val, stat_val_fmt)

        # ── Sheet 2: Full Comparison ───────────────────────────────────────
        export_df = result_df.copy()
        for col in ['bank_date', 'finance_date']:
            export_df[col] = pd.to_datetime(export_df[col]).dt.strftime('%d/%m/%Y').fillna('')

        export_df.to_excel(writer, sheet_name='Full Comparison', index=False)
        ws2 = writer.sheets['Full Comparison']
        for col_num, col_name in enumerate(export_df.columns):
            ws2.write(0, col_num, col_name, hdr_fmt)
        col_widths = {
            'bank_date': 12, 'bank_description': 35, 'bank_amount': 16,
            'finance_date': 12, 'finance_description': 35, 'finance_amount': 16,
            'finance_invoice': 14, 'finance_customer': 20, 'match_status': 14,
            'match_confidence': 16, 'notes': 40,
        }
        for i, col in enumerate(export_df.columns):
            ws2.set_column(i, i, col_widths.get(col, 14))
        for row_num, row_data in export_df.iterrows():
            status = row_data.get('match_status', '')
            fmt = exact_fmt if status == 'exact' else (fuzzy_fmt if status == 'fuzzy' else unmatch_fmt)
            for col_num, val in enumerate(row_data):
                ws2.write(row_num + 1, col_num, '' if pd.isna(val) else val, fmt)

        # ── Sheet 3: Unmatched Only ────────────────────────────────────────
        unmatched = result_df[result_df['match_status'].isin(['unmatched', 'unmatched_finance'])].copy()
        for col in ['bank_date', 'finance_date']:
            unmatched[col] = pd.to_datetime(unmatched[col]).dt.strftime('%d/%m/%Y').fillna('')
        unmatched.to_excel(writer, sheet_name='Unmatched', index=False)
        ws3 = writer.sheets['Unmatched']
        for col_num, col_name in enumerate(unmatched.columns):
            ws3.write(0, col_num, col_name, hdr_fmt)

    return output.getvalue()


def generate_pdf_report(result_df: pd.DataFrame, stats: dict) -> bytes:
    """Generate a professional PDF summary report."""
    output = io.BytesIO()
    doc = SimpleDocTemplate(
        output,
        pagesize=A4,
        rightMargin=1.5*cm,
        leftMargin=1.5*cm,
        topMargin=2*cm,
        bottomMargin=1.5*cm
    )

    styles = getSampleStyleSheet()
    story = []

    # ── Title ──────────────────────────────────────────────────────────────
    title_style = ParagraphStyle('Title', fontSize=20, textColor=C_PRIMARY,
                                  spaceAfter=4, fontName='Helvetica-Bold', alignment=TA_CENTER)
    sub_style = ParagraphStyle('Sub', fontSize=10, textColor=colors.grey,
                                spaceAfter=2, alignment=TA_CENTER)
    story.append(Paragraph("Transaction Comparison Report", title_style))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%d %B %Y %H:%M WIB')}", sub_style))
    story.append(HRFlowable(width="100%", thickness=2, color=C_ACCENT))
    story.append(Spacer(1, 0.4*cm))

    # ── KPI Cards (as a table) ─────────────────────────────────────────────
    kpi_data = [
        ['TOTAL RECORDS', 'EXACT MATCHES', 'FUZZY MATCHES', 'UNMATCHED'],
        [
            str(stats['total_records']),
            str(stats['exact_matches']),
            str(stats['fuzzy_matches']),
            str(stats['unmatched_bank'] + stats['unmatched_finance'])
        ],
        ['', f"{stats['exact_rate_pct']}%", '', f"{100 - stats['match_rate_pct']:.1f}%"]
    ]
    kpi_table = Table(kpi_data, colWidths=[4*cm, 4*cm, 4*cm, 4*cm])
    kpi_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), C_PRIMARY),
        ('TEXTCOLOR', (0, 0), (-1, 0), C_WHITE),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTSIZE', (0, 1), (-1, 1), 18),
        ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (1, 1), (1, 1), C_SUCCESS),
        ('TEXTCOLOR', (2, 1), (2, 1), C_WARNING),
        ('TEXTCOLOR', (3, 1), (3, 1), C_DANGER),
        ('FONTSIZE', (0, 2), (-1, 2), 9),
        ('TEXTCOLOR', (0, 2), (-1, 2), colors.grey),
        ('BACKGROUND', (0, 1), (-1, -1), C_LIGHT),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [C_LIGHT, C_LIGHT]),
        ('BOX', (0, 0), (-1, -1), 1, C_MID),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, C_MID),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 0.5*cm))

    # ── Amount Summary ─────────────────────────────────────────────────────
    section_style = ParagraphStyle('Section', fontSize=12, textColor=C_PRIMARY,
                                    fontName='Helvetica-Bold', spaceBefore=10, spaceAfter=6)
    story.append(Paragraph("Financial Summary", section_style))

    amt_data = [
        ['', 'Amount (IDR)'],
        ['Total Bank Statement Amount', _fmt_idr(stats['total_bank_amount'])],
        ['Total Finance Record Amount', _fmt_idr(stats['total_finance_amount'])],
        ['Discrepancy', _fmt_idr(stats['amount_discrepancy'])],
        ['Match Rate', f"{stats['match_rate_pct']}%"],
    ]
    amt_table = Table(amt_data, colWidths=[10*cm, 6*cm])
    amt_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), C_ACCENT),
        ('TEXTCOLOR', (0, 0), (-1, 0), C_WHITE),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [C_WHITE, C_LIGHT]),
        ('BOX', (0, 0), (-1, -1), 1, C_MID),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, C_MID),
        ('FONTNAME', (0, -2), (-1, -1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (1, -2), (1, -2), C_DANGER),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(amt_table)
    story.append(Spacer(1, 0.5*cm))

    # ── Unmatched Transactions ─────────────────────────────────────────────
    unmatched = result_df[result_df['match_status'].isin(['unmatched', 'unmatched_finance'])]
    if len(unmatched) > 0:
        story.append(Paragraph("Transactions Requiring Attention", section_style))
        um_display = unmatched.head(20)  # max 20 rows in PDF
        table_data = [['Source', 'Date', 'Description', 'Amount (IDR)', 'Notes']]
        for _, row in um_display.iterrows():
            source = 'Bank' if row['match_status'] == 'unmatched' else 'Finance'
            date = row['bank_date'] if row['match_status'] == 'unmatched' else row['finance_date']
            desc = row['bank_description'] if row['match_status'] == 'unmatched' else row['finance_description']
            amt = row['bank_amount'] if row['match_status'] == 'unmatched' else row['finance_amount']
            date_str = date.strftime('%d/%m/%Y') if not pd.isna(date) else '-'
            table_data.append([
                source,
                date_str,
                str(desc)[:35] + ('...' if len(str(desc)) > 35 else ''),
                _fmt_idr(amt),
                str(row.get('notes', ''))[:40],
            ])
        um_table = Table(table_data, colWidths=[1.8*cm, 2.4*cm, 5*cm, 3.5*cm, 4.5*cm])
        um_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), C_DANGER),
            ('TEXTCOLOR', (0, 0), (-1, 0), C_WHITE),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [C_WHITE, colors.HexColor('#fff5f5')]),
            ('BOX', (0, 0), (-1, -1), 1, C_MID),
            ('INNERGRID', (0, 0), (-1, -1), 0.3, C_MID),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(um_table)
        if len(unmatched) > 20:
            story.append(Paragraph(
                f"<i>...and {len(unmatched) - 20} more unmatched records. See Excel report for full list.</i>",
                ParagraphStyle('note', fontSize=8, textColor=colors.grey, spaceBefore=4)
            ))

    # ── Footer ─────────────────────────────────────────────────────────────
    story.append(Spacer(1, 1*cm))
    story.append(HRFlowable(width="100%", thickness=1, color=C_MID))
    footer_style = ParagraphStyle('Footer', fontSize=8, textColor=colors.grey,
                                   alignment=TA_CENTER, spaceBefore=4)
    story.append(Paragraph(
        "Generated by Transaction Comparison AI · Confidential · Internal Use Only",
        footer_style
    ))

    doc.build(story)
    return output.getvalue()
