from html import escape
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph


SOURCE = Path(r"C:\dev\hpo-ptbr-lab\output\Contabilidade - Revisão Cumulativa - Contas, Atos e Fatos Contábeis.docx")
OUTPUT = Path(r"C:\dev\hpo-ptbr-lab\tmp\aula04_20260911\docx_qa_preview.html")


def blocks(doc):
    for child in doc.element.body.iterchildren():
        if child.tag == qn("w:p"):
            yield Paragraph(child, doc)
        elif child.tag == qn("w:tbl"):
            yield Table(child, doc)


def paragraph_html(paragraph: Paragraph) -> str:
    text = escape(paragraph.text)
    style = paragraph.style.name if paragraph.style else "Normal"
    p_pr = paragraph._p.pPr
    page_break = p_pr is not None and p_pr.find(qn("w:pageBreakBefore")) is not None
    break_class = " page-break" if page_break else ""
    if style == "Title":
        return f'<h1 class="title{break_class}">{text}</h1>'
    if style == "Subtitle":
        return f'<p class="subtitle{break_class}">{text}</p>'
    if style.startswith("Heading 1"):
        return f'<h1 class="h1{break_class}">{text}</h1>'
    if style.startswith("Heading 2"):
        return f'<h2 class="h2{break_class}">{text}</h2>'
    if style.startswith("Heading 3"):
        return f'<h3 class="h3{break_class}">{text}</h3>'
    is_bullet = p_pr is not None and p_pr.numPr is not None
    if not text:
        return '<div class="spacer"></div>'
    if is_bullet:
        return f'<p class="bullet{break_class}">• {text}</p>'
    return f'<p class="body{break_class}">{text}</p>'


def table_html(table: Table) -> str:
    rows = []
    for row_index, row in enumerate(table.rows):
        cells = []
        tag = "th" if row_index == 0 else "td"
        for cell in row.cells:
            value = "<br>".join(escape(p.text) for p in cell.paragraphs)
            cells.append(f"<{tag}>{value}</{tag}>")
        rows.append("<tr>" + "".join(cells) + "</tr>")
    return '<table><thead>' + rows[0] + "</thead><tbody>" + "".join(rows[1:]) + "</tbody></table>"


doc = Document(SOURCE)
content = []
for block in blocks(doc):
    content.append(paragraph_html(block) if isinstance(block, Paragraph) else table_html(block))

html = """<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><style>
@page { size: Letter; margin: 1in; }
* { box-sizing: border-box; }
body { margin: 0; font-family: Arial, sans-serif; color: #202124; font-size: 11pt; line-height: 1.28; }
.title { font-size: 24pt; margin: 0 0 8pt; color: #000; }
.subtitle { color: #5f6368; font-size: 12pt; margin: 0 0 18pt; }
.h1 { color: #000; font-size: 18pt; margin: 18pt 0 8pt; page-break-after: avoid; }
.h2 { color: #000; font-size: 14pt; margin: 14pt 0 6pt; page-break-after: avoid; }
.h3 { color: #000; font-size: 12pt; margin: 10pt 0 4pt; page-break-after: avoid; }
.body, .bullet { margin: 0 0 6pt; }
.bullet { padding-left: 14pt; text-indent: -10pt; }
.spacer { height: 5pt; }
.page-break { break-before: page; }
table { width: 100%; border-collapse: collapse; table-layout: fixed; margin: 7pt 0 10pt; font-size: 9.5pt; break-inside: auto; }
thead { display: table-header-group; }
tr { break-inside: avoid; }
th, td { border: 1px solid #d9d9d9; padding: 6pt 7pt; vertical-align: middle; text-align: left; overflow-wrap: anywhere; }
th:first-child, td:first-child { width: 31%; }
th { background: #4b3ca7; color: #fff; font-weight: 700; }
tbody tr:nth-child(even) { background: #f6f5fb; }
</style></head><body>""" + "\n".join(content) + "</body></html>"
OUTPUT.write_text(html, encoding="utf-8")
print(OUTPUT)
