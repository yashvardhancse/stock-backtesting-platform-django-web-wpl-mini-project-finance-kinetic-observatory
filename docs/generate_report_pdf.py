from __future__ import annotations

import argparse
import html
import re
from pathlib import Path
from typing import Iterable
from urllib.parse import unquote

from bs4 import BeautifulSoup, NavigableString, Tag
from markdown import markdown
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    HRFlowable,
    Image,
    KeepTogether,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MARKDOWN = ROOT / "docs" / "Kinetic_Observatory_Project_Report.md"
DEFAULT_OUTPUT = ROOT / "docs" / "Kinetic_Observatory_Project_Report.pdf"


def make_styles():
    styles = getSampleStyleSheet()

    styles.add(
        ParagraphStyle(
            name="ReportTitle",
            fontName="Times-Bold",
            fontSize=20,
            leading=24,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#0f172a"),
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ReportSubtitle",
            fontName="Times-Roman",
            fontSize=12,
            leading=16,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#334155"),
            spaceAfter=14,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ReportProjectTitle",
            fontName="Times-Bold",
            fontSize=16,
            leading=20,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#111827"),
            spaceAfter=16,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ReportSectionTitle",
            fontName="Times-Bold",
            fontSize=16,
            leading=20,
            spaceBefore=10,
            spaceAfter=8,
            textColor=colors.HexColor("#0f172a"),
            keepWithNext=True,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ReportSubsectionTitle",
            fontName="Times-Bold",
            fontSize=13,
            leading=16,
            spaceBefore=8,
            spaceAfter=6,
            textColor=colors.HexColor("#111827"),
            keepWithNext=True,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ReportBody",
            fontName="Times-Roman",
            fontSize=10.4,
            leading=15,
            alignment=TA_JUSTIFY,
            spaceAfter=7,
            textColor=colors.HexColor("#111827"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="ReportBullet",
            fontName="Times-Roman",
            fontSize=10.2,
            leading=14,
            leftIndent=18,
            firstLineIndent=0,
            spaceAfter=3,
            alignment=TA_JUSTIFY,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ReportTableText",
            fontName="Times-Roman",
            fontSize=9,
            leading=11,
            alignment=TA_LEFT,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ReportCode",
            fontName="Courier",
            fontSize=8.6,
            leading=11,
            leftIndent=8,
            rightIndent=8,
            spaceBefore=4,
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ReportEquation",
            fontName="Courier",
            fontSize=10,
            leading=13,
            alignment=TA_CENTER,
            spaceBefore=4,
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ReportCaption",
            fontName="Times-Italic",
            fontSize=9,
            leading=11,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#475569"),
            spaceAfter=8,
        )
    )
    return styles


def parse_front_matter(text: str) -> dict[str, object]:
    data: dict[str, object] = {
        "doc_title": "Web Development Project Journal Paper",
        "doc_subtitle": "Comprehensive Research and Implementation Report",
        "project_title": "Kinetic Observatory: Web-Based Stock Backtesting and Visualization Platform",
        "academic_details": [],
        "student_details": [],
        "submission_date": "",
    }
    current_section = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("# "):
            data["doc_title"] = line[2:].strip()
            continue
        if line.startswith("## "):
            current_section = line[3:].strip().lower()
            continue
        if line.startswith("- "):
            item = line[2:].strip()
            if current_section == "academic details":
                cast_list(data["academic_details"]).append(item)
            elif current_section == "student and guide details":
                cast_list(data["student_details"]).append(item)
            continue
        if current_section == "project title":
            data["project_title"] = line

    for item in cast_list(data["student_details"]):
        if item.lower().startswith("submission date:"):
            data["submission_date"] = item.split(":", 1)[1].strip()
            break

    return data


def cast_list(value: object) -> list[str]:
    if isinstance(value, list):
        return value
    raise TypeError("Expected list value")


def split_front_matter(report_text: str) -> tuple[str, str]:
    separator = "\n---\n"
    if separator in report_text:
        first_split = report_text.split(separator, 1)
        return first_split[0].strip(), first_split[1].strip()
    return report_text.strip(), ""


def html_inline_text(value: str) -> str:
    value = value.replace("<strong>", "<b>").replace("</strong>", "</b>")
    value = value.replace("<em>", "<i>").replace("</em>", "</i>")
    value = re.sub(r"<code>(.*?)</code>", r"<font name='Courier'>\1</font>", value, flags=re.DOTALL)
    return value


def render_title_page(front_matter: dict[str, object], styles) -> list:
    academic_details = cast_list(front_matter["academic_details"])
    student_details = cast_list(front_matter["student_details"])
    usable_width = A4[0] - (0.8 * inch * 2)
    label_width = 2.15 * inch
    value_width = usable_width - label_width

    def detail_table(items: Iterable[str], title: str) -> Table:
        rows = [[Paragraph(f"<b>{html.escape(title)}</b>", styles["ReportBody"]), ""]]
        for item in items:
            if ":" in item:
                label, value = item.split(":", 1)
            else:
                label, value = item, ""
            rows.append(
                [
                    Paragraph(f"<b>{html.escape(label.strip())}</b>", styles["ReportBody"]),
                    Paragraph(html_inline_text(html.escape(value.strip())), styles["ReportBody"]),
                ]
            )
        table = Table(rows, colWidths=[label_width, value_width])
        table.setStyle(
            TableStyle(
                [
                    ("SPAN", (0, 0), (1, 0)),
                    ("BACKGROUND", (0, 0), (1, 0), colors.HexColor("#dbeafe")),
                    ("TEXTCOLOR", (0, 0), (1, 0), colors.HexColor("#0f172a")),
                    ("FONTNAME", (0, 0), (1, 0), "Times-Bold"),
                    ("ALIGN", (0, 0), (1, 0), "CENTER"),
                    ("GRID", (0, 0), (1, -1), 0.5, colors.HexColor("#94a3b8")),
                    ("VALIGN", (0, 0), (1, -1), "TOP"),
                    ("BACKGROUND", (0, 1), (1, -1), colors.whitesmoke),
                    ("LEADING", (0, 0), (1, -1), 12),
                    ("TOPPADDING", (0, 0), (1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (1, -1), 6),
                    ("LEFTPADDING", (0, 0), (1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (1, -1), 8),
                ]
            )
        )
        return table

    story = [
        Spacer(1, 1.05 * inch),
        Paragraph(html.escape(str(front_matter["doc_title"])), styles["ReportTitle"]),
        Paragraph(html.escape(str(front_matter["doc_subtitle"])), styles["ReportSubtitle"]),
        Spacer(1, 0.2 * inch),
        Paragraph(html.escape(str(front_matter["project_title"])), styles["ReportProjectTitle"]),
        Spacer(1, 0.2 * inch),
        detail_table(academic_details, "Academic Details"),
        Spacer(1, 0.18 * inch),
        detail_table(student_details, "Student and Guide Details"),
    ]

    if front_matter.get("submission_date"):
        story.extend(
            [
                Spacer(1, 0.18 * inch),
                Paragraph(
                    f"<b>Submission Date:</b> {html.escape(str(front_matter['submission_date']))}",
                    styles["ReportBody"],
                ),
            ]
        )
    return story


def decode_image_path(src: str, source_dir: Path) -> Path:
    src = unquote(src)
    path = (source_dir / src).resolve()
    return path


def scale_image(path: Path, max_width: float, max_height: float) -> Image:
    reader = ImageReader(str(path))
    width, height = reader.getSize()
    ratio = min(max_width / float(width), max_height / float(height), 1.0)
    return Image(str(path), width=width * ratio, height=height * ratio)


def mermaid_to_text(code: str) -> str:
    labels: list[str] = []
    for line in code.splitlines():
        line = line.strip()
        if "-->" not in line:
            continue
        parts = re.findall(r"\[(.*?)\]", line)
        for part in parts:
            if part not in labels:
                labels.append(part)
    if not labels:
        return code.strip()
    rendered: list[str] = []
    for index, label in enumerate(labels):
        rendered.append(label)
        if index < len(labels) - 1:
            rendered.append("v")
    return "\n".join(rendered)


def paragraph_from_html_text(text: str, styles, style_name: str = "ReportBody") -> Paragraph:
    cleaned = html_inline_text(text)
    cleaned = cleaned.replace("\n", "<br/>")
    return Paragraph(cleaned, styles[style_name])


def convert_table(tag: Tag, styles) -> Table:
    rows = []
    for tr in tag.find_all("tr"):
        cells = tr.find_all(["th", "td"])
        row = [Paragraph(html.escape(cell.get_text(" ", strip=True)), styles["ReportTableText"]) for cell in cells]
        if row:
            rows.append(row)
    if not rows:
        return Table([[Paragraph("", styles["ReportTableText"])]] )

    col_count = max(len(row) for row in rows)
    normalized_rows = []
    for row in rows:
        if len(row) < col_count:
            row = row + [Paragraph("", styles["ReportTableText"]) for _ in range(col_count - len(row))]
        normalized_rows.append(row)

    table = Table(normalized_rows, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dbeafe")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                ("FONTNAME", (0, 0), (-1, 0), "Times-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Times-Roman"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#94a3b8")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def build_list(tag: Tag, styles, source_dir: Path) -> ListFlowable:
    items = []
    for li in tag.find_all("li", recursive=False):
        direct_parts = []
        nested_lists = []
        for child in li.contents:
            if isinstance(child, Tag) and child.name in {"ul", "ol"}:
                nested_lists.append(child)
            else:
                direct_parts.append(str(child))

        item_flowables = []
        direct_html = "".join(direct_parts).strip()
        if direct_html:
            item_flowables.append(paragraph_from_html_text(direct_html, styles, "ReportBody"))
        for nested in nested_lists:
            item_flowables.append(build_list(nested, styles, source_dir))

        if not item_flowables:
            item_flowables.append(Paragraph("", styles["ReportBody"]))
        items.append(ListItem(item_flowables))

    return ListFlowable(
        items,
        bulletType="bullet",
        leftIndent=18,
    )


def convert_html_to_story(html_text: str, styles, source_dir: Path) -> list:
    soup = BeautifulSoup(html_text, "html.parser")
    story: list = []
    max_width = A4[0] - (1.0 * inch * 2)
    max_height = 6.6 * inch

    for element in soup.contents:
        if isinstance(element, NavigableString):
            text = str(element).strip()
            if text:
                story.append(paragraph_from_html_text(html.escape(text), styles, "ReportBody"))
            continue

        if not isinstance(element, Tag):
            continue

        name = element.name.lower()

        if name in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            level_map = {
                "h1": "ReportSectionTitle",
                "h2": "ReportSectionTitle",
                "h3": "ReportSubsectionTitle",
                "h4": "ReportSubsectionTitle",
                "h5": "ReportSubsectionTitle",
                "h6": "ReportSubsectionTitle",
            }
            story.append(Paragraph(html_inline_text(element.get_text(" ", strip=True)), styles[level_map[name]]))
            continue

        if name == "p":
            images = element.find_all("img", recursive=False)
            if images and len(element.get_text(strip=True)) == 0:
                for img_tag in images:
                    src = img_tag.get("src", "")
                    img_path = decode_image_path(src, source_dir)
                    if img_path.exists():
                        caption = img_tag.get("alt", "")
                        figure = [
                            scale_image(img_path, max_width=max_width, max_height=max_height),
                        ]
                        if caption:
                            figure.append(Spacer(1, 0.05 * inch))
                            figure.append(Paragraph(html.escape(caption), styles["ReportCaption"]))
                        story.append(KeepTogether(figure))
                        story.append(Spacer(1, 0.06 * inch))
                    else:
                        story.append(
                            Paragraph(
                                f"<font color='red'>Missing image: {html.escape(str(img_path))}</font>",
                                styles["ReportBody"],
                            )
                        )
                continue

            paragraph_text = element.decode_contents().strip()
            if paragraph_text.startswith("$$") and paragraph_text.endswith("$$"):
                equation = paragraph_text.strip("$").strip()
                story.append(Paragraph(html.escape(equation).replace("\n", "<br/>") , styles["ReportEquation"]))
            else:
                story.append(paragraph_from_html_text(paragraph_text, styles, "ReportBody"))
            continue

        if name == "ul" or name == "ol":
            story.append(build_list(element, styles, source_dir))
            story.append(Spacer(1, 0.03 * inch))
            continue

        if name == "table":
            story.append(convert_table(element, styles))
            story.append(Spacer(1, 0.1 * inch))
            continue

        if name == "hr":
            story.append(Spacer(1, 0.08 * inch))
            story.append(HRFlowable(width="100%", thickness=0.6, color=colors.HexColor("#cbd5e1")))
            story.append(Spacer(1, 0.08 * inch))
            continue

        if name == "pre":
            code = element.get_text("\n", strip=False)
            classes = element.get("class", [])
            if "language-mermaid" in classes or code.strip().startswith("flowchart"):
                mermaid_text = mermaid_to_text(code)
                flow = paragraph_from_html_text(html.escape(mermaid_text).replace("\n", "<br/>") , styles, "ReportEquation")
                box = Table([[flow]], colWidths=[max_width * 0.92])
                box.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                            ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#94a3b8")),
                            ("LEFTPADDING", (0, 0), (-1, -1), 10),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                            ("TOPPADDING", (0, 0), (-1, -1), 10),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                        ]
                    )
                )
                story.append(box)
                story.append(Spacer(1, 0.08 * inch))
            else:
                story.append(
                    Preformatted(
                        code.rstrip(),
                        styles["ReportCode"],
                        dedent=0,
                    )
                )
            continue

        if name == "div":
            inner = element.decode_contents().strip()
            if inner:
                story.extend(convert_html_to_story(inner, styles, source_dir))
            continue

    return story


