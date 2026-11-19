"""Build report/Calibra_Final_Report.docx from report/md/*.md and report/figures.

    report/.venv/Scripts/python.exe report/scripts/build_docx.py [--pdf]

Two passes: the document is built, converted to PDF with LibreOffice, page
numbers of headings and captions are read back from the PDF, and the document
is rebuilt with those numbers cached inside real Word TOC fields (Word can
refresh them with F9; LibreOffice shows them as-is).
Markdown dialect: see report/PLAN.md.
"""
from __future__ import annotations

import io
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

import fitz  # PyMuPDF
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from docx import Document  # noqa: E402
from docx.enum.section import WD_SECTION  # noqa: E402
from docx.enum.table import WD_TABLE_ALIGNMENT  # noqa: E402
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_LINE_SPACING, WD_TAB_ALIGNMENT, WD_TAB_LEADER  # noqa: E402
from docx.oxml import OxmlElement  # noqa: E402
from docx.oxml.ns import qn  # noqa: E402
from docx.shared import Cm, Pt, RGBColor  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "report"
MD = REPORT / "md"
FIG = REPORT / "figures"
OUT_DOCX = REPORT / "Calibra_Final_Report.docx"
OUT_PDF = REPORT / "Calibra_Final_Report.pdf"
EQ_DIR = REPORT / "build" / "equations"
SOFFICE = Path("C:/Program Files/LibreOffice/program/soffice.com")

TITLE = "Calibra: Step-Level Confidence Calibration for LLM Reasoning"
RUNNING = "Calibra: Step-Level Confidence Calibration for LLM Reasoning"
FONT = "Times New Roman"
MONO = "Consolas"
BODY_PT = 12
LINE = 1.2
TEXT_WIDTH_CM = 16.0  # A4 21 cm - 2 x 2.5 cm
MAX_FIG_H_CM = 19.0

STUDENTS = [
    ("Aarya Pandey", "231071003"),
    ("Khushbu Chaudhari", "231081018"),
    ("Diksha Dhanmane", "231081020"),
    ("Nisarg Gadhiya", "231080022"),
]
GUIDE = "Prof. Sopan Kolte"
HOD = "[Head of Department]"
DEPARTMENT = "DEPARTMENT OF COMPUTER ENGINEERING AND INFORMATION TECHNOLOGY"
INSTITUTE = "VEERMATA JIJABAI TECHNOLOGICAL INSTITUTE"
INSTITUTE_LINES = [
    "(An Autonomous Institute Affiliated to Mumbai University)",
    "(Central Technological Institute, Maharashtra State)",
    "Matunga, MUMBAI – 400019",
]
YEAR = "A.Y. 2026–2027"
LOGO = ROOT / "assets" / "vjti_logo.png"


# ===================================================================== parsing
@dataclass
class Block:
    kind: str  # h1 h2 h3 para bullet number fig table eq code pagebreak
    text: str = ""
    level: int = 0
    data: dict = field(default_factory=dict)


@dataclass
class Unit:
    """A chapter, an appendix or an unnumbered front/back-matter section."""
    path: Path
    kind: str  # chapter | appendix | front
    number: str  # "6", "A", ""
    title: str
    blocks: list


LABEL = re.compile(r"\s*\{#((?:fig|tab|eq|sec):[\w-]+)\}\s*$")


