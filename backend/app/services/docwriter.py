"""Two renderers, one content path.

The dossier is the artefact that reaches an authority, and an operator may want it as
DOCX (to edit alongside the authority's own forms) or as PDF (to file). Writing those as
two documents would be an invitation for them to drift — and a PDF whose SAIL does not
match the DOCX's is the single worst bug this product could ship.

So ``dossier.py`` describes the document once, against the ``Writer`` protocol below,
and a backend turns those calls into a `.docx` or a `.pdf`. Neither backend decides what
goes in the document; both are told. A test renders both from the same input and asserts
the values match.

Both backends are pure Python with the typeface bundled, so a dossier renders the same
on a laptop, on a free-tier host and in CI with nothing to install but the wheels.

The vocabulary is deliberately small — headings, paragraphs, bullets, key/value tables,
grid tables, notes, images, page breaks. Anything richer would start to encode layout in
the content path, which is where drift begins.
"""

from __future__ import annotations

from io import BytesIO
from typing import Protocol

from docx import Document as new_document
from docx.document import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
from fpdf import FPDF
from fpdf.fonts import FontFace
from PIL import Image

from app.services import fonts

INK = RGBColor(0x1A, 0x1A, 0x1A)
MUTED = RGBColor(0x5A, 0x60, 0x66)
WARN = RGBColor(0x8A, 0x52, 0x10)



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


#: Point sizes, matched to the DOCX styles so the two documents read as one product.
_SIZE = {"title": 22, "subtitle": 14, "h1": 15, "h2": 12.5, "h3": 11, "body": 10.5,
         "note": 8.5, "table": 9, "header": 7.5}

#: Page geometry in millimetres. A4 with the DOCX's margins.
_MARGIN_X = 22.0
_MARGIN_TOP = 26.0
_MARGIN_BOTTOM = 18.0

#: RGB tuples for fpdf2, from the same values the DOCX uses.
_INK = (0x1A, 0x1A, 0x1A)
_MUTED = (0x5A, 0x60, 0x66)
_WARN = (0x8A, 0x52, 0x10)
_RULE = (0xB9, 0xBF, 0xC4)
_TH_FILL = (0xEE, 0xF1, 0xF3)


#: What fpdf2 reads as emphasis inside a cell. Doubled, not single — a rule id with one
#: underscore is safe; `__like_this__` is not.
_MD_DELIMITERS = ("**", "__", "--")


def _has_markup(*parts: str) -> bool:
    """Whether any part would be eaten as emphasis rather than printed."""
    return any(d in part for part in parts for d in _MD_DELIMITERS)


class _Pdf(FPDF):
    """An A4 page with the running header and the page number the dossier needs.

    The header is not decoration: a printed page is read on its own, so the disclaimer
    and the UNVERIFIED banner have to be on every one of them.
    """

    def __init__(self, *, disclaimer: str, stamp: str, banner: str | None) -> None:
        super().__init__(orientation="P", unit="mm", format="A4")
        self._disclaimer = disclaimer
        self._stamp = stamp
        self._banner = banner
        self.set_margins(_MARGIN_X, _MARGIN_TOP, _MARGIN_X)
        self.set_auto_page_break(auto=True, margin=_MARGIN_BOTTOM)
        self.add_font("dejavu", "", str(fonts.regular()))
        self.add_font("dejavu", "B", str(fonts.bold()))
        self.set_font("dejavu", size=_SIZE["body"])

    def header(self) -> None:  # fpdf2 calls this on every new page
        top = 8.0
        self.set_y(top)
        self.set_font("dejavu", size=_SIZE["header"])
        self.set_text_color(*_MUTED)
        self.multi_cell(0, 3.4, self._disclaimer, align="L", new_x="LMARGIN", new_y="NEXT")
        self.multi_cell(0, 3.4, self._stamp, align="L", new_x="LMARGIN", new_y="NEXT")
        if self._banner:
            self.set_font("dejavu", "B", _SIZE["header"])
            self.set_text_color(*_WARN)
            self.multi_cell(0, 3.4, self._banner, align="L", new_x="LMARGIN", new_y="NEXT")
        # Start the body below whatever the header actually took, never under it.
        self.set_y(max(self.get_y() + 4.0, _MARGIN_TOP))
        self.set_font("dejavu", size=_SIZE["body"])
        self.set_text_color(*_INK)

    def footer(self) -> None:  # fpdf2 calls this on every new page
        self.set_y(-14)
        self.set_font("dejavu", size=_SIZE["header"])
        self.set_text_color(*_MUTED)
        self.cell(0, 5, f"{self.page_no()} / {{nb}}", align="R")
        self.set_text_color(*_INK)


