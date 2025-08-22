from datetime import datetime
from fpdf import FPDF
from typing import Optional
from io import BytesIO

APP_TITLE = "AI Stock Risk & VaR Suite"

DISCLAIMER = (
    "Disclaimer: This report is generated for educational purposes only and does not constitute "
    "investment advice. Historical performance and risk metrics (VaR / CVaR) are not guarantees "
    "of future results. Use alongside independent research and judgment."
)

# -------------------------------------------------
# Helper: Robust conversion to bytes across fpdf2 versions
# -------------------------------------------------
def _pdf_bytes(pdf: FPDF) -> bytes:
    """
    fpdf2 historically returned a latin-1 str for output(dest='S'),
    but newer versions may return a bytearray. This normalizes to bytes.
    """
    raw = pdf.output(dest="S")
    if isinstance(raw, (bytes, bytearray)):
        return bytes(raw)
    # Fallback: encode string (should already be latin-1 safe)
    return raw.encode("latin-1", "ignore")


# -------------------------------------------------
# Sanitization for core Helvetica (Latin-1 only)
# -------------------------------------------------
def _sanitize(text) -> str:
    if not isinstance(text, str):
        text = str(text)
    replacements = {
        "₹": "INR ",
        "–": "-",
        "—": "-",
        "’": "'",
        "‘": "'",
        "“": '"',
        "”": '"',
        "•": "-",
        "→": "->",
        "↔": "<->",
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return "".join(ch if 32 <= ord(ch) <= 255 else "?" for ch in text)


class ReportPDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(40, 42, 48)
        self.cell(0, 8, APP_TITLE, 0, 1, "L")
        self.set_draw_color(200, 200, 200)
        self.set_line_width(0.3)
        y = self.get_y()
        self.line(self.l_margin, y, self.w - self.r_margin, y)
        self.ln(4)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 125)
        self.cell(
            0,
            6,
            f"Generated {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}  |  Page {self.page_no()}",
            0,
            0,
            "R",
        )


def _section(pdf: FPDF, title: str):
    pdf.set_text_color(25, 25, 30)
    pdf.set_font("Helvetica", "B", 11)
    pdf.ln(1)
    pdf.cell(0, 7, _sanitize(title), 0, 1)
    pdf.set_draw_color(220, 220, 220)
    pdf.set_line_width(0.2)
    y = pdf.get_y()
    pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
    pdf.ln(2)


def _kv_table(
    pdf: FPDF,
    rows,
    key_width: float = 55,
    gap: float = 3,
    line_height: float = 6,
    min_value_width: float = 30,
    font_name: str = "Helvetica",
    font_size: int = 9,
):
    """
    Fixed two-column key/value renderer that avoids the FPDFException
    "Not enough horizontal space to render a single character" by:
      - Restarting each row at left margin
      - Using explicit (bounded) widths
      - Wrapping values with MultiCell
    """
    pdf.set_font(font_name, "", font_size)
    pdf.set_text_color(50, 50, 55)
    effective_width = pdf.w - pdf.l_margin - pdf.r_margin

    if key_width > effective_width - min_value_width - gap:
        key_width = max(effective_width * 0.35, effective_width - min_value_width - gap)

    value_width = effective_width - key_width - gap
    if value_width < min_value_width:
        value_width = max(min_value_width, effective_width * 0.5)
        key_width = effective_width - value_width - gap

    for k, v in rows:
        key_txt = _sanitize(f"{k}:")
        val_txt = _sanitize(v)
        pdf.set_x(pdf.l_margin)
        pdf.cell(key_width, line_height, key_txt, 0, 0)
        pdf.set_x(pdf.l_margin + key_width + gap)
        pdf.multi_cell(value_width, line_height, val_txt, 0, "L")


