"""Generate the two FICTIONAL sample PDFs used for demos (no real company or data).

    python scripts/make_sample_pdfs.py
"""
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

OUT = Path(__file__).resolve().parents[1] / "samples"
ss = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=ss["Title"], fontSize=20, spaceAfter=10)
H2 = ParagraphStyle("H2", parent=ss["Heading2"], spaceBefore=10, spaceAfter=6)
P = ParagraphStyle("P", parent=ss["BodyText"], fontSize=10.5, leading=15, spaceAfter=7)
NOTE = ParagraphStyle("N", parent=P, fontSize=8.5, textColor=colors.grey)


def table(rows, widths):
    t = Table(rows, colWidths=widths)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f3a5f")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5), ("GRID", (0, 0), (-1, -1), 0.4, colors.lightgrey),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
    ]))
    return t


def report():
    doc = SimpleDocTemplate(str(OUT / "aurora_robotics_fy2025_report.pdf"), pagesize=letter, title="Aurora Robotics, Inc. — Fiscal 2025 Annual Report (Excerpt)")
    s = [
        Paragraph("Aurora Robotics, Inc.", H1),
        Paragraph("Fiscal 2025 Annual Report — Excerpt", H2),
        Paragraph("FICTIONAL DOCUMENT created for software demonstration only. Aurora Robotics is not a real company and all figures are invented.", NOTE),
        Paragraph("Letter to Shareholders", H2),
        Paragraph("Fiscal 2025 was a breakout year for Aurora Robotics. Revenue grew 23.4% to $482.6 million, up from $391.2 million in fiscal 2024, driven by strong demand for our warehouse automation systems and the first full year of our recurring fleet-management software. We expanded into three new regions and signed 41 new enterprise customers, bringing our total to 318.", P),
        Paragraph("Profitability improved meaningfully. Gross margin expanded to 59.1% from 55.7% as software mix rose and manufacturing yields improved. Operating income was $61.4 million, a 12.7% operating margin, compared with $34.8 million in fiscal 2024. Net income was $48.2 million, up 77.9% from $27.1 million, and diluted earnings per share were $1.21 versus $0.70 a year earlier.", P),
        Paragraph("We continue to invest for the long term. Research and development expense was $92.5 million, or 19.2% of revenue, as we scaled our perception and motion-planning teams. We ended the year with a record order backlog of $640 million, which gives us strong visibility into fiscal 2026.", P),
        PageBreak(),
        Paragraph("Management's Discussion and Analysis", H2),
        Paragraph("Revenue. Product revenue was $356.9 million in fiscal 2025, an increase of 14.9% year over year. Software and services revenue grew 56.2% to $125.7 million and now represents 26.0% of total revenue. Revenue in North America was 54% of the total, Europe 31%, and Asia-Pacific 15%.", P),
        Paragraph("Margins and expenses. Gross profit was $285.0 million. Selling, general and administrative expense rose 9.8% to $131.1 million, below the pace of revenue growth, which produced operating leverage. We expect gross margin to remain in a range of 58% to 60% in fiscal 2026.", P),
        Paragraph("Cash flow and liquidity. Cash provided by operating activities was $73.9 million. Capital expenditures were $21.4 million, resulting in free cash flow of $52.5 million. We ended the year with cash and cash equivalents of $214.7 million and total debt of $120.0 million, which matures in 2029. We do not expect to need additional external financing to fund our plan.", P),
        PageBreak(),
        Paragraph("Consolidated Statement of Operations (US$ millions, except per-share data)", H2),
        table([
            ["", "FY2025", "FY2024", "Change"],
            ["Revenue", "482.6", "391.2", "+23.4%"],
            ["Gross profit", "285.0", "218.1", "+30.7%"],
            ["Research & development", "92.5", "78.3", "+18.1%"],
            ["Selling, general & administrative", "131.1", "119.4", "+9.8%"],
            ["Operating income", "61.4", "34.8", "+76.4%"],
            ["Net income", "48.2", "27.1", "+77.9%"],
            ["Diluted EPS ($)", "1.21", "0.70", "+72.9%"],
        ], [2.9 * inch, 1.1 * inch, 1.1 * inch, 1.1 * inch]),
        Spacer(1, 14),
        Paragraph("Selected Balance Sheet Data (US$ millions)", H2),
        table([
            ["", "Dec 31, 2025", "Dec 31, 2024"],
            ["Cash and cash equivalents", "214.7", "168.3"],
            ["Total assets", "712.3", "603.9"],
            ["Total debt", "120.0", "135.0"],
            ["Total stockholders' equity", "398.6", "331.2"],
        ], [2.9 * inch, 1.5 * inch, 1.5 * inch]),
        PageBreak(),
        Paragraph("Risk Factors (Summary)", H2),
        Paragraph("Customer concentration. Our ten largest customers accounted for 46% of revenue in fiscal 2025, and the loss of any one of them could harm our results.", P),
        Paragraph("Supply chain. We depend on a limited number of suppliers for advanced sensors and motor controllers. Shortages or tariff changes may adversely affect gross margin and our ability to deliver on backlog.", P),
        Paragraph("Competition and technology. Larger competitors may price aggressively, and rapid advances in general-purpose robotics could reduce demand for our current products.", P),
        Paragraph("Foreign exchange. About 46% of revenue is generated outside the United States; a stronger dollar would reduce reported revenue.", P),
        Paragraph("Outlook for Fiscal 2026", H2),
        Paragraph("For fiscal 2026 we expect revenue guidance of $560 million to $580 million, representing growth of 16% to 20%, and operating margin of approximately 14%. We plan capital expenditures of about $30 million and will continue to prioritize research and development, which we expect to be roughly 18% of revenue.", P),
    ]
    doc.build(s)


