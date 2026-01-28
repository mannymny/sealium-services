from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

from ...domain.ports.pdf_writer_port import PdfWriterPort

DEFAULT_SPONSOR_TEXT = "Esta transcripcion fue patrocinada por mi Deus Raed, Akuuuuum"


def _wrap_text(c, text: str, max_width: float) -> list[str]:
    words = (text or "").split()
    if not words:
        return [""]

    lines: list[str] = []
    cur: list[str] = []

    for w in words:
        test = (" ".join(cur + [w])).strip()
        if c.stringWidth(test) <= max_width or not cur:
            cur.append(w)
        else:
            lines.append(" ".join(cur))
            cur = [w]

    if cur:
        lines.append(" ".join(cur))
    return lines


def _extract_space_id(url: str) -> str:
    if not url:
        return ""
    m = re.search(r"/i/spaces/([A-Za-z0-9]+)", url)
    return m.group(1) if m else ""


def _extract_duration_from_lines(lines: Iterable[str]) -> str:
    for raw in lines:
        s = (raw or "").strip()
        if s.lower().startswith("duration:"):
            return s.split(":", 1)[1].strip() if ":" in s else ""
    return ""


def _iter_clean_transcript_lines(transcript_lines: Iterable[str]) -> Iterable[str]:
    last_was_blank = False
    for raw in transcript_lines:
        s = (raw or "").rstrip("\n")
        if s.strip().lower().startswith("duration:"):
            continue

        is_blank = (s.strip() == "")
        if is_blank:
            if last_was_blank:
                continue
            last_was_blank = True
            yield ""
        else:
            last_was_blank = False
            yield s


def _draw_header_and_sponsor(
    c,
    *,
    letter_pagesize,
    x: float,
    y_top: float,
    max_width: float,
    title: str | None,
    source_url: str | None,
    transcript_lines: Iterable[str],
    sponsor_text: str,
) -> float:
    page_w, _ = letter_pagesize

    space_url = source_url or ""
    space_id = _extract_space_id(space_url)

    duration = _extract_duration_from_lines(transcript_lines)
    duration_line = f"Duration: {duration}" if duration else ""

    header_lines = [
        f"{title or ''}".rstrip(),
        f"Space ID - {space_id}".rstrip(),
        f"Source URL - {space_url}".rstrip(),
    ]
    if duration_line:
        header_lines.append(duration_line)

    c.setFont("Helvetica-Bold", 11)
    y = y_top
    leading = 14

    for line in header_lines:
        wrapped = _wrap_text(c, line, max_width=max_width)
        for wl in wrapped:
            c.drawString(x, y, wl)
            y -= leading

    y -= 6
    c.setLineWidth(1)
    c.line(x, y, page_w - x, y)
    y -= 14

    c.setFont("Helvetica-Bold", 13)
    sponsor_lines = _wrap_text(c, sponsor_text, max_width=max_width)
    for line in sponsor_lines:
        c.drawString(x, y, line)
        y -= 16
    y -= 6
    return y


class ReportLabPdfWriterAdapter(PdfWriterPort):
    def write_pdf(
        self,
        pdf_path: Path,
        *,
        title: str | None,
        source_url: str | None,
        transcript_lines: Iterable[str],
        sponsor_text: str = DEFAULT_SPONSOR_TEXT,
    ) -> Path:
        from reportlab.lib.pagesizes import LETTER
        from reportlab.pdfgen import canvas

        pdf_path = Path(pdf_path)

        c = canvas.Canvas(str(pdf_path), pagesize=LETTER)
        page_w, page_h = LETTER

        margin_x = 50
        max_width = page_w - 2 * margin_x

        body_font = "Helvetica"
        body_size = 10
        leading = 14

        top_y_default = page_h - 60
        bottom_y = 50

        y = page_h - 50
        y = _draw_header_and_sponsor(
            c,
            letter_pagesize=LETTER,
            x=margin_x,
            y_top=y,
            max_width=max_width,
            title=title,
            source_url=source_url,
            transcript_lines=transcript_lines,
            sponsor_text=sponsor_text,
        )

        c.setFont(body_font, body_size)
        y = min(y, top_y_default)

        def next_page():
            nonlocal y
            c.showPage()
            c.setFont(body_font, body_size)
            y = top_y_default

        for raw in _iter_clean_transcript_lines(transcript_lines):
            line = (raw or "")
            if line == "":
                y -= 8
                if y < bottom_y:
                    next_page()
                continue

            wrapped = _wrap_text(c, line, max_width=max_width)
            for wl in wrapped:
                if y < bottom_y:
                    next_page()
                c.drawString(margin_x, y, wl)
                y -= leading

        c.save()
        return pdf_path