def page_decorator(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 9)
    canvas.setFillColor(colors.HexColor("#475569"))
    footer_text = "Kinetic Observatory Project Report"
    canvas.drawString(doc.leftMargin, 0.55 * inch, footer_text)
    canvas.drawRightString(doc.pagesize[0] - doc.rightMargin, 0.55 * inch, f"Page {doc.page}")
    canvas.restoreState()


def build_pdf(markdown_path: Path, output_path: Path) -> None:
    report_text = markdown_path.read_text(encoding="utf-8")
    front_text, body_text = split_front_matter(report_text)
    front_matter = parse_front_matter(front_text)
    styles = make_styles()

    story = []
    story.extend(render_title_page(front_matter, styles))
    story.append(PageBreak())

    if body_text:
        html_text = markdown(
            body_text,
            extensions=["extra", "tables", "fenced_code", "sane_lists"],
            output_format="html5",
        )
        story.extend(convert_html_to_story(html_text, styles, markdown_path.parent))

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=0.8 * inch,
        rightMargin=0.8 * inch,
        topMargin=0.8 * inch,
        bottomMargin=0.8 * inch,
        title=str(front_matter.get("project_title", "Kinetic Observatory")),
        author="Copilot",
        subject="Project report",
    )
    doc.build(story, onFirstPage=page_decorator, onLaterPages=page_decorator)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the Kinetic Observatory report PDF.")
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_MARKDOWN,
        help="Path to the markdown report source.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Path to the generated PDF file.",
    )
    args = parser.parse_args()

    if not args.input.exists():
        raise FileNotFoundError(f"Markdown report not found: {args.input}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    build_pdf(args.input, args.output)
    print(f"Generated PDF: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