def paper():
    doc = SimpleDocTemplate(str(OUT / "retrieval_augmented_earnings_forecasting_paper.pdf"), pagesize=letter, title="Retrieval-Augmented Language Models for Earnings Forecasting")
    s = [
        Paragraph("Retrieval-Augmented Language Models for Earnings Forecasting", H1),
        Paragraph("FICTIONAL paper created for software demonstration only. Authors, data and results are invented.", NOTE),
        Paragraph("Abstract", H2),
        Paragraph("We study whether retrieval-augmented language models can improve analyst-style forecasts of quarterly earnings surprises. We propose EarnRAG, a method that retrieves relevant passages from prior filings and earnings-call transcripts and conditions a language model on them. On a dataset of 18,400 quarterly reports from 1,210 U.S. firms (2012-2024), EarnRAG improves directional accuracy of earnings-surprise prediction from 54.1% to 61.7% over a strong gradient-boosting baseline. However, gains concentrate in large-cap firms and vanish during the 2020 volatility regime, which we discuss as a key limitation.", P),
        Paragraph("1. Introduction", H2),
        Paragraph("Forecasting whether a firm will beat or miss consensus earnings is a central task for investors. Traditional models rely on structured features such as past surprises and analyst dispersion, but ignore the rich text in filings. Large language models can read text, yet they hallucinate figures when asked to recall facts. We hypothesize that retrieving evidence from a firm's own prior documents reduces hallucination and improves forecasts.", P),
        Paragraph("2. Method", H2),
        Paragraph("EarnRAG has three stages. First, each filing is split into 512-token passages and embedded with a dense retriever. Second, for each forecast we retrieve the top 8 passages from the firm's previous four quarters using hybrid lexical and dense search. Third, a language model is prompted with the retrieved passages and structured features and outputs a probability that the firm will beat consensus. We fine-tune the final classifier head with a cross-entropy loss and calibrate probabilities with temperature scaling.", P),
        PageBreak(),
        Paragraph("3. Experiments", H2),
        Paragraph("Data. We use 18,400 firm-quarter observations from 1,210 firms between 2012 and 2024, split chronologically: 2012-2020 for training, 2021 for validation and 2022-2024 for testing. Baselines include logistic regression on structured features, gradient boosting (XGBoost) and a zero-shot language model without retrieval.", P),
        table([
            ["Model", "Directional accuracy", "AUC", "Brier score"],
            ["Logistic regression", "52.3%", "0.538", "0.261"],
            ["Gradient boosting", "54.1%", "0.571", "0.253"],
            ["Zero-shot LLM (no retrieval)", "55.0%", "0.580", "0.255"],
            ["EarnRAG (ours)", "61.7%", "0.659", "0.236"],
        ], [2.6 * inch, 1.6 * inch, 0.9 * inch, 1.1 * inch]),
        Spacer(1, 10),
        Paragraph("Results. EarnRAG improves directional accuracy by 7.6 percentage points over gradient boosting (p &lt; 0.01, paired bootstrap). Removing retrieval drops accuracy to 55.0%, and removing structured features drops it to 58.9%, showing that both components contribute. Calibration also improves, with Brier score falling from 0.253 to 0.236.", P),
        Paragraph("4. Limitations", H2),
        Paragraph("Gains are concentrated in large-cap firms with rich disclosure: accuracy is 64.8% for the top size tercile but only 56.2% for the bottom tercile. During the 2020 volatility regime, EarnRAG's accuracy fell to 52.0%, no better than chance. Our backtest ignores transaction costs and we did not test whether the signal survives after publication. Finally, evaluation uses a single market (U.S.) and results may not transfer to other disclosure regimes.", P),
        Paragraph("5. Conclusion", H2),
        Paragraph("Retrieval grounds language models in firm-specific evidence and yields meaningful gains in earnings-surprise prediction, but the benefit is uneven across firm size and market regimes. Future work will study robustness, cost-aware trading evaluation and multilingual filings.", P),
    ]
    doc.build(s)


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    report()
    paper()
    print("wrote", *sorted(p.name for p in OUT.glob("*.pdf")))
