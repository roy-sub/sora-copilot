"""Two renderers, one content path.

The dossier is the artefact that reaches an authority, and an operator may want it as
DOCX (to edit alongside the authority's own forms) or as PDF (to file). Writing those as
two documents would be an invitation for them to drift — and a PDF whose SAIL does not
match the DOCX's is the single worst bug this product could ship.

So ``dossier.py`` describes the document once, against the ``Writer`` protocol below,
and a backend turns those calls into a `.docx` or a `.pdf`. Neither backend decides what
goes in the document; both are told. A test renders both from the same input and asserts
the values match.

The vocabulary is deliberately small — headings, paragraphs, bullets, key/value tables,
grid tables, notes, images, page breaks. Anything richer would start to encode layout in
the content path, which is where drift begins.
"""

from __future__ import annotations

import html
from io import BytesIO
from typing import Any, Protocol

from docx import Document as new_document
from docx.document import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

INK = RGBColor(0x1A, 0x1A, 0x1A)
MUTED = RGBColor(0x5A, 0x60, 0x66)
WARN = RGBColor(0x8A, 0x52, 0x10)

#: Hex equivalents, for the HTML backend. Kept beside the DOCX colours so the two
#: documents cannot end up looking like different products.
INK_HEX = "#1a1a1a"
MUTED_HEX = "#5a6066"
WARN_HEX = "#8a5210"


class Writer(Protocol):
    """Everything the dossier is allowed to put in a document."""

    def title(self, text: str, subtitle: str | None = None) -> None: ...
    def heading(self, text: str, level: int = 1) -> None: ...
    def paragraph(self, text: str) -> None: ...
    def bullet(self, text: str) -> None: ...
    def note(self, text: str) -> None: ...
    def warning(self, text: str) -> None: ...
    def kv_table(self, rows: list[tuple[str, str]]) -> None: ...
    def table(self, headers: list[str], rows: list[list[str]]) -> None: ...
    def image(self, png: bytes, width_cm: float) -> None: ...
    def page_break(self) -> None: ...
    #: A bullet whose first phrase is emphasised, as "12 m — the rule that produced it".
    def lead_bullet(self, lead: str, rest: str) -> None: ...
    def render(self) -> bytes: ...


# ------------------------------------------------------------------ DOCX