# ----------------- Assessment PDF -----------------
def generate_assessment_pdf(data: dict) -> bytes:
    pdf = ReportPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 15)
    pdf.set_text_color(25, 25, 30)
    pdf.cell(0, 9, _sanitize(f"Assessment Report: {data['company']} ({data['ticker']})"), 0, 1)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(90, 90, 95)
    pdf.cell(
        0,
        6,
        f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}  |  Confidence: {data['confidence_percent']:.0f}%",
        0,
        1,
    )

    _section(pdf, "Summary")
    _kv_table(pdf, [
        ("Company", data["company"]),
        ("Ticker", data["ticker"]),
        ("Sector", data["sector"]),
        ("Suggested Action", data["action"]),
        ("Risk Score", f"{data['risk_score']:.2f} ({data['risk_level']})"),
        ("Confidence", f"{data['confidence_percent']:.0f}%"),
        ("Investment (INR)", f"{data['investment_amount']:,.2f}"),
    ])

    _section(pdf, "Factors")
    _kv_table(pdf, [
        ("Debt / Equity", f"{data['de_ratio']:.2f}"),
        ("Earnings Volatility", f"{data['earnings_vol']:.2f}"),
        ("Sector Beta", f"{data['sector_beta']:.2f}"),
        ("Sector Risk (norm)", data["sector_risk"].title()),
        ("Macro Risk (scaled)", f"{data['macro_risk']:.2f}"),
    ])

    _section(pdf, f"Statistical Loss ({data['cl_label']})")
    _kv_table(pdf, [
        ("VaR", f"{data['var_pct']:.2%} ({data['var_amount']:,.2f} INR)"),
        ("CVaR", f"{data['cvar_pct']:.2%} ({data['cvar_amount']:,.2f} INR)"),
        ("Method", "Historical (empirical)"),
    ])

    _section(pdf, "Notes")
    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_text_color(65, 65, 70)
    pdf.multi_cell(
        0,
        5,
        _sanitize(
            "VaR is the loss threshold not exceeded at the chosen confidence level. "
            "CVaR (Expected Shortfall) is the mean loss beyond that threshold. Metrics rely on historical daily returns "
            "and do not capture structural breaks or future regime shifts."
        ),
    )

    _section(pdf, "Disclaimer")
    pdf.set_font("Helvetica", "I", 7.5)
    pdf.set_text_color(110, 110, 115)
    pdf.multi_cell(0, 4.5, _sanitize(DISCLAIMER))

    return _pdf_bytes(pdf)