def parse_md(path: Path) -> tuple[str, list[Block]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    title, blocks, i = "", [], 0
    para: list[str] = []

    def flush():
        if para:
            blocks.append(Block("para", " ".join(s.strip() for s in para)))
            para.clear()

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if stripped.startswith("```"):
            flush()
            lang = stripped[3:].strip()
            body = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                body.append(lines[i])
                i += 1
            blocks.append(Block("code", "\n".join(body), data={"lang": lang}))
            i += 1
            continue
        if not stripped:
            flush()
            i += 1
            continue
        if stripped == "\\newpage":
            flush()
            blocks.append(Block("pagebreak"))
            i += 1
            continue
        m = re.match(r"^(#{1,3})\s+(.*)$", stripped)
        if m:
            flush()
            text = m.group(2)
            label = LABEL.search(text)
            key = label.group(1) if label else None
            text = LABEL.sub("", text).strip()
            if len(m.group(1)) == 1:
                title = text
            else:
                blocks.append(Block(f"h{len(m.group(1))}", text, data={"label": key}))
            i += 1
            continue
        m = re.match(r"^!\[(.*)\]\(([^)]+)\)(\{#(fig:[\w-]+)\})?\s*$", stripped)
        if m:
            flush()
            blocks.append(Block("fig", m.group(1), data={"file": m.group(2), "label": m.group(4)}))
            i += 1
            continue
        if stripped.startswith("Table:"):
            flush()
            cap = stripped[len("Table:"):].strip()
            label = LABEL.search(cap)
            key = label.group(1) if label else None
            cap = LABEL.sub("", cap).strip()
            i += 1
            while i < len(lines) and not lines[i].strip():
                i += 1
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
                    rows.append(cells)
                i += 1
            blocks.append(Block("table", cap, data={"rows": rows, "label": key}))
            continue
        m = re.match(r"^\$\$(.+)\$\$\s*(\{#(eq:[\w-]+)\})?\s*$", stripped)
        if m:
            flush()
            blocks.append(Block("eq", m.group(1).strip(), data={"label": m.group(3)}))
            i += 1
            continue
        m = re.match(r"^(\s*)[-*]\s+(.*)$", line)
        if m and not para:
            blocks.append(Block("bullet", m.group(2), level=len(m.group(1)) // 2))
            i += 1
            while i < len(lines) and lines[i].startswith("  ") and lines[i].strip() and not re.match(r"^\s*([-*]|\d+\.)\s", lines[i]):
                blocks[-1].text += " " + lines[i].strip()
                i += 1
            continue
        m = re.match(r"^(\s*)(\d+)\.\s+(.*)$", line)
        if m and not para:
            blocks.append(Block("number", m.group(3), level=len(m.group(1)) // 2, data={"n": int(m.group(2))}))
            i += 1
            while i < len(lines) and lines[i].startswith("   ") and lines[i].strip() and not re.match(r"^\s*([-*]|\d+\.)\s", lines[i]):
                blocks[-1].text += " " + lines[i].strip()
                i += 1
            continue
        para.append(line)
        i += 1
    flush()
    return title, blocks


def load_units() -> list[Unit]:
    units = []
    for path in sorted(MD.glob("*.md")):
        stem = path.stem
        title, blocks = parse_md(path)
        if re.match(r"^\d{2}_", stem) and stem[:2] != "00":
            units.append(Unit(path, "chapter", str(int(stem[:2])), title, blocks))
        elif re.match(r"^A[A-Z]_", stem):
            units.append(Unit(path, "appendix", stem[1], title, blocks))
        else:
            units.append(Unit(path, "front", "", title, blocks))
    return units


# ============================================================ numbering / refs
class Registry:
    def __init__(self, units, references):
        self.labels: dict[str, str] = {}
        self.figures: list[tuple[str, str]] = []  # (number, caption)
        self.tables: list[tuple[str, str]] = []
        self.headings: list[tuple[int, str, str]] = []  # (level, number, title)
        self.references = references
        self.cite_order: list[str] = []
        for unit in units:
            if unit.kind not in ("chapter", "appendix"):
                continue
            n = unit.number
            counters = {"fig": 0, "tab": 0, "eq": 0, "h2": 0, "h3": 0}
            for block in unit.blocks:
                if block.kind == "h2":
                    counters["h2"] += 1
                    counters["h3"] = 0
                    num = f"{n}.{counters['h2']}"
                    block.data["num"] = num
                elif block.kind == "h3":
                    counters["h3"] += 1
                    num = f"{n}.{counters['h2']}.{counters['h3']}"
                    block.data["num"] = num
                elif block.kind in ("fig", "table", "eq"):
                    key = {"fig": "fig", "table": "tab", "eq": "eq"}[block.kind]
                    counters[key] += 1
                    num = f"{n}.{counters[key]}"
                    block.data["num"] = num
                    if block.kind == "fig":
                        self.figures.append((num, block.text))
                    elif block.kind == "table":
                        self.tables.append((num, block.text))
                else:
                    continue
                if block.data.get("label"):
                    self.labels[block.data["label"]] = num
        # citation order follows reading order
        for unit in units:
            for block in unit.blocks:
                texts = [block.text]
                if block.kind == "table":
                    texts += [c for row in block.data["rows"] for c in row]
                for t in texts:
                    for group in re.findall(r"\[(@[^\]]+)\]", t):
                        for key in re.findall(r"@([\w:-]+)", group):
                            if key in self.references and key not in self.cite_order:
                                self.cite_order.append(key)

    def ref(self, key):
        if key not in self.labels:
            print("WARNING unresolved reference", key)
            return "??"
        kind = key.split(":")[0]
        word = {"fig": "Figure", "tab": "Table", "eq": "Equation", "sec": "Section"}[kind]
        return f"{word} {self.labels[key]}" if kind != "eq" else f"({self.labels[key]})"

    def cite(self, keys):
        nums = []
        for key in keys:
            if key not in self.references:
                print("WARNING unknown citation", key)
                continue
            nums.append(self.cite_order.index(key) + 1)
        nums = sorted(set(nums))
        parts, start = [], None
        for idx, n in enumerate(nums):
            if start is None:
                start = n
            if idx + 1 == len(nums) or nums[idx + 1] != n + 1:
                parts.append(f"{start}" if start == n else f"{start}–{n}" if n - start > 1 else f"{start}], [{n}")
                start = None
        return "[" + "], [".join(parts) + "]" if parts else "[?]"


def resolve(text: str, reg: Registry) -> str:
    text = re.sub(r"\[(@[^\]]+)\]", lambda m: reg.cite(re.findall(r"@([\w:-]+)", m.group(1))), text)
    text = re.sub(r"@((?:fig|tab|eq|sec):[\w-]+)", lambda m: reg.ref(m.group(1)), text)
    return text


# ================================================================ docx helpers
def set_cell_shading(cell, hex_fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_fill)
    tc_pr.append(shd)


def add_field(paragraph, instr, cached=""):
    run = paragraph.add_run()
    fld = OxmlElement("w:fldChar")
    fld.set(qn("w:fldCharType"), "begin")
    run._r.append(fld)
    run = paragraph.add_run()
    instr_el = OxmlElement("w:instrText")
    instr_el.set(qn("xml:space"), "preserve")
    instr_el.text = instr
    run._r.append(instr_el)
    run = paragraph.add_run()
    fld = OxmlElement("w:fldChar")
    fld.set(qn("w:fldCharType"), "separate")
    run._r.append(fld)
    paragraph.add_run(cached)
    run = paragraph.add_run()
    fld = OxmlElement("w:fldChar")
    fld.set(qn("w:fldCharType"), "end")
    run._r.append(fld)


def field_begin(paragraph, instr):
    run = paragraph.add_run()
    fld = OxmlElement("w:fldChar")
    fld.set(qn("w:fldCharType"), "begin")
    fld.set(qn("w:dirty"), "false")
    run._r.append(fld)
    run = paragraph.add_run()
    el = OxmlElement("w:instrText")
    el.set(qn("xml:space"), "preserve")
    el.text = instr
    run._r.append(el)
    run = paragraph.add_run()
    fld = OxmlElement("w:fldChar")
    fld.set(qn("w:fldCharType"), "separate")
    run._r.append(fld)


def field_end(paragraph):
    run = paragraph.add_run()
    fld = OxmlElement("w:fldChar")
    fld.set(qn("w:fldCharType"), "end")
    run._r.append(fld)


def page_number_format(section, fmt, start=None):
    sect_pr = section._sectPr
    pg = sect_pr.find(qn("w:pgNumType"))
    if pg is None:
        pg = OxmlElement("w:pgNumType")
        sect_pr.append(pg)
    pg.set(qn("w:fmt"), fmt)
    if start is not None:
        pg.set(qn("w:start"), str(start))


def keep_with_next(paragraph):
    paragraph.paragraph_format.keep_with_next = True


INLINE = re.compile(r"(\$[^$]+\$|\*\*.+?\*\*|`[^`]+`|(?<![\w*])\*[^*\s][^*]*?\*(?![\w*]))")

TEX_SYMBOLS = {
    r"\dots": "…", r"\ldots": "…", r"\cdots": "⋯", r"\cdot": "·", r"\times": "×", r"\in": "∈", r"\notin": "∉",
    r"\le": "≤", r"\leq": "≤", r"\ge": "≥", r"\geq": "≥", r"\ne": "≠", r"\neq": "≠", r"\approx": "≈",
    r"\to": "→", r"\rightarrow": "→", r"\Rightarrow": "⇒", r"\forall": "∀", r"\exists": "∃", r"\neg": "¬",
    r"\land": "∧", r"\wedge": "∧", r"\lor": "∨", r"\vee": "∨", r"\infty": "∞", r"\sum": "Σ", r"\prod": "Π",
    r"\alpha": "α", r"\beta": "β", r"\gamma": "γ", r"\delta": "δ", r"\epsilon": "ε", r"\theta": "θ",
    r"\lambda": "λ", r"\mu": "μ", r"\pi": "π", r"\sigma": "σ", r"\tau": "τ", r"\phi": "φ", r"\omega": "ω",
    r"\Delta": "Δ", r"\Sigma": "Σ", r"\ell": "ℓ", r"\imath": "ı", r"\log": "log", r"\exp": "exp",
    r"\min": "min", r"\max": "max", r"\arg": "arg", r"\mid": "|", r"\vert": "|", r"\,": " ", r"\;": " ",
    r"\quad": "  ", r"\{": "{", r"\}": "}", r"\%": "%", r"\top": "⊤", r"\models": "⊨", r"\vdash": "⊢",
    r"\lnot": "¬", r"\mathbb{1}": "𝟙", r"\sim": "∼", r"\pm": "±", r"\langle": "⟨", r"\rangle": "⟩",
}


def tex_to_runs(tex: str):
    """Very small LaTeX-to-Unicode converter for inline math -> [(text, valign, italic)]."""
    tex = re.sub(r"\\(?:mathrm|text|operatorname|mathit|textrm)\{([^{}]*)\}", lambda m: "\x01" + m.group(1) + "\x02", tex)
    tex = re.sub(r"\\hat\{\\imath\}", "î", tex)
    tex = re.sub(r"\\hat\{(\w)\}", lambda m: m.group(1) + "\u0302", tex)
    tex = re.sub(r"\\bar\{(\\?\w+)\}", lambda m: (TEX_SYMBOLS.get(m.group(1), m.group(1).lstrip("\\"))) + "\u0304", tex)
    tex = re.sub(r"\\frac\{([^{}]*)\}\{([^{}]*)\}", r"(\1)/(\2)", tex)
    tex = tex.replace(r"\left", "").replace(r"\right", "").replace(r"\!", "")
    for cmd in sorted(TEX_SYMBOLS, key=len, reverse=True):
        tex = re.sub(re.escape(cmd) + r"(?![A-Za-z])", lambda m, c=cmd: TEX_SYMBOLS[c], tex)
    runs, i, upright = [], 0, False
    buf = ""

    def flush(text, valign=None):
        if text:
            runs.append((text, valign))

    while i < len(tex):
        ch = tex[i]
        if ch in "_^":
            flush(buf)
            buf = ""
            valign = "subscript" if ch == "_" else "superscript"
            i += 1
            if i < len(tex) and tex[i] == "{":
                depth, j = 1, i + 1
                while j < len(tex) and depth:
                    depth += {"{": 1, "}": -1}.get(tex[j], 0)
                    j += 1
                flush(tex[i + 1:j - 1].replace("{", "").replace("}", ""), valign)
                i = j
            elif i < len(tex):
                flush(tex[i], valign)
                i += 1
            continue
        if ch in "{}":
            i += 1
            continue
        buf += ch
        i += 1
    flush(buf)
    return runs


def add_math(paragraph, tex, size=None, bold=False):
    for text, valign in tex_to_runs(tex):
        # upright for words, digits and operators; italic for single-letter variables
        for chunk in re.split(r"(\x01[^\x02]*\x02)", text):
            if not chunk:
                continue
            upright = chunk.startswith("\x01")
            chunk = chunk.strip("\x01\x02")
            for part in re.split(r"((?<![A-Za-z])[A-Za-zα-ωℓı](?![A-Za-z]))", chunk):
                if not part:
                    continue
                run = paragraph.add_run(part)
                run.italic = (not upright) and bool(re.fullmatch(r"[A-Za-zα-ωℓı]", part))
                run.bold = bold or None
                if valign == "subscript":
                    run.font.subscript = True
                elif valign == "superscript":
                    run.font.superscript = True
                if size:
                    run.font.size = Pt(size)


def add_inline(paragraph, text, reg, size=None, base_bold=False, base_italic=False):
    text = resolve(text, reg)
    for piece in INLINE.split(text):
        if not piece:
            continue
        if piece.startswith("$") and piece.endswith("$") and len(piece) > 2:
            add_math(paragraph, piece[1:-1], size=size, bold=base_bold)
            continue
        if piece.startswith("**") and piece.endswith("**"):
            inner = piece[2:-2]
            if re.search(r"(?<![\w*])\*[^*\s][^*]*?\*(?![\w*])|`|\$", inner):
                add_inline(paragraph, inner, reg, size=size, base_bold=True, base_italic=base_italic)
                continue
            run = paragraph.add_run(inner)
            run.bold = True
            run.italic = base_italic or None
        elif piece.startswith("`") and piece.endswith("`"):
            run = paragraph.add_run(piece[1:-1])
            run.font.name = MONO
            run._element.rPr.rFonts.set(qn("w:eastAsia"), MONO)
            run.font.size = Pt((size or BODY_PT) - 1.5)
            run.bold = base_bold or None
        elif piece.startswith("*") and piece.endswith("*") and len(piece) > 2:
            run = paragraph.add_run(piece[1:-1])
            run.italic = True
            run.bold = base_bold or None
        else:
            run = paragraph.add_run(piece)
            run.bold = base_bold or None
            run.italic = base_italic or None
        if size:
            run.font.size = Pt(size)


TECTONIC = Path("C:/Users/nisar/AppData/Local/Programs/tectonic/tectonic.exe")


def render_equation(latex: str, name: str) -> Path:
    """Render a display equation with real LaTeX (Tectonic), cached by content hash."""
    import hashlib
    EQ_DIR.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha1(latex.encode("utf-8")).hexdigest()[:16]
    path = EQ_DIR / f"{digest}.png"
    if path.exists():
        return path
    work = EQ_DIR / digest
    work.mkdir(exist_ok=True)
    tex = work / "eq.tex"
    tex.write_text(
        "\\documentclass[border=3pt,varwidth=16cm]{standalone}\n"
        "\\usepackage{amsmath,amssymb,bm}\n"
        "\\usepackage{lmodern}\n"
        "\\begin{document}\n"
        f"$\\displaystyle {latex}$\n"
        "\\end{document}\n",
        encoding="utf-8",
    )
    proc = subprocess.run([str(TECTONIC), "-X", "compile", "eq.tex"], cwd=work, capture_output=True, text=True, timeout=600)
    pdf = work / "eq.pdf"
    if proc.returncode != 0 or not pdf.exists():
        raise RuntimeError(f"Equation failed to compile ({name}): {latex}\n{proc.stderr[-800:]}")
    page = fitz.open(pdf)[0]
    page.get_pixmap(dpi=300).save(path)
    return path


# ==================================================================== builder
class Builder:
    def __init__(self, units, reg: Registry, pages: dict | None):
        self.units = units
        self.reg = reg
        self.pages = pages or {}
        self.doc = Document()
        self._styles()

    # ---------------------------------------------------------------- styles
    def _styles(self):
        doc = self.doc
        st = doc.styles["Normal"]
        st.font.name = FONT
        st.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
        st.font.size = Pt(BODY_PT)
        pf = st.paragraph_format
        pf.line_spacing = LINE
        pf.space_after = Pt(6)
        pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        for name, size, before, after in (("Heading 1", 20, 0, 18), ("Heading 2", 14, 14, 6), ("Heading 3", 12.5, 10, 4)):
            h = doc.styles[name]
            h.font.name = FONT
            h.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
            h.element.rPr.rFonts.set(qn("w:ascii"), FONT)
            h.element.rPr.rFonts.set(qn("w:hAnsi"), FONT)
            h.font.size = Pt(size)
            h.font.bold = True
            h.font.italic = False
            h.font.color.rgb = RGBColor(0, 0, 0)
            h.paragraph_format.space_before = Pt(before)
            h.paragraph_format.space_after = Pt(after)
            h.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
            h.paragraph_format.keep_with_next = True
        for name in ("Figure Caption", "Table Caption"):
            c = doc.styles.add_style(name, 1)
            c.base_style = doc.styles["Normal"]
            c.font.size = Pt(10.5)
            c.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
            c.paragraph_format.space_before = Pt(4)
            c.paragraph_format.space_after = Pt(10)
            c.paragraph_format.line_spacing = 1.0
        code = doc.styles.add_style("Code Block", 1)
        code.base_style = doc.styles["Normal"]
        code.font.name = MONO
        code.element.rPr.rFonts.set(qn("w:eastAsia"), MONO)
        code.font.size = Pt(8.5)
        code.paragraph_format.line_spacing = 1.0
        code.paragraph_format.space_after = Pt(0)
        code.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
        for lvl in (1, 2, 3):
            name = f"TOC {lvl}"
            try:
                t = doc.styles[name]
            except KeyError:
                t = doc.styles.add_style(name, 1)
            t.base_style = doc.styles["Normal"]
            t.font.size = Pt(12 if lvl == 1 else 11)
            t.font.bold = lvl == 1
            t.paragraph_format.left_indent = Cm(0.8 * (lvl - 1))
            t.paragraph_format.space_after = Pt(2 if lvl > 1 else 4)
            t.paragraph_format.space_before = Pt(6 if lvl == 1 else 0)
            t.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
            t.paragraph_format.line_spacing = 1.0

    # --------------------------------------------------------------- helpers
    def para(self, text="", style=None, align=None, size=None, bold=False, italic=False, space_after=None, inline=True):
        p = self.doc.add_paragraph(style=style)
        if text:
            if inline:
                add_inline(p, text, self.reg, size=size, base_bold=bold, base_italic=italic)
            else:
                run = p.add_run(text)
                run.bold = bold or None
                run.italic = italic or None
                if size:
                    run.font.size = Pt(size)
        if align is not None:
            p.alignment = align
        if space_after is not None:
            p.paragraph_format.space_after = Pt(space_after)
        return p

    def page_break(self):
        self.doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    def centered(self, text, size=12, bold=False, after=4, italic=False):
        return self.para(text, align=WD_ALIGN_PARAGRAPH.CENTER, size=size, bold=bold, italic=italic, space_after=after, inline=False)

    def header_footer(self, section, show):
        section.header.is_linked_to_previous = False
        section.footer.is_linked_to_previous = False
        hp = section.header.paragraphs[0]
        for r in list(hp.runs):
            r._r.getparent().remove(r._r)
        if not show:
            return
        hp.paragraph_format.tab_stops.add_tab_stop(Cm(TEXT_WIDTH_CM), WD_TAB_ALIGNMENT.RIGHT)
        run = hp.add_run(RUNNING)
        run.italic = True
        run.font.size = Pt(9.5)
        hp.add_run("\t").font.size = Pt(9.5)
        add_field(hp, "PAGE", "1")
        for r in hp.runs:
            r.font.size = Pt(9.5)
        p_pr = hp._p.get_or_add_pPr()
        bdr = OxmlElement("w:pBdr")
        bottom = OxmlElement("w:bottom")
        bottom.set(qn("w:val"), "single")
        bottom.set(qn("w:sz"), "4")
        bottom.set(qn("w:space"), "1")
        bottom.set(qn("w:color"), "808080")
        bdr.append(bottom)
        p_pr.append(bdr)

    # ---------------------------------------------------------- front matter
    def title_page(self):
        sec = self.doc.sections[0]
        sec.page_height, sec.page_width = Cm(29.7), Cm(21.0)
        for side in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
            setattr(sec, side, Cm(2.5))
        sec.header_distance = Cm(1.25)
        self.header_footer(sec, False)
        self.centered("Final Report", 16, bold=True, after=0)
        self.centered("on", 13, after=10)
        self.centered(TITLE, 20, bold=True, after=18)
        self.centered("Submitted", 12, after=0)
        self.centered("in partial fulfillment of", 12, after=0)
        self.centered("the requirements for the degree of Bachelor of Technology in Computer Engineering", 12, after=10)
        self.centered("by", 12, italic=True, after=6)
        for name, roll in STUDENTS:
            self.centered(f"{name} ({roll})", 13, bold=True, after=2)
        self.centered("", 6, after=8)
        self.centered("Under the Guidance of", 12, italic=True, after=2)
        self.centered(GUIDE, 13, bold=True, after=12)
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.add_run().add_picture(str(LOGO), width=Cm(3.5))
        p.paragraph_format.space_after = Pt(12)
        self.centered(DEPARTMENT, 12, bold=True, after=2)
        self.centered(INSTITUTE, 13, bold=True, after=2)
        for line in INSTITUTE_LINES:
            self.centered(line, 11, after=0)
        self.centered(YEAR, 12, bold=True, after=0)

    def signature_table(self, rows, headers):
        table = self.doc.add_table(rows=1, cols=len(headers))
        table.style = "Table Grid"
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        for cell, text in zip(table.rows[0].cells, headers):
            cell.paragraphs[0].add_run(text).bold = True
            cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            set_cell_shading(cell, "EDEDED")
        for row in rows:
            cells = table.add_row().cells
            for cell, text in zip(cells, row):
                cell.paragraphs[0].add_run(text)
                cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
                cell.paragraphs[0].paragraph_format.space_before = Pt(9)
                cell.paragraphs[0].paragraph_format.space_after = Pt(9)
        return table

    def candidate_table(self):
        return self.signature_table([(n, r, "") for n, r in STUDENTS], ["Name of Candidate", "Roll No.", "Signature"])

    def front_heading(self, title):
        p = self.doc.add_paragraph(style="Heading 1")
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.add_run(title)
        return p

    def signature_lines(self, people):
        """A row of blank signature lines with a name and role under each."""
        table = self.doc.add_table(rows=2, cols=len(people))
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        for col, (name, role) in enumerate(people):
            table.rows[0].cells[col].paragraphs[0].add_run("\n\n______________________")
            p = table.rows[1].cells[col].paragraphs[0]
            if name:
                p.add_run(name).bold = True
                p.add_run("\n")
            p.add_run(role)
            for row in table.rows:
                row.cells[col].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        return table

    def date_place(self):
        self.para("")
        self.para("Date: ____________________", align=WD_ALIGN_PARAGRAPH.LEFT, space_after=2)
        self.para("Place: VJTI, Mumbai", align=WD_ALIGN_PARAGRAPH.LEFT)

    def front_pages(self):
        sec = self.doc.add_section(WD_SECTION.NEW_PAGE)
        self.header_footer(sec, True)
        page_number_format(sec, "lowerRoman", 1)
        department = "Department of Computer Engineering and Information Technology"
        # Statement of candidate
        self.front_heading("STATEMENT OF CANDIDATE")
        self.para(f"We, the undersigned, declare that the project report entitled “{TITLE}”, submitted in partial "
                  "fulfillment of the requirements for the degree of Bachelor of Technology in Computer Engineering, "
                  f"presents work that we carried out ourselves during the academic year 2026–2027 under the guidance of {GUIDE}.")
        self.para("We further declare that this work has not been submitted to any other university or institute for the award "
                  "of any degree or diploma, that the work of others used in this report has been acknowledged and cited, "
                  "and that every result reported here was produced by the system described in this report from data and "
                  "scripts held in the project repository.")
        self.para("")
        self.candidate_table()
        self.date_place()
        self.page_break()
        # Approval sheet
        self.front_heading("APPROVAL SHEET")
        self.para(f"The project report entitled “{TITLE}”, submitted by the following candidates in partial fulfillment "
                  "of the requirements for the degree of Bachelor of Technology in Computer Engineering, is approved.")
        self.para(f"The work was carried out under the supervision of {GUIDE}, {department}, Veermata Jijabai "
                  "Technological Institute (VJTI), Mumbai, and the report has been examined and found to meet the "
                  "requirements prescribed by the institute.")
        self.para("")
        self.candidate_table()
        self.para("")
        self.signature_lines([(GUIDE, "B.Tech. Supervisor"), ("", "Examiner"), ("", "Examiner")])
        self.date_place()
        self.page_break()
        # Certificate
        self.front_heading("CERTIFICATE")
        self.para(f"This is to certify that the project entitled “{TITLE}”, submitted by the following students, has been "
                  f"carried out under the supervision of {GUIDE}, {department}, Veermata Jijabai Technological Institute "
                  "(VJTI), Mumbai, in partial fulfillment of the requirements for the degree of Bachelor of Technology in "
                  "Computer Engineering during the academic year 2026–2027.")
        self.para("The work presented in this report is original and has not been submitted to any other university or "
                  "institute for the award of any degree or diploma.")
        self.para("")
        self.candidate_table()
        self.para("")
        self.signature_lines([(GUIDE, "B.Tech. Supervisor"), (HOD, "Head of Department"), ("", "Examiner")])
        self.para("")
        self.para("College Seal / Stamp", align=WD_ALIGN_PARAGRAPH.RIGHT)
        self.date_place()
        self.page_break()

    def toc_entry(self, style, text, page, right_tab=True):
        p = self.doc.add_paragraph(style=style)
        p.paragraph_format.tab_stops.add_tab_stop(Cm(TEXT_WIDTH_CM), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)
        p.add_run(text)
        p.add_run(f"\t{page}")
        return p

    def lists(self, front_units):
        # Contents
        self.front_heading("Contents")
        self.mark("Contents", "front")
        entries = []
        before = ["Statement of Candidate", "Approval Sheet", "Certificate"] + \
            [u.title for u in front_units if "abbrev" not in u.path.stem]
        after = [u.title for u in front_units if "abbrev" in u.path.stem]
        for title in before + ["List of Figures", "List of Tables"] + after:
            entries.append((1, title, self.pages.get(("front", title), "")))
        for unit in self.units:
            if unit.kind == "chapter":
                entries.append((1, f"{unit.number}  {unit.title}", self.pages.get(("h1", unit.number), "")))
            elif unit.kind == "appendix":
                entries.append((1, f"Appendix {unit.number}  {unit.title}", self.pages.get(("h1", unit.number), "")))
            elif unit.kind == "back":
                entries.append((1, unit.title, self.pages.get(("h1", unit.title), "")))
            else:
                continue
            for block in unit.blocks:
                if block.kind in ("h2", "h3") and "num" in block.data:
                    lvl = 2 if block.kind == "h2" else 3
                    if lvl == 3:
                        continue
                    entries.append((lvl, f"{block.data['num']}  {block.text}", self.pages.get(("h", block.data["num"]), "")))
        ref_title = "References"
        entries.insert(next(i for i, e in enumerate(entries) if e[1].startswith("Appendix")) if any(e[1].startswith("Appendix") for e in entries) else len(entries),
                       (1, ref_title, self.pages.get(("h1", ref_title), "")))
        first = True
        for lvl, text, page in entries:
            p = self.toc_entry(f"TOC {lvl}", text, page)
            if first:
                # wrap the cached entries in a real TOC field
                r = p.runs[0]
                field_p = p
                first = False
        self._wrap_field(self._last_n_paragraphs(len(entries)), 'TOC \\o "1-2" \\h \\z \\u')
        self.page_break()
        # List of figures
        self.front_heading("List of Figures")
        paras = []
        for num, cap in self.reg.figures:
            paras.append(self.toc_entry("TOC 2", f"Figure {num}  {self._plain(cap)}", self.pages.get(("fig", num), "")))
        self._wrap_field(paras, 'TOC \\h \\z \\t "Figure Caption,1"')
        self.page_break()
        self.front_heading("List of Tables")
        paras = []
        for num, cap in self.reg.tables:
            paras.append(self.toc_entry("TOC 2", f"Table {num}  {self._plain(cap)}", self.pages.get(("tab", num), "")))
        self._wrap_field(paras, 'TOC \\h \\z \\t "Table Caption,1"')
        self.page_break()

    def _last_n_paragraphs(self, n):
        return self.doc.paragraphs[-n:]

    def _wrap_field(self, paras, instr):
        if not paras:
            return
        first, last = paras[0], paras[-1]
        # insert field begin at the start of first paragraph
        tmp = self.doc.add_paragraph()
        field_begin(tmp, instr)
        runs = list(tmp._p.findall(qn("w:r")))
        p_pr = first._p.find(qn("w:pPr"))
        anchor = p_pr if p_pr is not None else None
        for idx, r in enumerate(runs):
            if anchor is not None:
                anchor.addnext(r)
                anchor = r
            else:
                first._p.insert(idx, r)
        tmp._p.getparent().remove(tmp._p)
        field_end(last)

    def _plain(self, text):
        text = resolve(text, self.reg)
        text = re.sub(r"\*\*|`|(?<!\w)\*(?!\s)|(?<!\s)\*(?!\w)", "", text)
        return text.rstrip(".")

    def mark(self, title, kind):
        pass

    # ------------------------------------------------------------- body
    def body(self):
        sec = self.doc.add_section(WD_SECTION.NEW_PAGE)
        self.header_footer(sec, True)
        page_number_format(sec, "decimal", 1)
        first = True
        for unit in self.units:
            if unit.kind == "front":
                continue
            if not first:
                self.page_break()
            first = False
            self.unit(unit)

    def unit(self, unit):
        if unit.kind == "chapter":
            label = f"Chapter {unit.number}"
        elif unit.kind == "appendix":
            label = f"Appendix {unit.number}"
        else:
            label = ""
        if label:
            p = self.para(label, size=16, bold=True, align=WD_ALIGN_PARAGRAPH.LEFT, space_after=4, inline=False)
            p.paragraph_format.space_before = Pt(36)
            keep_with_next(p)
        h = self.doc.add_paragraph(style="Heading 1")
        h.add_run(unit.title)
        if not label:
            h.paragraph_format.space_before = Pt(36)
        self.blocks(unit.blocks, unit)

    def blocks(self, blocks, unit):
        list_counter = 0
        for block in blocks:
            k = block.kind
            if k != "number":
                list_counter = 0
            if k == "h2":
                p = self.doc.add_paragraph(style="Heading 2")
                p.add_run(f"{block.data['num']}  {block.text}")
            elif k == "h3":
                p = self.doc.add_paragraph(style="Heading 3")
                p.add_run(f"{block.data['num']}  {block.text}")
            elif k == "para":
                self.para(block.text)
            elif k in ("bullet", "number"):
                p = self.doc.add_paragraph()
                indent = 0.9 + 0.7 * block.level
                p.paragraph_format.left_indent = Cm(indent)
                p.paragraph_format.first_line_indent = Cm(-0.55)
                p.paragraph_format.space_after = Pt(3)
                p.paragraph_format.tab_stops.add_tab_stop(Cm(indent))
                if k == "bullet":
                    p.add_run("•\t")
                else:
                    list_counter += 1
                    p.add_run(f"{block.data['n']}.\t")
                add_inline(p, block.text, self.reg)
            elif k == "fig":
                self.figure(block)
            elif k == "table":
                self.table(block)
            elif k == "eq":
                self.equation(block, unit)
            elif k == "code":
                self.code(block.text)
            elif k == "pagebreak":
                self.page_break()

    def figure(self, block):
        path = FIG / block.data["file"]
        if not path.exists():
            print("WARNING missing figure", path)
            self.para(f"[Missing figure: {block.data['file']}]", align=WD_ALIGN_PARAGRAPH.CENTER)
        else:
            from PIL import Image
            with Image.open(path) as im:
                w, h = im.size
            width = TEXT_WIDTH_CM
            if width * h / w > MAX_FIG_H_CM:
                width = MAX_FIG_H_CM * w / h
            p = self.doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_before = Pt(6)
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.keep_with_next = True
            p.add_run().add_picture(str(path), width=Cm(width))
        cap = self.doc.add_paragraph(style="Figure Caption")
        r = cap.add_run(f"Figure {block.data['num']}: ")
        r.bold = True
        add_inline(cap, block.text, self.reg, size=10.5)

    def table(self, block):
        cap = self.doc.add_paragraph(style="Table Caption")
        cap.paragraph_format.keep_with_next = True
        cap.paragraph_format.space_after = Pt(4)
        if "num" in block.data:
            r = cap.add_run(f"Table {block.data['num']}: ")
            r.bold = True
            add_inline(cap, block.text, self.reg, size=10.5)
        else:
            cap._p.getparent().remove(cap._p)
        rows = block.data["rows"]
        ncols = max(len(r) for r in rows)
        table = self.doc.add_table(rows=0, cols=ncols)
        table.style = "Table Grid"
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        size = 10 if ncols <= 4 else 9
        for i, row in enumerate(rows):
            cells = table.add_row().cells
            for j in range(ncols):
                text = row[j] if j < len(row) else ""
                p = cells[j].paragraphs[0]
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                p.paragraph_format.line_spacing = 1.0
                p.paragraph_format.space_after = Pt(1)
                add_inline(p, text, self.reg, size=size, base_bold=(i == 0))
                if i == 0:
                    set_cell_shading(cells[j], "E8EEF7")
        # repeat header row
        tr_pr = table.rows[0]._tr.get_or_add_trPr()
        hdr = OxmlElement("w:tblHeader")
        hdr.set(qn("w:val"), "true")
        tr_pr.append(hdr)
        spacer = self.doc.add_paragraph()
        spacer.paragraph_format.space_after = Pt(6)
        spacer.paragraph_format.line_spacing = 0.6

    def equation(self, block, unit):
        name = f"eq_{block.data['num'].replace('.', '_')}"
        path = render_equation(block.text, name)
        from PIL import Image
        with Image.open(path) as im:
            w, h = im.size
        width_cm = min(13.0, w / 300 * 2.54)
        p = self.doc.add_paragraph()
        p.paragraph_format.tab_stops.add_tab_stop(Cm(TEXT_WIDTH_CM / 2), WD_TAB_ALIGNMENT.CENTER)
        p.paragraph_format.tab_stops.add_tab_stop(Cm(TEXT_WIDTH_CM), WD_TAB_ALIGNMENT.RIGHT)
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.add_run("\t")
        p.add_run().add_picture(str(path), width=Cm(width_cm))
        p.add_run(f"\t({block.data['num']})")
        p.paragraph_format.space_before = Pt(4)
        p.paragraph_format.space_after = Pt(8)

    def code(self, text):
        lines = text.split("\n")
        for idx, line in enumerate(lines):
            p = self.doc.add_paragraph(style="Code Block")
            p.add_run(line if line else " ")
            p_pr = p._p.get_or_add_pPr()
            shd = OxmlElement("w:shd")
            shd.set(qn("w:val"), "clear")
            shd.set(qn("w:color"), "auto")
            shd.set(qn("w:fill"), "F4F4F2")
            p_pr.append(shd)
            if idx == 0:
                p.paragraph_format.space_before = Pt(4)
            if idx == len(lines) - 1:
                p.paragraph_format.space_after = Pt(8)
            else:
                p.paragraph_format.keep_with_next = len(lines) < 25

    def references(self):
        self.page_break()
        h = self.doc.add_paragraph(style="Heading 1")
        h.paragraph_format.space_before = Pt(36)
        h.add_run("References")
        for idx, key in enumerate(self.reg.cite_order, start=1):
            p = self.doc.add_paragraph()
            p.paragraph_format.left_indent = Cm(1.0)
            p.paragraph_format.first_line_indent = Cm(-1.0)
            p.paragraph_format.space_after = Pt(4)
            p.paragraph_format.line_spacing = 1.0
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.tab_stops.add_tab_stop(Cm(1.0))
            p.add_run(f"[{idx}]\t")
            add_inline(p, self.reg.references[key]["ieee"], self.reg, size=11)

    # ------------------------------------------------------------- build
    def build(self):
        self.title_page()
        self.front_pages()
        front_units = [u for u in self.units if u.kind == "front"]
        for unit in front_units:  # acknowledgement, abstract-like pages before the lists
            if unit.path.stem.startswith("00_") and "abbrev" not in unit.path.stem:
                self.front_heading(unit.title.upper())
                self.blocks(unit.blocks, unit)
                if "acknowledgement" in unit.path.stem:
                    self.para("")
                    self.candidate_table()
                    self.date_place()
                self.page_break()
        self.lists(front_units)
        for unit in front_units:
            if "abbrev" in unit.path.stem:
                self.front_heading(unit.title)
                self.blocks(unit.blocks, unit)
        self.body_with_refs()
        settings = self.doc.settings.element
        upd = OxmlElement("w:updateFields")
        upd.set(qn("w:val"), "false")
        settings.append(upd)
        return self.doc

    def body_with_refs(self):
        sec = self.doc.add_section(WD_SECTION.NEW_PAGE)
        self.header_footer(sec, True)
        page_number_format(sec, "decimal", 1)
        chapters = [u for u in self.units if u.kind == "chapter"]
        appendices = [u for u in self.units if u.kind == "appendix"]
        for idx, unit in enumerate(chapters):
            if idx:
                self.page_break()
            self.unit(unit)
        self.references()
        for unit in appendices:
            self.page_break()
            self.unit(unit)


# ============================================================ page discovery
def to_pdf(docx: Path) -> Path:
    out_dir = docx.parent
    subprocess.run([str(SOFFICE), "--headless", "--convert-to", "pdf", "--outdir", str(out_dir), str(docx)],
                   check=True, capture_output=True, timeout=600)
    return out_dir / (docx.stem + ".pdf")


def discover_pages(pdf: Path, units, reg) -> dict:
    doc = fitz.open(pdf)
    texts = [page.get_text("text") for page in doc]
    norm = [re.sub(r"\s+", " ", t) for t in texts]
    # body starts at the page that contains "Chapter 1" as a heading line after the lists
    first_chapter = next(u.number for u in units if u.kind == "chapter")
    body_start = next(i for i, t in enumerate(texts)
                      if re.search(rf"^Chapter {first_chapter}\s*$", t, re.M) and "Contents" not in t[:200])
    pages = {}

    def roman(n):
        vals = [(10, "x"), (9, "ix"), (5, "v"), (4, "iv"), (1, "i")]
        out = ""
        for v, s in vals:
            while n >= v:
                out += s
                n -= v
        return out

    # front matter: first front page after title has roman i
    for title in ["Statement of Candidate", "Approval Sheet", "Certificate", "Acknowledgement",
                  "List of Figures", "List of Tables", "List of Abbreviations"]:
        for i in range(1, body_start):
            head = "\n" + texts[i][:500]
            if re.search(rf"\n(?:{re.escape(title)}|{re.escape(title.upper())})\s*\n", head):
                pages[("front", title)] = roman(i)
                break
    cursor = body_start
    for unit in units:
        if unit.kind not in ("chapter", "appendix"):
            continue
        label = f"Chapter {unit.number}" if unit.kind == "chapter" else f"Appendix {unit.number}"
        for i in range(cursor, len(texts)):
            if re.search(rf"^{re.escape(label)}\s*$", texts[i], re.M):
                pages[("h1", unit.number)] = str(i - body_start + 1)
                cursor = i
                break
        for block in unit.blocks:
            if block.kind in ("h2", "h3", "fig", "table") and "num" in block.data:
                if block.kind in ("h2", "h3"):
                    needle = f"{block.data['num']} {block.text}"[:40]
                    key = ("h", block.data["num"])
                elif block.kind == "fig":
                    needle = f"Figure {block.data['num']}:"
                    key = ("fig", block.data["num"])
                else:
                    needle = f"Table {block.data['num']}:"
                    key = ("tab", block.data["num"])
                needle = re.sub(r"\s+", " ", needle)
                needle = re.sub(r"[*`]", "", needle)
                for i in range(cursor, len(norm)):
                    if needle in norm[i]:
                        pages[key] = str(i - body_start + 1)
                        cursor = i
                        break
        if unit.kind == "chapter" and unit is [u for u in units if u.kind == "chapter"][-1]:
            for i in range(cursor, len(texts)):
                if re.search(r"^References\s*$", texts[i], re.M):
                    pages[("h1", "References")] = str(i - body_start + 1)
                    break
    pages["_total"] = len(texts)
    pages["_body_start"] = body_start
    return pages


def main():
    units = load_units()
    references = json.loads((MD / "references.json").read_text(encoding="utf-8")) if (MD / "references.json").exists() else {}
    reg = Registry(units, references)
    doc = Builder(units, reg, None).build()
    doc.save(OUT_DOCX)
    print("pass 1 saved", OUT_DOCX)
    if "--pdf" not in sys.argv:
        return
    pdf = to_pdf(OUT_DOCX)
    pages = discover_pages(pdf, units, reg)
    units = load_units()
    reg = Registry(units, references)
    doc = Builder(units, reg, pages).build()
    doc.save(OUT_DOCX)
    pdf = to_pdf(OUT_DOCX)
    final = fitz.open(pdf)
    unresolved = [k for k in [("h1", u.number) for u in units if u.kind in ("chapter", "appendix")] if k not in pages]
    print(f"pass 2 saved {OUT_DOCX}; PDF pages: {len(final)} (body starts at PDF page {pages['_body_start'] + 1})")
    if unresolved:
        print("unresolved page numbers:", unresolved)
    (REPORT / "build").mkdir(exist_ok=True)
    (REPORT / "build" / "pages.json").write_text(json.dumps({"|".join(k) if isinstance(k, tuple) else k: v for k, v in pages.items()}, indent=1))


if __name__ == "__main__":
    main()