class DocxWriter:
    """python-docx. The format an operator edits."""

    def __init__(self, *, disclaimer: str, stamp: str, banner: str | None) -> None:
        self._disclaimer = disclaimer
        self._stamp = stamp
        self._banner = banner
        self.document: Document = new_document()
        self._style()
        section = self.document.sections[0]
        section.top_margin = Cm(2.6)
        section.bottom_margin = Cm(2.0)
        section.left_margin = Cm(2.2)
        section.right_margin = Cm(2.2)

    def _style(self) -> None:
        normal = self.document.styles["Normal"]
        normal.font.name = "Calibri"
        normal.font.size = Pt(10.5)
        normal.font.color.rgb = INK
        # East-Asian font name too, or Word substitutes its own for some glyphs.
        normal.element.rPr.rFonts.set(qn("w:eastAsia"), "Calibri")
        normal.paragraph_format.space_after = Pt(6)
        normal.paragraph_format.line_spacing = 1.15

    def title(self, text: str, subtitle: str | None = None) -> None:
        paragraph = self.document.add_paragraph()
        paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
        run = paragraph.add_run(text)
        run.bold = True
        run.font.size = Pt(22)
        if subtitle:
            second = self.document.add_paragraph()
            run = second.add_run(subtitle)
            run.font.size = Pt(14)
            run.font.color.rgb = MUTED
        self.document.add_paragraph()

    def heading(self, text: str, level: int = 1) -> None:
        heading = self.document.add_heading(text, level=level)
        for run in heading.runs:
            run.font.color.rgb = INK
            run.font.name = "Calibri"

    def paragraph(self, text: str) -> None:
        self.document.add_paragraph(text)

    def bullet(self, text: str) -> None:
        self.document.add_paragraph(text, style="List Bullet")

    def lead_bullet(self, lead: str, rest: str) -> None:
        paragraph = self.document.add_paragraph(style="List Bullet")
        paragraph.add_run(lead).bold = True
        paragraph.add_run(rest)

    def note(self, text: str) -> None:
        paragraph = self.document.add_paragraph()
        run = paragraph.add_run(text)
        run.font.size = Pt(8.5)
        run.font.color.rgb = MUTED

    def warning(self, text: str) -> None:
        paragraph = self.document.add_paragraph()
        run = paragraph.add_run(text)
        run.bold = True
        run.font.color.rgb = WARN

    def kv_table(self, rows: list[tuple[str, str]]) -> None:
        table = self.document.add_table(rows=0, cols=2)
        table.style = "Light Grid Accent 1"
        table.alignment = WD_TABLE_ALIGNMENT.LEFT
        for key, value in rows:
            cells = table.add_row().cells
            cells[0].text = key
            cells[1].text = value
            for paragraph in cells[0].paragraphs:
                for run in paragraph.runs:
                    run.bold = True
        table.columns[0].width = Cm(6.5)
        table.columns[1].width = Cm(10.5)
        self.document.add_paragraph()

    def table(self, headers: list[str], rows: list[list[str]]) -> None:
        table = self.document.add_table(rows=1, cols=len(headers))
        table.style = "Light Grid Accent 1"
        for cell, text in zip(table.rows[0].cells, headers, strict=False):
            cell.text = text
            for paragraph in cell.paragraphs:
                for run in paragraph.runs:
                    run.bold = True
        for row in rows:
            cells = table.add_row().cells
            for cell, text in zip(cells, row, strict=False):
                cell.text = text
        self.document.add_paragraph()

    def image(self, png: bytes, width_cm: float) -> None:
        self.document.add_picture(BytesIO(png), width=Cm(width_cm))

    def page_break(self) -> None:
        self.document.add_section(WD_SECTION.NEW_PAGE)

    def render(self) -> bytes:
        self._apply_header()
        buffer = BytesIO()
        self.document.save(buffer)
        return buffer.getvalue()

    def _apply_header(self) -> None:
        """The disclaimer on every page, and the UNVERIFIED banner when it applies.

        Applied at render time rather than at construction because sections are created
        by `page_break` as the document is written, and a header set before a section
        exists does not reach it.
        """
        for section in self.document.sections:
            header = section.header
            header.is_linked_to_previous = False
            first = header.paragraphs[0]
            first.text = ""
            run = first.add_run(self._disclaimer)
            run.font.size = Pt(7.5)
            run.font.color.rgb = MUTED
            first.paragraph_format.space_after = Pt(0)

            line = header.add_paragraph()
            run = line.add_run(self._stamp)
            run.font.size = Pt(7.5)
            run.font.color.rgb = MUTED

            if self._banner:
                warning = header.add_paragraph()
                run = warning.add_run(self._banner)
                run.font.size = Pt(7.5)
                run.bold = True
                run.font.color.rgb = WARN


# ------------------------------------------------------------------ PDF


#: Print CSS. `@page` carries the running header, so the disclaimer and the UNVERIFIED
#: banner appear on every page of the PDF exactly as they do in the DOCX — a printed page
#: has to be readable on its own.
_CSS = """
@page {{
  size: A4;
  margin: 26mm 22mm 20mm 22mm;
  @top-left {{
    content: "{header}";
    font: 7.5pt/1.3 "DejaVu Sans", sans-serif;
    color: {muted};
    white-space: pre-wrap;
    width: 100%;
  }}
  @bottom-right {{
    content: counter(page) " / " counter(pages);
    font: 7.5pt "DejaVu Sans", sans-serif;
    color: {muted};
  }}
}}
body {{ font: 10.5pt/1.45 "DejaVu Sans", sans-serif; color: {ink}; }}
h1.doc-title {{ font-size: 22pt; margin: 0 0 4pt; }}
p.doc-subtitle {{ font-size: 14pt; color: {muted}; margin: 0 0 18pt; }}
h1 {{ font-size: 15pt; margin: 18pt 0 6pt; }}
h2 {{ font-size: 12.5pt; margin: 14pt 0 5pt; }}
h3 {{ font-size: 11pt; margin: 12pt 0 4pt; }}
p {{ margin: 0 0 6pt; }}
ul {{ margin: 0 0 6pt 0; padding-left: 16pt; }}
li {{ margin: 0 0 3pt; }}
.note {{ font-size: 8.5pt; color: {muted}; }}
.warn {{ font-weight: bold; color: {warn}; }}
table {{ border-collapse: collapse; width: 100%; margin: 0 0 10pt; font-size: 9.5pt; }}
th, td {{ border: 0.5pt solid #b9bfc4; padding: 3pt 5pt; text-align: left;
          vertical-align: top; }}
th {{ background: #eef1f3; font-weight: bold; }}
td.k {{ font-weight: bold; width: 38%; }}
img {{ max-width: 100%; }}
.break {{ break-before: page; }}
"""