# ----------------- Portfolio PDF -----------------
def generate_portfolio_pdf(data: dict, allocation_chart: Optional[bytes] = None) -> bytes:
    pdf = ReportPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 15)
    pdf.set_text_color(25, 25, 30)
    pdf.cell(0, 9, "Portfolio Risk Report", 0, 1)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(90, 90, 95)
    pdf.cell(0, 6, f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", 0, 1)

    _section(pdf, "Summary")
    s = data["summary"]
    _kv_table(pdf, [
        ("Tickers", s["num_tickers"]),
        ("Risk Score", f"{s['risk_score']:.2f} ({s['risk_level']})"),
        ("Confidence", f"{s['confidence']:.0f}%"),
        ("Macro Risk", f"{s['macro_risk']:.2f}"),
        ("Suggested Action", s["action"]),
    ])

    if allocation_chart:
        _section(pdf, "Allocation (Pie Chart)")
        try:
            pdf.image(stream=BytesIO(allocation_chart), type="PNG", w=90)
        except Exception:
            pdf.set_font("Helvetica", "I", 8)
            pdf.set_text_color(180, 50, 50)
            pdf.cell(0, 6, "Chart embedding failed.", 0, 1)

    _section(pdf, "Weighted Factor Averages")
    f = data["factors"]
    _kv_table(pdf, [
        ("Avg D/E", f"{f['avg_de']:.2f}"),
        ("Avg Earnings Vol", f"{f['avg_ev']:.2f}"),
        ("Avg Beta", f"{f['avg_beta']:.2f}"),
        ("Avg Data Confidence", f"{f['avg_conf']:.2f}"),
    ])

    _section(pdf, f"Portfolio Statistical Loss ({data['var']['cl_label']})")
    v = data["var"]
    _kv_table(pdf, [
        ("VaR", f"{v['var_pct']:.2%}"),
        ("CVaR", f"{v['cvar_pct']:.2%}"),
        ("Daily Volatility", f"{v['vol']:.2%}"),
        ("Tail Probability", f"{v['tail_prob']:.2%}"),
        ("Method", "Historical (linear aggregation)"),
    ])

    _section(pdf, "Per-Ticker Factors")
    pdf.set_font("Helvetica", "B", 7.2)
    headers = ["Ticker", "W%", "Risk", "D/E", "EarnVol", "Beta", "SecR"]
    widths = [22, 12, 14, 14, 20, 14, 14]
    for h, w in zip(headers, widths):
        pdf.cell(w, 6, _sanitize(h), 0, 0)
    pdf.ln(6)
    pdf.set_font("Helvetica", "", 7)
    for row in data["portfolio"]:
        pdf.cell(widths[0], 5, _sanitize(row["Ticker"][:8]), 0, 0)
        pdf.cell(widths[1], 5, f"{row['Weight']*100:,.1f}", 0, 0, "R")
        pdf.cell(widths[2], 5, f"{row['RiskScore']:.2f}", 0, 0, "R")
        pdf.cell(widths[3], 5, f"{row['D/E']:.2f}", 0, 0, "R")
        pdf.cell(widths[4], 5, f"{row['EarnVol']:.2f}", 0, 0, "R")
        beta_disp = f"{row['Beta']:.2f}" if row['Beta'] == row['Beta'] else "-"
        pdf.cell(widths[5], 5, beta_disp, 0, 0, "R")
        pdf.cell(widths[6], 5, _sanitize(row["SectorRisk"][:5]), 0, 1, "R")

    if data.get("variance"):
        _section(pdf, "Variance Contributions")
        pdf.set_font("Helvetica", "B", 7.2)
        h2 = ["Ticker", "Weight%", "Vol%"]
        w2 = [30, 22, 22]
        for h, w in zip(h2, w2):
            pdf.cell(w, 6, _sanitize(h), 0, 0)
        pdf.ln(6)
        pdf.set_font("Helvetica", "", 7)
        for row in data["variance"]:
            pdf.cell(w2[0], 5, _sanitize(row["Ticker"][:10]), 0, 0)
            pdf.cell(w2[1], 5, f"{row['Weight%']:.2f}", 0, 0, "R")
            pdf.cell(w2[2], 5, f"{row['PctTotalVol%']:.2f}", 0, 1, "R")

    _section(pdf, "Disclaimer")
    pdf.set_font("Helvetica", "I", 7.5)
    pdf.set_text_color(110, 110, 115)
    pdf.multi_cell(0, 4.5, _sanitize(DISCLAIMER))

    return _pdf_bytes(pdf)


# ----------------- Combined PDF -----------------
def generate_combined_pdf(
    assessment: Optional[dict],
    portfolio: Optional[dict],
    allocation_chart: Optional[bytes] = None
) -> bytes:
    pdf = ReportPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(25, 25, 30)
    pdf.cell(0, 10, "Combined Risk Report", 0, 1)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(90, 90, 95)
    pdf.cell(0, 6, f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", 0, 1)

    if assessment:
        _section(pdf, f"Assessment: {assessment['company']} ({assessment['ticker']})")
        _kv_table(pdf, [
            ("Risk Score", f"{assessment['risk_score']:.2f} ({assessment['risk_level']})"),
            ("Action", assessment["action"]),
            ("Confidence", f"{assessment['confidence_percent']:.0f}%"),
            ("Debt / Equity", f"{assessment['de_ratio']:.2f}"),
            ("Earnings Volatility", f"{assessment['earnings_vol']:.2f}"),
            ("Sector Beta", f"{assessment['sector_beta']:.2f}"),
            ("Sector Risk", assessment["sector_risk"].title()),
            ("Macro Risk", f"{assessment['macro_risk']:.2f}"),
            ("VaR", f"{assessment['var_pct']:.2%} ({assessment['var_amount']:,.2f} INR)"),
            ("CVaR", f"{assessment['cvar_pct']:.2%} ({assessment['cvar_amount']:,.2f} INR)"),
        ])
    else:
        _section(pdf, "Assessment Section")
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(140, 60, 60)
        pdf.cell(0, 6, "No single-stock assessment data supplied.", 0, 1)

    if portfolio:
        pdf.add_page()
        _section(pdf, "Portfolio Summary")
        s = portfolio["summary"]
        _kv_table(pdf, [
            ("Tickers", s["num_tickers"]),
            ("Risk Score", f"{s['risk_score']:.2f} ({s['risk_level']})"),
            ("Action", s["action"]),
            ("Confidence", f"{s['confidence']:.0f}%"),
            ("Macro Risk", f"{s['macro_risk']:.2f}"),
        ])

        if allocation_chart:
            _section(pdf, "Allocation Pie Chart")
            try:
                pdf.image(stream=BytesIO(allocation_chart), type="PNG", w=100)
            except Exception:
                pdf.set_font("Helvetica", "I", 8)
                pdf.set_text_color(180, 50, 50)
                pdf.cell(0, 6, "Chart embedding failed.", 0, 1)

        _section(pdf, "Weighted Factor Averages")
        f = portfolio["factors"]
        _kv_table(pdf, [
            ("Avg D/E", f"{f['avg_de']:.2f}"),
            ("Avg Earnings Vol", f"{f['avg_ev']:.2f}"),
            ("Avg Beta", f"{f['avg_beta']:.2f}"),
            ("Avg Data Confidence", f"{f['avg_conf']:.2f}"),
        ])

        _section(pdf, f"Portfolio Statistical Loss ({portfolio['var']['cl_label']})")
        v = portfolio["var"]
        _kv_table(pdf, [
            ("VaR", f"{v['var_pct']:.2%}"),
            ("CVaR", f"{v['cvar_pct']:.2%}"),
            ("Daily Volatility", f"{v['vol']:.2%}"),
            ("Tail Probability", f"{v['tail_prob']:.2%}"),
            ("Method", "Historical"),
        ])

        _section(pdf, "Per-Ticker Factors (Abbrev)")
        pdf.set_font("Helvetica", "B", 7.2)
        headers = ["Ticker", "W%", "Risk", "D/E", "Vol", "Beta"]
        widths = [24, 12, 14, 14, 14, 14]
        for h, w in zip(headers, widths):
            pdf.cell(w, 6, _sanitize(h), 0, 0)
        pdf.ln(6)
        pdf.set_font("Helvetica", "", 7)
        for row in portfolio["portfolio"]:
            pdf.cell(widths[0], 5, _sanitize(row["Ticker"][:8]), 0, 0)
            pdf.cell(widths[1], 5, f"{row['Weight']*100:,.1f}", 0, 0, "R")
            pdf.cell(widths[2], 5, f"{row['RiskScore']:.2f}", 0, 0, "R")
            pdf.cell(widths[3], 5, f"{row['D/E']:.2f}", 0, 0, "R")
            pdf.cell(widths[4], 5, f"{row['EarnVol']:.2f}", 0, 0, "R")
            pdf.cell(widths[5], 5, f"{row['Beta']:.2f}" if row['Beta'] == row['Beta'] else "-", 0, 1, "R")
    else:
        pdf.add_page()
        _section(pdf, "Portfolio Section")
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(140, 60, 60)
        pdf.cell(0, 6, "No portfolio data supplied.", 0, 1)

    pdf.add_page()
    _section(pdf, "Disclaimer")
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(110, 110, 115)
    pdf.multi_cell(0, 4.5, _sanitize(DISCLAIMER))

    return _pdf_bytes(pdf)