class PdfWriter:
    """fpdf2. The format an authority files.

    Pure Python, with the typeface bundled in the repository — so a dossier renders
    identically on a laptop, on a free-tier host and in CI, with nothing to install
    beyond ``pip install``. The previous backend rendered HTML through WeasyPrint, which
    needed cairo, pango and a system font: five native libraries that existed only
    because a Dockerfile installed them, and the Dockerfile is gone.
    """

    def __init__(self, *, disclaimer: str, stamp: str, banner: str | None) -> None:
        self._pdf = _Pdf(disclaimer=disclaimer, stamp=stamp, banner=banner)
        self._pdf.add_page()

    # -------------------------------------------------------------- helpers

    @property
    def _width(self) -> float:
        return float(self._pdf.w - 2 * _MARGIN_X)

    def _text(self, body: str, *, size: float, bold: bool = False,
              colour: tuple[int, int, int] = _INK, leading: float = 1.45,
              space_after: float = 2.0, indent: float = 0.0) -> None:
        pdf = self._pdf
        pdf.set_font("dejavu", "B" if bold else "", size)
        pdf.set_text_color(*colour)
        if indent:
            pdf.set_x(_MARGIN_X + indent)
        pdf.multi_cell(
            self._width - indent, size * leading * 0.3528, body,
            align="L", new_x="LMARGIN", new_y="NEXT",
        )
        pdf.ln(space_after)
        pdf.set_text_color(*_INK)

    def _space_for(self, lines: float, size: float) -> None:
        """Keep a heading with at least the start of what follows it."""
        needed = lines * size * 0.52
        if self._pdf.get_y() + needed > self._pdf.h - _MARGIN_BOTTOM:
            self._pdf.add_page()

    # -------------------------------------------------------------- the protocol

    def title(self, text: str, subtitle: str | None = None) -> None:
        self._text(text, size=_SIZE["title"], bold=True, leading=1.15, space_after=1.0)
        if subtitle:
            self._text(subtitle, size=_SIZE["subtitle"], colour=_MUTED, space_after=5.0)
        else:
            self._pdf.ln(4.0)

    def heading(self, text: str, level: int = 1) -> None:
        size = _SIZE[f"h{min(max(level, 1), 3)}"]
        self._space_for(4, size)
        self._pdf.ln(2.0 if level > 1 else 3.0)
        self._text(text, size=size, bold=True, leading=1.2, space_after=1.5)

    def paragraph(self, text: str) -> None:
        self._text(text, size=_SIZE["body"])

    def bullet(self, text: str) -> None:
        self._bullet_row(text, lead=None)

    def lead_bullet(self, lead: str, rest: str) -> None:
        self._bullet_row(rest, lead=lead)

    def _bullet_row(self, text: str, *, lead: str | None) -> None:
        """A hanging bullet: the glyph in the gutter, the text in a block beside it.

        Written as two cells rather than one string so a wrapped second line aligns
        under the first word, not under the bullet.
        """
        pdf = self._pdf
        size = _SIZE["body"]
        line = size * 1.45 * 0.3528
        gutter = 4.5
        if pdf.get_y() + line * 2 > pdf.h - _MARGIN_BOTTOM:
            pdf.add_page()
        y0 = pdf.get_y()
        pdf.set_font("dejavu", size=size)
        pdf.set_text_color(*_INK)
        pdf.set_xy(_MARGIN_X, y0)
        pdf.cell(gutter, line, "\u2022")
        pdf.set_xy(_MARGIN_X + gutter, y0)
        # One multi_cell either way, so a wrapped line hangs under the first word rather
        # than returning to the margin. `write()` cannot do that: it wraps to the page.
        #
        # The emphasis rides along as markdown, which is the only way fpdf2 mixes weights
        # inside a wrapping block — and fpdf2 has no escape character. So when the content
        # itself contains a delimiter, the bold lead is dropped rather than letting the
        # renderer eat part of a rule id. A document that is right beats one that is bold.
        markup = bool(lead) and not _has_markup(lead or "", text)
        body = f"**{lead}**{text}" if markup else f"{lead or ''}{text}"
        pdf.multi_cell(
            self._width - gutter, line, body,
            align="L", new_x="LMARGIN", new_y="NEXT", markdown=markup,
        )
        pdf.ln(0.8)

    def note(self, text: str) -> None:
        self._text(text, size=_SIZE["note"], colour=_MUTED, space_after=2.5)

    def warning(self, text: str) -> None:
        self._text(text, size=_SIZE["body"], bold=True, colour=_WARN, space_after=2.5)

    def kv_table(self, rows: list[tuple[str, str]]) -> None:
        self._grid(None, [[k, v] for k, v in rows], widths=(38.0, 62.0), key_column=True)

    def table(self, headers: list[str], rows: list[list[str]]) -> None:
        self._grid(headers, rows, widths=None, key_column=False)

    def _grid(
        self,
        headers: list[str] | None,
        rows: list[list[str]],
        *,
        widths: tuple[float, ...] | None,
        key_column: bool,
    ) -> None:
        """One table renderer for both shapes, so they cannot look like two products."""
        pdf = self._pdf
        pdf.set_font("dejavu", size=_SIZE["table"])
        pdf.set_draw_color(*_RULE)
        pdf.set_line_width(0.18)
        columns = len(headers) if headers else (len(rows[0]) if rows else 0)
        if not columns:
            return
        col_widths = widths or tuple(100.0 / columns for _ in range(columns))

        with pdf.table(
            col_widths=col_widths,
            line_height=_SIZE["table"] * 1.35 * 0.3528,
            text_align="LEFT",
            borders_layout="ALL",
            headings_style=FontFace(emphasis="BOLD", fill_color=_TH_FILL, color=_INK),
            first_row_as_headings=headers is not None,
            padding=(1.2, 1.6, 1.2, 1.6),
        ) as table:
            if headers:
                row = table.row()
                for cell in headers:
                    row.cell(cell)
            for values in rows:
                row = table.row()
                for index, cell in enumerate(values):
                    style = (
                        FontFace(emphasis="BOLD")
                        if key_column and index == 0
                        else None
                    )
                    row.cell(cell or "", style=style)
        pdf.ln(3.0)
        pdf.set_font("dejavu", size=_SIZE["body"])

    def image(self, png: bytes, width_cm: float) -> None:
        pdf = self._pdf
        width_mm = min(width_cm * 10.0, self._width)
        with Image.open(BytesIO(png)) as probe:
            ratio = probe.height / probe.width
        height_mm = width_mm * ratio
        if pdf.get_y() + height_mm > pdf.h - _MARGIN_BOTTOM:
            pdf.add_page()
        pdf.image(BytesIO(png), x=_MARGIN_X, w=width_mm)
        pdf.ln(2.5)

    def page_break(self) -> None:
        self._pdf.add_page()

    def render(self) -> bytes:
        # `{nb}` in the footer resolves to the total once the document is complete.
        self._pdf.alias_nb_pages()
        return bytes(self._pdf.output())


def writer_for(fmt: str, *, disclaimer: str, stamp: str, banner: str | None) -> Writer:
    if fmt == "docx":
        return DocxWriter(disclaimer=disclaimer, stamp=stamp, banner=banner)
    if fmt == "pdf":
        return PdfWriter(disclaimer=disclaimer, stamp=stamp, banner=banner)
    raise ValueError(f"unknown dossier format {fmt!r}")