class HtmlWriter:
    """WeasyPrint. The format an authority files.

    Renders through HTML rather than converting the DOCX, because converting would need
    LibreOffice — which does not fit on a free tier, and which this product deliberately
    does not depend on.
    """

    def __init__(self, *, disclaimer: str, stamp: str, banner: str | None) -> None:
        self._disclaimer = disclaimer
        self._stamp = stamp
        self._banner = banner
        self._parts: list[str] = []
        self._pending_break = False

    def _emit(self, html_fragment: str) -> None:
        if self._pending_break:
            html_fragment = html_fragment.replace("<", '<div class="break"></div><', 1)
            self._pending_break = False
        self._parts.append(html_fragment)

    @staticmethod
    def _e(text: str) -> str:
        return html.escape(str(text))

    def title(self, text: str, subtitle: str | None = None) -> None:
        self._emit(f'<h1 class="doc-title">{self._e(text)}</h1>')
        if subtitle:
            self._parts.append(f'<p class="doc-subtitle">{self._e(subtitle)}</p>')

    def heading(self, text: str, level: int = 1) -> None:
        tag = f"h{min(max(level, 1), 3)}"
        self._emit(f"<{tag}>{self._e(text)}</{tag}>")

    def paragraph(self, text: str) -> None:
        self._emit(f"<p>{self._e(text)}</p>")

    def _list_item(self, inner: str) -> None:
        """Append to the open list, or start one.

        Consecutive bullets have to share a `<ul>`: a run of single-item lists stacks
        the margin between every line and reads as loose, which is not how the DOCX
        renders the same content.
        """
        if self._parts and self._parts[-1].endswith("</ul>") and not self._pending_break:
            self._parts[-1] = self._parts[-1][: -len("</ul>")] + f"<li>{inner}</li></ul>"
            return
        self._emit(f"<ul><li>{inner}</li></ul>")

    def bullet(self, text: str) -> None:
        self._list_item(self._e(text))

    def lead_bullet(self, lead: str, rest: str) -> None:
        self._list_item(f"<strong>{self._e(lead)}</strong>{self._e(rest)}")

    def note(self, text: str) -> None:
        self._emit(f'<p class="note">{self._e(text)}</p>')

    def warning(self, text: str) -> None:
        self._emit(f'<p class="warn">{self._e(text)}</p>')

    def kv_table(self, rows: list[tuple[str, str]]) -> None:
        body = "".join(
            f'<tr><td class="k">{self._e(k)}</td><td>{self._e(v)}</td></tr>' for k, v in rows
        )
        self._emit(f"<table>{body}</table>")

    def table(self, headers: list[str], rows: list[list[str]]) -> None:
        head = "".join(f"<th>{self._e(h)}</th>" for h in headers)
        body = "".join(
            "<tr>" + "".join(f"<td>{self._e(c)}</td>" for c in row) + "</tr>" for row in rows
        )
        self._emit(f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>")

    def image(self, png: bytes, width_cm: float) -> None:
        import base64

        encoded = base64.b64encode(png).decode("ascii")
        self._emit(f'<img src="data:image/png;base64,{encoded}" style="width:{width_cm}cm">')

    def page_break(self) -> None:
        self._pending_break = True

    def render(self) -> bytes:
        import weasyprint

        header = self._disclaimer + "\n" + self._stamp
        if self._banner:
            header += "\n" + self._banner
        css = _CSS.format(
            header=header.replace('"', "'").replace("\n", "\\A "),
            ink=INK_HEX,
            muted=MUTED_HEX,
            warn=WARN_HEX,
        )
        document = (
            '<!doctype html><html><head><meta charset="utf-8">'
            f"<style>{css}</style></head><body>" + "".join(self._parts) + "</body></html>"
        )
        pdf: Any = weasyprint.HTML(string=document).write_pdf()
        return bytes(pdf)


def writer_for(fmt: str, *, disclaimer: str, stamp: str, banner: str | None) -> Writer:
    if fmt == "docx":
        return DocxWriter(disclaimer=disclaimer, stamp=stamp, banner=banner)
    if fmt == "pdf":
        return HtmlWriter(disclaimer=disclaimer, stamp=stamp, banner=banner)
    raise ValueError(f"unknown dossier format {fmt!r}")
