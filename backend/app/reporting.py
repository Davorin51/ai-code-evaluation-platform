import html
import json
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from backend.app.challenges import REGISTRY


def render_report(submission: dict, format: str) -> tuple[bytes, str]:
    if format == "json":
        return json.dumps(submission, indent=2, allow_nan=False).encode(), "application/json"
    result = submission["result"]
    title = REGISTRY[submission["challenge_id"]].title
    fields = {
        "Submission label": submission["label"],
        "Submission ID": submission["id"],
        "Challenge": title,
        "Evaluated (UTC)": submission["created_at"],
        "Source label": submission["origin"],
        "Mode": result["mode"],
        "Test pass rate": f"{result['passed']}/{result['total']} ({result['pass_rate']:.2f}%)",
        "Completed-case time": f"{result['execution_ms']:.3f} ms",
        "Ruff": f"{result['static_status']}; {len(result['static_findings'])} findings",
        "Reference verified": str(result["reference_verified"]),
        "Runtime": result["runtime"],
        "Candidate SHA-256": result["candidate_sha256"],
    }
    note = (
        "Deterministic test pass rate is not code coverage or proof of correctness. "
        "Timings are single measurements, include interpreter work and exclude container startup. "
        "Timed-out or resource-terminated cases have no completed duration. RSS includes the interpreter (Linux KiB). "
        "Hidden edge cases are revealed after evaluation for reproducible debugging."
    )
    if format == "html":

        def e(value):
            return html.escape(str(value))

        rows = "".join(f"<tr><th>{e(k)}</th><td>{e(v)}</td></tr>" for k, v in fields.items())
        cases = "".join(
            f"<section><h2>{e(case['name'])} - {e(case['status'])}</h2>"
            f"<pre>{e(json.dumps(case, indent=2))}</pre></section>"
            for case in result["cases"]
        )
        document = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Evaluation report - {e(title)}</title><style>body{{font:15px/1.65 system-ui,sans-serif;color:#142333;max-width:940px;margin:40px auto;padding:0 24px}}h1{{font-size:30px}}h2{{font-size:19px}}table{{border-collapse:collapse;width:100%}}th,td{{text-align:left;padding:9px;border-bottom:1px solid #ddd;overflow-wrap:anywhere}}th{{width:25%}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;background:#f1f4f7;padding:18px;font:12px/1.6 monospace}}section{{break-inside:avoid}}.note{{color:#475569}}</style></head><body><p>AI CODE EVALUATION PLATFORM</p><h1>{e(title)} - Evaluation report</h1><table>{rows}</table><p>{e(result["summary"])}</p><p class="note">{e(note)}</p>{cases}<h2>Static analysis findings</h2><pre>{e(json.dumps(result["static_findings"], indent=2))}</pre><h2>Candidate source</h2><pre>{e(submission["code"])}</pre><h2>Execution limits</h2><pre>{e(json.dumps(result["limits"], indent=2))}</pre></body></html>"""
        return document.encode(), "text/html"
    if format != "pdf":
        raise ValueError("Unknown report format")
    buffer = BytesIO()
    styles = getSampleStyleSheet()
    styles["Normal"].fontSize = 9
    styles["Normal"].leading = 14
    styles["BodyText"].fontSize = 9
    styles["BodyText"].leading = 14

    def para(value, style="BodyText"):
        # Escape user strings; ReportLab Paragraph markup is not user-controlled.
        return Paragraph(escape(str(value)).replace("\n", "<br/>"), styles[style])

    story = [
        para("AI CODE EVALUATION PLATFORM", "Heading3"),
        para(title + " - Evaluation report", "Title"),
    ]
    table = Table([[para(k), para(v)] for k, v in fields.items()], colWidths=[130, 360])
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor("#d9e1e9")),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    story.extend([table, Spacer(1, 14), para(result["summary"]), para(note)])
    for case in result["cases"]:
        story.extend([Spacer(1, 12), para(f"{case['name']} - {case['status']}", "Heading2")])
        for key in (
            "hidden",
            "input",
            "expected",
            "actual",
            "error",
            "duration_ms",
            "reference_duration_ms",
            "peak_rss_kib",
        ):
            value = (
                json.dumps(case[key], ensure_ascii=True)
                if isinstance(case[key], (dict, list))
                else str(case[key])
            )
            # Long source values are broken for readable wrapping, without hiding errors.
            story.append(para(f"{key}: {value}"))
    story.extend(
        [
            Spacer(1, 14),
            para("Static analysis", "Heading2"),
            para(json.dumps(result["static_findings"], indent=2)),
            para("Candidate source", "Heading2"),
            para(submission["code"]),
            para("Execution limits", "Heading2"),
            para(json.dumps(result["limits"], indent=2)),
        ]
    )

    def footer(canvas, doc):
        canvas.setFont("Helvetica", 8)
        canvas.drawString(45, 25, "Code Review Lab | Reproducible evaluation report")
        canvas.drawRightString(550, 25, f"Page {doc.page}")

    SimpleDocTemplate(
        buffer,
        title=f"{title} - Evaluation report",
        author="AI Code Evaluation Platform",
        leftMargin=45,
        rightMargin=45,
        topMargin=40,
        bottomMargin=45,
    ).build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue(), "application/pdf"
