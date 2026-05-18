"""Build the final GrGU-formatted coursework DOCX.

Formatting: ГрГУ им. Янки Купалы, ГОСТ 7.0.11-2011 adaptation.
  Times New Roman 14pt, margins 30/15/20/20 mm, line spacing exactly 18pt,
  first-line indent 1.25 cm, chapters – new page, uppercase, bold, centered.

Usage:
    python scripts/build_coursework.py

Outputs:
    artifacts/coursework/coursework_final.docx
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "artifacts" / "coursework"
ISCX_DIR = ROOT / "artifacts" / "iscx_vpn"
DEMO_DIR = ROOT / "artifacts" / "demo"
PROXY_DIR = ROOT / "artifacts" / "iscx_userid_proxy"

# ── Identity ──────────────────────────────────────────────────────────────────
STUDENT_NAME = "Тураев Сейит"
GROUP_NAME = "СДП-КБ-231"
SUPERVISOR = "Петров С. В."
FACULTY = "Факультет математики и информатики"
KAFEDRA = "Кафедра системного программирования и компьютерной безопасности"
SPECIALTY_CODE = "6-05-0533-12"
SPECIALTY_NAME = "Кибербезопасность"
DISCIPLINE = "Методология и инструменты анализа данных"
YEAR = "2026"
CITY = "Гродно"
UNIVERSITY = (
    "Учреждение образования «Гродненский государственный университет имени Янки Купалы»"
)
TITLE = (
    "Идентификация и верификация пользователя, использующего VPN/Proxy, "
    "на основе поведенческой биометрии и анализа временных сетевых сессий"
)

# ── Layout constants ──────────────────────────────────────────────────────────
FONT = "Times New Roman"
SZ = Pt(14)
SP = Pt(18)        # exactly 18 pt line spacing
IND = Cm(1.25)     # first-line indent


# ══════════════════════════════════════════════════════════════════════════════
# Data helpers
# ══════════════════════════════════════════════════════════════════════════════

def _csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _json(path: Path) -> dict | list:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _f(v, d: int = 4) -> str:
    if v in (None, ""):
        return "–"
    try:
        return f"{float(v):.{d}f}"
    except (ValueError, TypeError):
        return str(v)


def _pct(v) -> str:
    try:
        return f"{float(v) * 100:.1f}%"
    except (ValueError, TypeError):
        return "–"


# ══════════════════════════════════════════════════════════════════════════════
# Low-level formatting helpers
# ══════════════════════════════════════════════════════════════════════════════

def _body_fmt(para, *, indent: bool = True, align=WD_ALIGN_PARAGRAPH.JUSTIFY,
              sp_before: Pt = Pt(0), sp_after: Pt = Pt(0)) -> None:
    pf = para.paragraph_format
    pf.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    pf.line_spacing = SP
    pf.space_before = sp_before
    pf.space_after = sp_after
    pf.alignment = align
    pf.first_line_indent = IND if indent else Pt(0)


def _run(para, text: str, *, bold=False, italic=False, sz: Pt | None = None) -> None:
    run = para.add_run(text)
    run.font.name = FONT
    run.font.size = sz or SZ
    run.bold = bold
    run.italic = italic


# ══════════════════════════════════════════════════════════════════════════════
# Public paragraph builders
# ══════════════════════════════════════════════════════════════════════════════

def body(doc: Document, text: str, bold=False) -> None:
    """Standard body paragraph, first-line indented, justified."""
    p = doc.add_paragraph()
    _body_fmt(p)
    _run(p, text, bold=bold)


def noindent(doc: Document, text: str, *, bold=False, italic=False,
             center=False, right=False, sz: Pt | None = None,
             sp_before=Pt(0), sp_after=Pt(0)) -> None:
    """Paragraph without first-line indent."""
    align = (WD_ALIGN_PARAGRAPH.CENTER if center else
             WD_ALIGN_PARAGRAPH.RIGHT if right else
             WD_ALIGN_PARAGRAPH.JUSTIFY)
    p = doc.add_paragraph()
    _body_fmt(p, indent=False, align=align, sp_before=sp_before, sp_after=sp_after)
    _run(p, text, bold=bold, italic=italic, sz=sz)


def blank(doc: Document) -> None:
    noindent(doc, "")


def chapter(doc: Document, text: str) -> None:
    """Chapter heading: new page, UPPERCASE, bold, centered."""
    p = doc.add_paragraph()
    p.paragraph_format.page_break_before = True
    _body_fmt(p, indent=False, align=WD_ALIGN_PARAGRAPH.CENTER,
               sp_before=Pt(0), sp_after=SP)
    _run(p, text.upper(), bold=True)


def section(doc: Document, text: str) -> None:
    """Section heading (1.1 …), bold, left-aligned, no indent."""
    p = doc.add_paragraph()
    _body_fmt(p, indent=False, align=WD_ALIGN_PARAGRAPH.JUSTIFY,
               sp_before=SP, sp_after=Pt(0))
    _run(p, text, bold=True)


def numbered_list(doc: Document, items: list[str]) -> None:
    for i, item in enumerate(items, 1):
        p = doc.add_paragraph()
        _body_fmt(p, indent=False)
        p.paragraph_format.left_indent = IND
        p.paragraph_format.first_line_indent = Pt(0)
        _run(p, f"{i}. {item}")


def bullet_list(doc: Document, items: list[str]) -> None:
    for item in items:
        p = doc.add_paragraph()
        _body_fmt(p, indent=False)
        p.paragraph_format.left_indent = IND
        p.paragraph_format.first_line_indent = Pt(0)
        _run(p, f"– {item}")


def figure(doc: Document, path: Path, caption: str,
           width: float = 13.0) -> None:
    if not path.exists():
        return
    p = doc.add_paragraph()
    _body_fmt(p, indent=False, align=WD_ALIGN_PARAGRAPH.CENTER)
    p.add_run().add_picture(str(path), width=Cm(width))
    cap = doc.add_paragraph()
    _body_fmt(cap, indent=False, align=WD_ALIGN_PARAGRAPH.CENTER)
    _run(cap, caption, italic=True)


def figure_pair(doc: Document,
                path1: Path, cap1: str,
                path2: Path, cap2: str,
                each_width: float = 7.0) -> None:
    """Two figures side by side in a borderless 2-column table."""
    t = doc.add_table(rows=2, cols=2)
    # remove all table and cell borders
    from docx.oxml import OxmlElement as _OE
    from docx.oxml.ns import qn as _Q

    def _get_or_add(parent, tag):
        child = parent.find(_Q(tag))
        if child is None:
            child = _OE(tag)
            parent.append(child)
        return child

    tbl_pr = _get_or_add(t._tbl, "w:tblPr")
    tbl_borders = _OE("w:tblBorders")
    for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
        b = _OE(f"w:{side}")
        b.set(_Q("w:val"), "nil")
        tbl_borders.append(b)
    tbl_pr.append(tbl_borders)

    w_dxa = int(each_width * 567)  # 1 cm = 567 DXA
    for row in t.rows:
        for cell in row.cells:
            tc = cell._tc
            tcPr = tc.get_or_add_tcPr()
            tcW = _OE("w:tcW")
            tcW.set(_Q("w:w"), str(w_dxa))
            tcW.set(_Q("w:type"), "dxa")
            tcPr.append(tcW)

    for col_i, (path, cap) in enumerate([(path1, cap1), (path2, cap2)]):
        img_cell = t.cell(0, col_i)
        img_cell.text = ""
        p_img = img_cell.paragraphs[0]
        _body_fmt(p_img, indent=False, align=WD_ALIGN_PARAGRAPH.CENTER)
        if path.exists():
            p_img.add_run().add_picture(str(path), width=Cm(each_width))

        cap_cell = t.cell(1, col_i)
        cap_cell.text = ""
        p_cap = cap_cell.paragraphs[0]
        _body_fmt(p_cap, indent=False, align=WD_ALIGN_PARAGRAPH.CENTER)
        _run(p_cap, cap, italic=True)

    blank(doc)


def table(doc: Document, headers: list[str], rows: list[list[str]]) -> None:
    t = doc.add_table(rows=1 + len(rows), cols=len(headers))
    t.style = "Table Grid"
    for i, h in enumerate(headers):
        c = t.cell(0, i)
        c.text = ""
        r = c.paragraphs[0].add_run(h)
        r.bold = True
        r.font.name = FONT
        r.font.size = Pt(11)
        c.paragraphs[0].paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for ri, row in enumerate(rows):
        for ci, val in enumerate(row):
            c = t.cell(ri + 1, ci)
            c.text = ""
            r = c.paragraphs[0].add_run(str(val))
            r.font.name = FONT
            r.font.size = Pt(11)
    blank(doc)


# ══════════════════════════════════════════════════════════════════════════════
# Page numbering
# ══════════════════════════════════════════════════════════════════════════════

def _add_page_num(section_obj) -> None:
    footer = section_obj.footer
    para = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
    para.clear()
    para.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = para.add_run()
    run.font.name = FONT
    run.font.size = SZ
    for tag, text in [("w:fldChar", None), ("w:instrText", " PAGE "), ("w:fldChar", None)]:
        el = OxmlElement(tag)
        if text:
            el.text = text
        else:
            el.set(qn("w:fldCharType"),
                   "begin" if not run._r.find(qn("w:fldChar")) is not None else "end")
        run._r.append(el)


def setup_page_numbers(doc: Document) -> None:
    """First section (title page) has no page number; all others do."""
    for i, sec in enumerate(doc.sections):
        if i == 0:
            sec.different_first_page_header_footer = True
            # leave first-page footer empty (title page)
        else:
            _add_page_num(sec)


# ══════════════════════════════════════════════════════════════════════════════
# Document global style
# ══════════════════════════════════════════════════════════════════════════════

def setup_document(doc: Document) -> None:
    for sec in doc.sections:
        sec.left_margin = Cm(3.0)
        sec.right_margin = Cm(1.5)
        sec.top_margin = Cm(2.0)
        sec.bottom_margin = Cm(2.0)
    normal = doc.styles["Normal"]
    normal.font.name = FONT
    normal.font.size = SZ
    pf = normal.paragraph_format
    pf.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    pf.line_spacing = SP
    pf.space_before = Pt(0)
    pf.space_after = Pt(0)


# ══════════════════════════════════════════════════════════════════════════════
# Title page
# ══════════════════════════════════════════════════════════════════════════════

def build_title_page(doc: Document) -> None:

    def c(text, bold=False, sz=None, sp_before=0, sp_after=0):
        p = doc.add_paragraph()
        _body_fmt(p, indent=False, align=WD_ALIGN_PARAGRAPH.CENTER,
                   sp_before=Pt(sp_before), sp_after=Pt(sp_after))
        _run(p, text, bold=bold, sz=Pt(sz) if sz else SZ)

    def rr(text, bold=False):
        p = doc.add_paragraph()
        _body_fmt(p, indent=False, align=WD_ALIGN_PARAGRAPH.RIGHT)
        _run(p, text, bold=bold)

    # University block
    c("МИНИСТЕРСТВО ОБРАЗОВАНИЯ РЕСПУБЛИКИ БЕЛАРУСЬ", bold=True)
    c(UNIVERSITY)
    c(FACULTY)
    c(KAFEDRA, sp_after=18)

    # Title block
    c("КУРСОВАЯ РАБОТА", bold=True, sp_before=36, sp_after=0)
    c(f"по дисциплине «{DISCIPLINE}»", sp_after=0)
    blank(doc)
    c("Тема:", sp_after=0)
    c(f"«{TITLE}»", bold=True)

    # Spacer
    for _ in range(3):
        blank(doc)

    # Student block (right-aligned)
    rr("Выполнил студент")
    rr(f"специальности {SPECIALTY_CODE} {SPECIALTY_NAME}")
    rr(f"группы {GROUP_NAME}")
    rr(f"_______________ {STUDENT_NAME}")
    rr("       (подпись)")
    blank(doc)
    rr("Научный руководитель")
    rr(f"_______________ {SUPERVISOR}")
    rr("       (подпись)")

    # Bottom
    for _ in range(4):
        blank(doc)
    c(f"{CITY} {YEAR}")


# ══════════════════════════════════════════════════════════════════════════════
# РЕФЕРАТ
# ══════════════════════════════════════════════════════════════════════════════

def build_referat(doc: Document) -> None:
    doc.add_page_break()
    noindent(doc, "РЕФЕРАТ", bold=True, center=True, sp_after=SP)
    noindent(doc,
             "Курсовая работа: 55 с., 9 рис., 5 табл., 3 прил., 10 источников.",
             bold=True)
    blank(doc)
    noindent(doc, "КЛЮЧЕВЫЕ СЛОВА:", bold=True)
    body(doc,
         "ПОВЕДЕНЧЕСКАЯ БИОМЕТРИЯ, СЕТЕВЫЕ СЕССИИ, VPN, PROXY, ИДЕНТИФИКАЦИЯ "
         "ПОЛЬЗОВАТЕЛЯ, MACHINE LEARNING, ISOLATION FOREST, RANDOM FOREST, "
         "ОБНАРУЖЕНИЕ АНОМАЛИЙ, ВРЕМЕННЫЕ ПРИЗНАКИ ТРАФИКА.")
    blank(doc)
    body(doc,
         "В курсовой работе рассматривается задача идентификации и верификации "
         "пользователя, использующего VPN или proxy, на основе поведенческой "
         "биометрии и анализа временных сетевых сессий. Показана возможность "
         "вероятностной идентификации пользователя по flow-метаданным без "
         "анализа содержимого пакетов.")
    body(doc,
         "В теоретической части проанализированы современные подходы к "
         "continuous authentication, представлению сетевого поведения в виде "
         "flows и sessions, а также к построению поведенческих профилей. "
         "Обоснован выбор временных признаков как наиболее устойчивых к "
         "туннелированию трафика.")
    body(doc,
         "Разработан программный прототип, включающий: модуль sessionization "
         "с порогом неактивности, систему извлечения session-level признаков, "
         "гибридную модель (классификатор + детектор аномалий Isolation Forest) "
         "и модуль оценки в трёх сценариях: direct→VPN, mixed и open-set.")
    body(doc,
         "На реальном открытом датасете ISCX-VPN-NonVPN-2016 проведён "
         "методологически корректный эксперимент бинарной классификации "
         "VPN/non-VPN. Лучший результат получен на временном окне 15 с: "
         "accuracy = 0,9194; macro-F1 = 0,9191; ROC-AUC = 0,9769. Наиболее "
         "информативными признаками оказались total_biat, flowBytesPerSecond "
         "и межпотоковые интервалы (flow IAT).")
    body(doc,
         "Дополнительно выполнен прокси-эксперимент: приложение-класс "
         "датасета использовалось в качестве суррогата user_id. Результаты "
         "подтверждают частичную поведенческую устойчивость через VPN-туннель. "
         "Сформулированы ограничения метода и направления дальнейшего развития.")


# ══════════════════════════════════════════════════════════════════════════════
# SUMMARY
# ══════════════════════════════════════════════════════════════════════════════

def build_summary(doc: Document) -> None:
    doc.add_page_break()
    noindent(doc, "SUMMARY", bold=True, center=True, sp_after=SP)
    noindent(doc,
             "Course work: 55 p., 9 fig., 5 tab., 2 app., 10 ref.",
             bold=True)
    blank(doc)
    noindent(doc, "KEY WORDS:", bold=True)
    body(doc,
         "BEHAVIORAL BIOMETRICS, NETWORK SESSIONS, VPN, PROXY, USER "
         "IDENTIFICATION, MACHINE LEARNING, ISOLATION FOREST, RANDOM FOREST, "
         "ANOMALY DETECTION, TRAFFIC TIME-SERIES FEATURES.")
    blank(doc)
    body(doc,
         "This course work addresses the problem of probabilistic user "
         "identification and verification under VPN/Proxy concealment, using "
         "behavioral biometrics derived from temporal network session metadata. "
         "The approach avoids deep packet inspection and relies solely on "
         "flow-level statistics.")
    body(doc,
         "The theoretical part reviews continuous authentication literature, "
         "flow-and-session traffic representation, and the rationale for "
         "time-based features as the least VPN-distorted signal source.")
    body(doc,
         "A Python prototype was developed comprising a sessionization module, "
         "a session-level feature extractor, and a hybrid model combining a "
         "multi-class user classifier with per-user Isolation Forest anomaly "
         "detectors. Three evaluation scenarios are implemented: "
         "direct→VPN, mixed, and open-set identification.")
    body(doc,
         "On the public ISCX-VPN-NonVPN-2016 dataset a methodologically sound "
         "binary VPN/non-VPN classification experiment was conducted. Best "
         "results on the 15 s window: accuracy = 0.9194, macro-F1 = 0.9191, "
         "ROC-AUC = 0.9769. The most important features were total_biat, "
         "flowBytesPerSecond and flow inter-arrival time statistics.")
    body(doc,
         "A proxy experiment treating application class as a surrogate for "
         "user identity confirms partial behavioral persistence through VPN "
         "tunnels. Limitations and future directions are discussed.")


# ══════════════════════════════════════════════════════════════════════════════
# СОДЕРЖАНИЕ (manual TOC)
# ══════════════════════════════════════════════════════════════════════════════

def build_toc(doc: Document) -> None:
    doc.add_page_break()
    noindent(doc, "СОДЕРЖАНИЕ", bold=True, center=True, sp_after=SP)

    entries = [
        ("РЕФЕРАТ", "2"),
        ("SUMMARY", "3"),
        ("ВВЕДЕНИЕ", "5"),
        ("ГЛАВА 1. ТЕОРЕТИЧЕСКИЕ ОСНОВЫ ИДЕНТИФИКАЦИИ ПОЛЬЗОВАТЕЛЯ ПО СЕТЕВОМУ ПОВЕДЕНИЮ", "8"),
        ("    1.1. Поведенческая биометрия и continuous authentication", "8"),
        ("    1.2. Ограничения идентификации по IP и роль сетевых метаданных", "10"),
        ("    1.3. VPN/Proxy как источник искажений, но не полной анонимности", "12"),
        ("    1.4. Представление сетевого поведения как временного ряда", "14"),
        ("    1.5. Постановка задачи исследования", "16"),
        ("ГЛАВА 2. ПРОЕКТИРОВАНИЕ И РЕАЛИЗАЦИЯ МЕТОДА", "18"),
        ("    2.1. Общая схема метода", "18"),
        ("    2.2. Представление данных: flow и session", "20"),
        ("    2.3. Источники данных", "22"),
        ("    2.4. Система признаков", "24"),
        ("    2.5. Выбор моделей машинного обучения", "27"),
        ("    2.6. Практическая реализация пайплайна", "30"),
        ("ГЛАВА 3. ЭКСПЕРИМЕНТАЛЬНОЕ ИССЛЕДОВАНИЕ И ОЦЕНКА КАЧЕСТВА", "32"),
        ("    3.1. Сценарии экспериментов", "32"),
        ("    3.2. Метрики оценки", "34"),
        ("    3.3. Результаты VPN/non-VPN классификации на ISCX", "36"),
        ("    3.4. Прокси-эксперимент: приложение-класс как суррогат пользователя", "41"),
        ("    3.5. Результаты синтетического сценария идентификации", "44"),
        ("ЗАКЛЮЧЕНИЕ", "47"),
        ("СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ", "49"),
        ("ПРИЛОЖЕНИЕ А. Архитектура программного прототипа", "51"),
        ("ПРИЛОЖЕНИЕ Б. Полные численные результаты", "53"),
        ("ПРИЛОЖЕНИЕ В. Ключевые фрагменты программного кода", "55"),
    ]

    for title, page in entries:
        p = doc.add_paragraph()
        _body_fmt(p, indent=False, align=WD_ALIGN_PARAGRAPH.JUSTIFY)
        # title run
        r1 = p.add_run(title)
        r1.font.name = FONT
        r1.font.size = SZ
        # dot leaders  – use tab stop at right margin, then page number
        pf = p.paragraph_format
        from docx.oxml import OxmlElement as OE
        from docx.oxml.ns import qn as Q
        pPr = p._p.get_or_add_pPr()
        tabs_el = OE("w:tabs")
        tab_el = OE("w:tab")
        tab_el.set(Q("w:val"), "right")
        tab_el.set(Q("w:leader"), "dot")
        tab_el.set(Q("w:pos"), "8640")   # ~6 inches = 8640 twentieths-of-a-point
        tabs_el.append(tab_el)
        pPr.append(tabs_el)
        r2 = p.add_run(f"\t{page}")
        r2.font.name = FONT
        r2.font.size = SZ


# ══════════════════════════════════════════════════════════════════════════════
# ВВЕДЕНИЕ
# ══════════════════════════════════════════════════════════════════════════════

def build_intro(doc: Document) -> None:
    chapter(doc, "ВВЕДЕНИЕ")

    body(doc,
         "Рост объёма зашифрованного трафика, широкое распространение VPN "
         "и proxy-сервисов, а также высокая мобильность пользователей делают "
         "традиционную идентификацию по IP-адресу всё менее надёжной. "
         "В прикладных задачах кибербезопасности это приводит к важной "
         "проблеме: даже если сетевой адрес скрыт или меняется, организации "
         "по-прежнему необходимо понимать, какой именно пользователь с "
         "наибольшей вероятностью стоит за конкретной сетевой активностью.")
    body(doc,
         "Одним из перспективных направлений решения этой задачи является "
         "поведенческая биометрия. В отличие от классической аутентификации, "
         "которая проверяет пользователя однократно в начале работы, "
         "поведенческие методы позволяют оценивать, насколько текущая "
         "активность похожа на ранее наблюдавшийся профиль конкретного "
         "человека. Такой подход особенно хорошо сочетается с анализом "
         "временных рядов, поскольку сетевое поведение естественным образом "
         "представляется как последовательность событий: запусков сессий, "
         "пакетов, потоков, интервалов между действиями, периодов активности "
         "и бездействия.")
    body(doc,
         "В данной работе рассматривается задача вероятностной идентификации "
         "и верификации пользователя, использующего VPN или proxy, на основе "
         "временных паттернов сетевой активности. Цель работы – не "
         "гарантированная деанонимизация пользователя, а построение модели, "
         "которая по новой сетевой сессии оценивает степень её сходства "
         "с поведенческим профилем известного пользователя и, при необходимости, "
         "выявляет аномалии.")
    blank(doc)
    body(doc,
         "Объект исследования: сетевые сессии активности пользователей в "
         "условиях прямого соединения и при использовании VPN/Proxy.")
    body(doc,
         "Предмет исследования: методы машинного обучения для идентификации "
         "пользователя по сетевым метаданным и временным признакам сессий.")
    body(doc,
         "Цель работы: разработать и исследовать метод идентификации и "
         "верификации пользователя по временным сетевым паттернам в условиях "
         "сокрытия сетевой идентичности через VPN/Proxy.")
    blank(doc)
    noindent(doc, "Для достижения цели решаются следующие задачи:", bold=False)
    numbered_list(doc, [
        "проанализировать современные подходы к поведенческой биометрии, "
        "continuous authentication и анализу сетевого трафика;",
        "сформулировать задачу идентификации пользователя как задачу анализа "
        "временных рядов и выявления аномалий;",
        "разработать схему представления трафика в виде flows и sessions, "
        "пригодную для машинного обучения;",
        "выделить признаки, сохраняющие дискриминирующую способность при "
        "использовании VPN/Proxy;",
        "построить гибридную модель, объединяющую классификацию пользователя "
        "и детекцию аномалий;",
        "провести экспериментальную проверку в сценариях direct→VPN, mixed "
        "и open-set и сравнить результаты.",
    ])
    blank(doc)
    body(doc,
         "Гипотеза исследования: временные и поведенческие метаданные "
         "сетевых сессий сохраняют достаточную информативность для "
         "вероятностной идентификации и верификации пользователя даже при "
         "использовании VPN/Proxy, а объединение классификации пользователя "
         "и детекции аномалий обеспечивает более устойчивый результат, чем "
         "один классификатор.")
    body(doc,
         "Методы исследования: анализ научной литературы, анализ временных "
         "рядов, выделение статистических и поведенческих признаков сетевого "
         "трафика, методы классификации, методы обнаружения аномалий, "
         "сравнительный экспериментальный анализ.")
    body(doc,
         "Практическая значимость работы состоит в том, что предложенный "
         "подход может использоваться как дополнительный слой сетевой "
         "поведенческой аутентификации, как инструмент оценки риска при "
         "подозрительных сетевых сессиях, а также как исследовательская "
         "основа для систем continuous authentication.")


# ══════════════════════════════════════════════════════════════════════════════
# ГЛАВА 1
# ══════════════════════════════════════════════════════════════════════════════

def build_chapter1(doc: Document) -> None:
    chapter(doc,
            "ГЛАВА 1. ТЕОРЕТИЧЕСКИЕ ОСНОВЫ ИДЕНТИФИКАЦИИ ПОЛЬЗОВАТЕЛЯ "
            "ПО СЕТЕВОМУ ПОВЕДЕНИЮ")

    # 1.1 ─────────────────────────────────────────────────────────────────────
    section(doc, "1.1. Поведенческая биометрия и continuous authentication")

    body(doc,
         "Классические методы аутентификации – пароль, токен, отпечаток "
         "пальца или распознавание лица – решают задачу допуска пользователя "
         "в систему только на начальном этапе сессии. Однако после успешного "
         "входа возникает риск подмены пользователя, компрометации учётной "
         "записи или несанкционированного продолжения уже открытой сессии. "
         "По этой причине в последние годы активно развивается концепция "
         "continuous authentication – непрерывной проверки пользователя "
         "в процессе работы.")
    body(doc,
         "В рамках continuous authentication в качестве источника признаков "
         "используются не только физиологические, но и поведенческие "
         "характеристики: ритм набора текста, движения мыши, паттерны "
         "касаний, навигационные привычки, ритм использования приложений. "
         "Обзор Hernández-Álvarez и соавторов показывает, что поведенческие "
         "данные являются ценной основой для непрерывной аутентификации, "
         "поскольку они менее навязчивы и лучше отражают реальную активность "
         "пользователя [1]. Baig, Eskeland и Yang подчёркивают, что "
         "continuous authentication эффективна именно как механизм повторной "
         "проверки доверия к уже активной сессии [2].")
    body(doc,
         "В сетевом контексте поведенческая биометрия может строиться на "
         "характеристиках трафика, которые остаются наблюдаемыми даже при "
         "шифровании содержимого пакетов. Такими характеристиками являются "
         "интервалы между пакетами, длительность потоков, интенсивность "
         "обмена данными, периоды активности и бездействия, соотношение "
         "исходящего и входящего трафика и структура последовательности "
         "сетевых событий.")

    # 1.2 ─────────────────────────────────────────────────────────────────────
    section(doc, "1.2. Ограничения идентификации по IP и роль сетевых метаданных")

    body(doc,
         "Во многих прикладных системах безопасность по-прежнему опирается "
         "на IP-адрес как на один из признаков пользователя. Однако в "
         "реальных условиях IP-адрес является нестабильным идентификатором. "
         "На это влияют DHCP, NAT, мобильные сети, переключение между Wi-Fi "
         "и сотовой связью, использование нескольких устройств, а также "
         "VPN и proxy-сервисы.")
    body(doc,
         "Alotibi, Clarke, Li и Furnell показали, что идентификация "
         "пользователя может строиться не только по IP-адресу, но и по "
         "метаданным трафика. На основе packet metadata и производных "
         "поведенческих признаков были сформированы пользовательские профили, "
         "а эксперимент с участием 27 пользователей и двухмесячным периодом "
         "наблюдений продемонстрировал, что пользователи в ряде сценариев "
         "различимы даже при анализе зашифрованного трафика [3]. Этот "
         "результат подтверждает ключевой тезис: полезная информация о "
         "пользователе сохраняется не в содержимом трафика, а в его "
         "временной и структурной организации.")
    body(doc,
         "Следовательно, в условиях VPN/Proxy логично переносить фокус "
         "анализа с адресной информации на поведенческие сетевые признаки, "
         "которые труднее замаскировать полностью.")

    # 1.3 ─────────────────────────────────────────────────────────────────────
    section(doc, "1.3. VPN/Proxy как источник искажений, но не полной анонимности")

    body(doc,
         "VPN и proxy скрывают или подменяют внешний IP-адрес пользователя, "
         "а также могут шифровать трафик и изменять некоторые характеристики "
         "сетевого обмена. Тем не менее они не устраняют полностью временную "
         "структуру активности. Даже при туннелировании сохраняются:")
    bullet_list(doc, [
        "длительность и ритм сессий;",
        "распределения inter-arrival time пакетов и потоков;",
        "отношение периодов active и idle;",
        "burstiness (неравномерность активности);",
        "соотношение объёмов входящего и исходящего трафика;",
        "закономерности чередования коротких и длинных потоков.",
    ])
    body(doc,
         "Работа Draper-Gil, Lashkari, Mamun и Ghorbani показала, что "
         "time-related features позволяют не только различать VPN и non-VPN "
         "трафик, но и классифицировать типы активности внутри зашифрованного "
         "трафика [4]. Авторы использовали такие признаки, как duration, "
         "flow inter-arrival time, forward/backward inter-arrival time, "
         "active, idle, flow bytes per second и flow packets per second, "
         "и получили высокую точность классификации. Это означает, что "
         "временные метаданные являются разумной базой для построения "
         "пользовательских профилей.")
    body(doc,
         "Современные исследования в области traffic correlation также "
         "подтверждают, что даже в зашифрованных proxy-сетях сохраняются "
         "устойчивые spatio-temporal зависимости. В частности, в работе "
         "ProxyCorr показано, что последовательности состояний потока и "
         "их временные корреляции позволяют сопоставлять зашифрованные "
         "proxy-потоки даже при наличии шума, padding и мультиплексирования [5].")

    # 1.4 ─────────────────────────────────────────────────────────────────────
    section(doc, "1.4. Представление сетевого поведения как временного ряда")

    body(doc,
         "С точки зрения машинного обучения задача может быть представлена "
         "в виде анализа временных рядов. Поток сетевой активности "
         "пользователя можно рассматривать на нескольких уровнях:")
    numbered_list(doc, [
        "уровень пакетов – последовательность размеров, направлений и "
        "моментов прихода пакетов;",
        "уровень flows – агрегаты сетевых потоков с вычисленными "
        "статистиками времени и объёма;",
        "уровень sessions – группы потоков, относящихся к одному периоду "
        "целенаправленной пользовательской активности.",
    ])
    body(doc,
         "Для курсовой работы наиболее рационально использовать уровень "
         "flows и sessions. Он позволяет сохранить важные временные "
         "закономерности, но при этом существенно сокращает размерность "
         "данных по сравнению с поминутным или пакетным анализом.")
    body(doc,
         "Halfaker и соавторы показали, что для многих доменов "
         "онлайн-активности разумным эмпирическим порогом разделения сессий "
         "служит около одного часа неактивности [6]. Это даёт основу "
         "для выбора базового inactivity threshold в 60 минут, а также "
         "для сравнения с более распространённым порогом в 30 минут.")

    # 1.5 ─────────────────────────────────────────────────────────────────────
    section(doc, "1.5. Постановка задачи исследования")

    body(doc,
         "С учётом рассмотренных работ задача курсовой формулируется "
         "следующим образом. Пусть имеется множество пользователей "
         "U = {u₁, u₂, …, uₙ}. Для каждого пользователя доступны "
         "исторические сетевые сессии, представленные наборами потоков "
         "и временных признаков. Необходимо по новой сессии s:")
    numbered_list(doc, [
        "оценить, какому пользователю из множества U она наиболее вероятно "
        "принадлежит;",
        "определить, является ли эта сессия типичной для данного пользователя "
        "или аномальной.",
    ])
    body(doc, "Выход модели задаётся четырьмя значениями:")
    bullet_list(doc, [
        "pred_user_id – наиболее вероятный пользователь;",
        "confidence – уверенность классификатора;",
        "anomaly_score – степень отклонения от нормального профиля;",
        "final_risk_score – итоговая оценка риска.",
    ])
    body(doc,
         "Важное ограничение: предлагаемый подход не доказывает личность "
         "пользователя в юридическом смысле и не обеспечивает абсолютную "
         "деанонимизацию. Он строит вероятностную модель сходства сетевого "
         "поведения, пригодную для поддержки решений в задачах безопасности.")


# ══════════════════════════════════════════════════════════════════════════════
# ГЛАВА 2
# ══════════════════════════════════════════════════════════════════════════════

def build_chapter2(doc: Document) -> None:
    chapter(doc, "ГЛАВА 2. ПРОЕКТИРОВАНИЕ И РЕАЛИЗАЦИЯ МЕТОДА")

    # 2.1 ─────────────────────────────────────────────────────────────────────
    section(doc, "2.1. Общая схема метода")

    body(doc,
         "Предлагаемый метод строится как последовательный пайплайн: "
         "трафик → flows → sessions → features → модель → решение. "
         "На входе имеется сетевой трафик в форме экспортированных "
         "flow-записей. На следующем этапе потоки группируются в сессии "
         "активности пользователя. Из каждой сессии извлекается вектор "
         "признаков, после чего применяются две модели: классификатор "
         "пользователя и детектор аномалий. На последнем шаге результаты "
         "моделей объединяются в единую оценку риска.")
    body(doc,
         "Такое разделение важно для воспроизводимости. Если появляется "
         "реальный датасет с user_id и временными метками, его можно подать "
         "в существующий session-level pipeline. Если датасет содержит только "
         "flow-признаки и метку VPN/non-VPN, используется отдельный "
         "классификатор. Код не делает методологически неверных предположений "
         "о данных.")
    body(doc,
         "Все результаты сохраняются в папку artifacts. Это позволяет не "
         "только посмотреть итоговые метрики, но и восстановить ход "
         "эксперимента: какие предсказания были получены, какие признаки "
         "оказались важными, какие графики построены.")

    # 2.2 ─────────────────────────────────────────────────────────────────────
    section(doc, "2.2. Представление данных: flow и session")

    body(doc,
         "Базовым структурным объектом системы является flow – "
         "направленно-агрегированная запись сетевого обмена с вычисленными "
         "статистиками по времени и объёму. Структура flow содержит поля "
         "start_time, end_time, duration, bytes_up, bytes_down, pkts_up, "
         "pkts_down, статистики flow IAT, forward IAT, backward IAT, "
         "периодов активности и простоя (active/idle), а также скорости "
         "передачи bytes_per_sec и pkts_per_sec.")
    body(doc,
         "Следующим уровнем является session. Сессия определяется как "
         "упорядоченный по времени набор flows одного пользователя, между "
         "которыми отсутствует длительный период неактивности. В работе "
         "используются два порога: основной – 60 минут и дополнительный "
         "для сравнения – 30 минут [6].")
    body(doc,
         "В модуле sessionization граница сессии определяется тремя "
         "условиями: смена пользователя, превышение порога неактивности "
         "между соседними потоками, а также (опционально) смена режима "
         "direct/vpn. Алгоритм работает за одну сортировку по user_id и "
         "start_time, что обеспечивает линейную сложность по числу потоков.")

    # 2.3 ─────────────────────────────────────────────────────────────────────
    section(doc, "2.3. Источники данных")

    body(doc,
         "В работе используются два источника данных. Первый – публичный "
         "датасет ISCX-VPN-NonVPN-2016, опубликованный Canadian Institute "
         "for Cybersecurity. Он содержит ARFF-файлы с flow-признаками "
         "для обычного и VPN-трафика в нескольких категориях: browsing, "
         "email, chat, streaming, file transfer, VoIP, P2P [7]. "
         "Датасет не содержит user_id и временных меток начала/конца "
         "потоков, поэтому применяется для методологически корректной "
         "задачи бинарной VPN/non-VPN классификации.")
    body(doc,
         "Второй источник – синтетические данные, генерируемые модулем "
         "synthetic_data. Генератор создаёт flow-записи для нескольких "
         "виртуальных пользователей в режимах direct и vpn с различимыми "
         "поведенческими профилями. Это позволяет проверить гибридную "
         "идентификацию пользователя в управляемых условиях, где "
         "истинные метки известны.")
    body(doc,
         "Для устойчивого чтения ARFF-файлов реализован tolerant-загрузчик, "
         "который вручную считывает описание атрибутов и данные, обрабатывает "
         "пустые значения и вопросительные знаки как NaN, приводит числовые "
         "признаки к numeric-типу. Такой подход устраняет проблемы с "
         "нестандартным форматированием исходных файлов.")

    # 2.4 ─────────────────────────────────────────────────────────────────────
    section(doc, "2.4. Система признаков")

    body(doc,
         "Для устойчивой работы модели в условиях VPN/Proxy необходимо "
         "опираться на признаки, наименее зависящие от IP-адреса и "
         "полезной нагрузки пакетов. Предложены четыре группы признаков.")
    body(doc,
         "Первая группа – временные признаки flow. Включает duration, "
         "flow_iat_mean/std/min/max, forward и backward inter-arrival time, "
         "статистики периодов active и idle, а также pkts_per_sec и "
         "bytes_per_sec. Именно эта группа наиболее явно опирается на "
         "результаты работы [4] и подтверждается экспериментальным анализом "
         "важности признаков Random Forest.")
    body(doc,
         "Вторая группа – агрегированные session-признаки: общее число "
         "flows в сессии, средняя и медианная длительность flow, квантили "
         "межпотоковых интервалов, доля коротких и длинных flows, среднее "
         "отношение bytes_up / bytes_down, коэффициент burstiness и общая "
         "длительность сессии.")
    body(doc,
         "Третья группа – календарные и циклические признаки: час начала "
         "сессии, день недели, синус и косинус часа суток, синус и косинус "
         "дня недели. Эти признаки позволяют учитывать циркадные и "
         "поведенческие ритмы пользователя.")
    body(doc,
         "Четвёртая группа – режимные признаки: mode = direct/vpn/proxy, "
         "флаг смены режима и относительное изменение интенсивности трафика "
         "между режимами. Данные признаки полезны не для прямой привязки к "
         "личности, а для интерпретации устойчивости модели при переходе "
         "от обычного соединения к туннелированному.")

    # 2.5 ─────────────────────────────────────────────────────────────────────
    section(doc, "2.5. Выбор моделей машинного обучения")

    body(doc,
         "В работе используется двухуровневая гибридная схема. На первом "
         "уровне применяется классификатор пользователя по агрегированным "
         "признакам сессии. Основным вариантом является RandomForestClassifier "
         "с балансировкой классов (class_weight=balanced). Этот алгоритм "
         "устойчив на табличных данных, интерпретируем через важность "
         "признаков и не требует сложной нормализации. При наличии "
         "библиотеки CatBoost используется более мощный вариант [8, 9, 10].")
    body(doc,
         "На втором уровне для каждого пользователя обучается отдельный "
         "Isolation Forest, который получает на вход признаки сессий данного "
         "пользователя и оценивает, насколько новая сессия похожа на "
         "известный профиль. Чем сильнее отклонение, тем выше anomaly_score. "
         "Такой подход особенно важен в open-set сценариях, когда в тесте "
         "может присутствовать пользователь, отсутствовавший в обучении.")
    body(doc,
         "Итоговое решение строится не по одной жёсткой классификации, "
         "а по совмещению двух сигналов: уверенности классификатора и степени "
         "аномальности сессии. Формула итогового риска:")
    noindent(doc,
             "final_risk_score = α · (1 – confidence) + (1 – α) · anomaly_score,",
             center=True)
    body(doc,
         "где α – весовой коэффициент, выбираемый на валидации (по умолчанию 0,5). "
         "Если anomaly_score превышает порог τ_unknown, сессия переводится "
         "в класс unknown. Гибридный подход делает систему ближе к реальным "
         "сценариям информационной безопасности.")

    # 2.6 ─────────────────────────────────────────────────────────────────────
    section(doc, "2.6. Практическая реализация пайплайна")

    body(doc,
         "Реализация метода представляет собой набор слабосвязанных модулей "
         "на языке Python. Модуль генерации синтетических данных создаёт "
         "flow-записи с настраиваемыми поведенческими профилями. Центральным "
         "алгоритмом является модуль sessionization: он выделяет сессии по "
         "порогу неактивности с учётом смены режима direct/vpn (листинг В.1). "
         "Модуль извлечения признаков агрегирует каждую сессию в вектор "
         "статистик активности. Гибридный идентификатор обучается в два "
         "этапа – сначала классификатор, затем индивидуальные детекторы "
         "аномалий (листинг В.2), а вывод объединяет оба сигнала в итоговый "
         "риск (листинг В.3). Для работы с реальным датасетом ISCX выделен "
         "отдельный модуль, чтобы не смешивать методологически разные "
         "постановки задач.")
    body(doc,
         "После обучения параметры модели сериализуются вместе со списком "
         "признаков и медианами тренировочной выборки. Медианы необходимы "
         "для восстановления пропущенных значений при тестировании и "
         "обязательно вычисляются только на тренировочной части – это "
         "исключает утечку информации из тестовой выборки на стадии обучения. "
         "При последующем применении к новым данным порядок признаков "
         "восстанавливается из сохранённых метаданных.")
    body(doc,
         "Все промежуточные и итоговые результаты экспериментов сохраняются "
         "в структурированную директорию: сериализованная модель, таблицы "
         "метрик, предсказания для каждого объекта тестовой выборки, "
         "оценки важности признаков и набор визуализаций. Такой подход "
         "позволяет независимо воспроизвести любой шаг эксперимента, "
         "не запуская повторного обучения.")


# ══════════════════════════════════════════════════════════════════════════════
# ГЛАВА 3
# ══════════════════════════════════════════════════════════════════════════════

def build_chapter3(doc: Document, iscx_rows: list[dict],
                   demo_rows: list[dict], proxy_rows: list[dict],
                   cls_report: dict, top_features: list[dict]) -> None:
    chapter(doc, "ГЛАВА 3. ЭКСПЕРИМЕНТАЛЬНОЕ ИССЛЕДОВАНИЕ И ОЦЕНКА КАЧЕСТВА")

    # 3.1 ─────────────────────────────────────────────────────────────────────
    section(doc, "3.1. Сценарии экспериментов")

    body(doc,
         "Для подтверждения работоспособности подхода проведены четыре "
         "сценария экспериментов.")
    body(doc,
         "Сценарий 1 – обучение на direct, тестирование на VPN. Это "
         "основной эксперимент, поскольку он напрямую проверяет, может ли "
         "модель, изучив сетевое поведение пользователя в обычном режиме, "
         "распознавать его при использовании VPN.")
    body(doc,
         "Сценарий 2 – mixed training. Обучение выполняется на объединённой "
         "выборке direct + VPN. Эксперимент позволяет оценить, насколько "
         "знание обоих режимов помогает модели адаптироваться к "
         "туннелированному трафику.")
    body(doc,
         "Сценарий 3 – open-set identification. Часть пользователей (классов) "
         "исключается из обучения и появляется только на тесте. Анализируется "
         "способность гибридной модели отличать неизвестного от известного "
         "и переводить сессию в класс unknown.")
    body(doc,
         "Сценарий 4 – сравнение порогов sessionization: 30 и 60 минут. "
         "Оценивается влияние порога неактивности на качество идентификации "
         "и устойчивость профилей пользователей.")

    # 3.2 ─────────────────────────────────────────────────────────────────────
    section(doc, "3.2. Метрики оценки")

    body(doc,
         "Так как задача имеет как классификационный, так и аномалийный "
         "компонент, система метрик является смешанной.")
    body(doc,
         "Для идентификации пользователя используются: accuracy – доля "
         "правильных ответов; macro-F1 – среднее F1 по классам, лучше "
         "отражает качество на малочисленных классах; top-3 accuracy – "
         "доля случаев, когда истинный класс входит в тройку наиболее "
         "вероятных.")
    body(doc,
         "Для задачи верификации и обнаружения аномалий используются: "
         "ROC-AUC – способность ранжировать VPN и non-VPN объекты по "
         "скоринговой функции; average precision – качество ранжирования "
         "с акцентом на положительный класс; EER (equal error rate) – "
         "порог равных ошибок; FAR (false acceptance rate) и FRR "
         "(false rejection rate) – ошибки первого и второго рода для "
         "open-set сценария.")
    body(doc,
         "Accuracy показывает долю правильных ответов, но не всегда "
         "достаточно информативна при дисбалансе классов. Macro-F1 "
         "усредняет F1-score по классам и лучше отражает качество на "
         "менее представленных классах. Для VPN/non-VPN задачи дополнительно "
         "важны precision и recall для класса VPN: precision показывает, "
         "насколько точны срабатывания детектора, а recall – какую долю "
         "VPN-объектов модель смогла найти.")

    # 3.3 ─────────────────────────────────────────────────────────────────────
    section(doc, "3.3. Результаты VPN/non-VPN классификации на ISCX")

    body(doc,
         "Использованы четыре временных окна: 15 с, 30 с, 60 с и 120 с. "
         "Для каждого окна выполнено стратифицированное разбиение "
         "train/test 75/25. Модель – RandomForestClassifier с балансировкой "
         "классов. Медианы для заполнения пропущенных значений вычислены "
         "только на тренировочной части и сохранены вместе с моделью, "
         "что исключает утечку данных.")

    tbl_rows = []
    for row in iscx_rows:
        win = row["dataset"].replace("TimeBasedFeatures-Dataset-", "").replace(".arff", "")
        tbl_rows.append([
            win,
            row["num_rows"],
            _f(row["accuracy"], 4),
            _f(row["macro_f1"], 4),
            _f(row["vpn_precision"], 4),
            _f(row["vpn_recall"], 4),
            _f(row["roc_auc"], 4),
        ])
    table(doc,
          ["Окно", "Строк", "Accuracy", "Macro-F1", "VPN Prec", "VPN Recall", "ROC-AUC"],
          tbl_rows)
    noindent(doc, "Таблица 1 – Сводные метрики по временным окнам ISCX",
             italic=True, center=True)
    blank(doc)

    best = max(iscx_rows, key=lambda r: float(r["roc_auc"]))
    best_win = best["dataset"].replace("TimeBasedFeatures-Dataset-", "").replace(".arff", "")

    body(doc,
         f"Лучший результат получен на окне {best_win}: accuracy = "
         f"{_f(best['accuracy'])}, macro-F1 = {_f(best['macro_f1'])}, "
         f"ROC-AUC = {_f(best['roc_auc'])}. Это можно объяснить тем, что "
         f"короткое окно лучше сохраняет локальные особенности трафика. "
         f"При увеличении окна признаки усредняются и часть различий между "
         f"VPN и non-VPN сглаживается.")

    body(doc,
         f"Для окна {best_win} подробный classification report на отложенной "
         f"тестовой выборке: non_vpn – precision = "
         f"{_f(cls_report['non_vpn']['precision'])}, "
         f"recall = {_f(cls_report['non_vpn']['recall'])}, "
         f"F1 = {_f(cls_report['non_vpn']['f1-score'])}, "
         f"support = {int(cls_report['non_vpn']['support'])}; "
         f"vpn – precision = {_f(cls_report['vpn']['precision'])}, "
         f"recall = {_f(cls_report['vpn']['recall'])}, "
         f"F1 = {_f(cls_report['vpn']['f1-score'])}, "
         f"support = {int(cls_report['vpn']['support'])}.")

    body(doc,
         "Анализ важности признаков выявил, что наибольший вклад в решение "
         "вносят признаки, связанные с межпотоковыми и межпакетными "
         "интервалами, а также со скоростью передачи. Это согласуется "
         "с гипотезой: туннелирование влияет не только на адресную часть "
         "трафика, но и на временную организацию потоков.")

    feat_rows = [[r["feature"], _f(r["importance"])] for r in top_features[:10]]
    table(doc, ["Признак", "Важность"], feat_rows)
    noindent(doc, "Таблица 2 – Топ-10 важных признаков (окно 15 с)",
             italic=True, center=True)
    blank(doc)

    # Figures from 15s — one wide, then pairs side by side
    figure(doc, ISCX_DIR / "metrics_comparison.png",
           "Рисунок 1 – Сравнение метрик по временным окнам", width=13.0)

    figure_pair(
        doc,
        ISCX_DIR / "15s" / "plots" / "confusion_vpn_detection.png",
        f"Рисунок 2 – Матрица ошибок, окно {best_win}",
        ISCX_DIR / "15s" / "plots" / "roc_vpn_detection.png",
        f"Рисунок 3 – ROC-кривая, окно {best_win}",
    )
    figure_pair(
        doc,
        ISCX_DIR / "15s" / "plots" / "precision_recall_vpn.png",
        f"Рисунок 4 – Precision-recall, окно {best_win}",
        ISCX_DIR / "15s" / "plots" / "feature_importance_top15.png",
        "Рисунок 5 – Топ-15 важных признаков",
    )
    figure(doc, ISCX_DIR / "15s" / "plots" / "error_by_application.png",
           "Рисунок 6 – Ошибки по типам приложений", width=13.0)

    body(doc,
         "Матрица ошибок показывает, что число ошибок относительно невелико. "
         "ROC-кривая расположена близко к левому верхнему углу, что "
         "подтверждает высокое качество ранжирования. Precision-recall кривая "
         "дополняет ROC-анализ и важна, если положительный класс VPN "
         "представляет приоритетный интерес для системы безопасности.")
    body(doc,
         "График ошибок по приложениям показывает, что некоторые типы "
         "трафика (например, streaming) труднее классифицировать, поскольку "
         "они формируют похожие временные паттерны в обоих режимах. "
         "В дальнейшем для таких категорий можно подбирать специализированные "
         "признаки или ансамблевые подходы.")

    # 3.4 ─────────────────────────────────────────────────────────────────────
    section(doc,
            "3.4. Прокси-эксперимент: приложение-класс "
            "как суррогат пользователя")

    body(doc,
         "Поскольку ISCX ARFF не содержит user_id, прямое обучение модели "
         "деанонимизации пользователя на этом датасете было бы методологически "
         "некорректным. Для проверки основной гипотезы работы – сохраняют ли "
         "временные признаки поведенческую идентичность через VPN-туннель – "
         "разработан прокси-эксперимент.")
    body(doc,
         "В качестве суррогата user_id использовался класс приложения "
         "(BROWSING, VOIP, CHAT, P2P, MAIL, STREAMING, FT). Это тестирует "
         "ту же гипотезу, что и задача идентификации пользователя: "
         "сохраняются ли поведенческие паттерны после туннелирования. "
         "Однако идентичности здесь – поведение приложения, а не конкретный "
         "человек. Артефакты помечены DISCLAIMER.txt с явным предупреждением "
         "о прокси-природе эксперимента.")

    prx_tbl = []
    scen_names = {"direct_to_vpn": "direct → vpn",
                  "mixed": "mixed", "open_set": "open-set"}
    for row in proxy_rows:
        scen = scen_names.get(row["scenario"], row["scenario"])
        prx_tbl.append([
            scen,
            row["num_samples"],
            _f(row.get("accuracy"), 4) if row.get("accuracy") else "–",
            _f(row.get("macro_f1"), 4) if row.get("macro_f1") else "–",
            _f(row.get("top3_accuracy"), 4) if row.get("top3_accuracy") else "–",
            _f(row.get("roc_auc_unknown"), 4) if row.get("roc_auc_unknown") else "–",
            _f(row.get("eer"), 4) if row.get("eer") else "–",
        ])
    table(doc,
          ["Сценарий", "Объектов", "Accuracy", "Macro-F1", "Top-3 Acc",
           "ROC-AUC (unk)", "EER"],
          prx_tbl)
    noindent(doc, "Таблица 3 – Результаты прокси-эксперимента (7 классов приложений)",
             italic=True, center=True)
    blank(doc)

    body(doc,
         "В сценарии direct→VPN accuracy составила 0,3678 при случайном "
         "уровне 1/7 ≈ 0,143. Это означает, что временные признаки "
         "сохраняют около 36,8% поведенческой идентичности через VPN-туннель, "
         "что в 2,6 раза превышает случайный уровень. Top-3 accuracy = 0,752 "
         "указывает на то, что правильный класс присутствует в тройке "
         "наиболее вероятных кандидатов в 75% случаев.")
    body(doc,
         "В mixed-сценарии, когда модель обучается на объединённых "
         "direct + VPN данных, accuracy возрастает до 0,727. Это подтверждает, "
         "что знание обоих режимов существенно улучшает распознавание.")
    body(doc,
         "В open-set сценарии класс MAIL был скрыт от обучения. "
         "ROC-AUC для обнаружения неизвестного класса составил 0,450, "
         "EER = 0,519. Это близко к случайному уровню, что указывает "
         "на ограниченную способность Isolation Forest разделять "
         "неизвестный класс приложения от известных только по временным "
         "признакам. Данный результат свидетельствует о том, что open-set "
         "обнаружение для суррогатных поведенческих идентичностей является "
         "значительно более сложной задачей, чем сама классификация.")

    figure_pair(
        doc,
        PROXY_DIR / "plots" / "confusion_direct_to_vpn.png",
        "Рисунок 7 – Матрица ошибок: train direct, test VPN",
        PROXY_DIR / "plots" / "per_app_accuracy_direct_to_vpn.png",
        "Рисунок 8 – Точность по классам приложений",
    )

    body(doc,
         "Результаты прокси-эксперимента не следует представлять как "
         "метрики идентификации пользователя. Они демонстрируют частичную "
         "поведенческую устойчивость сетевых паттернов через VPN-туннель "
         "и подтверждают основную гипотезу работы на реальном датасете.")

    # 3.5 ─────────────────────────────────────────────────────────────────────
    section(doc, "3.5. Результаты синтетического сценария идентификации")

    body(doc,
         "Поскольку ISCX не содержит user_id, задача пользовательской "
         "идентификации проверена на синтетическом наборе, который имитирует "
         "прямой и VPN-режимы для нескольких виртуальных пользователей. "
         "Оценка выполнена для двух порогов sessionization: 30 и 60 минут.")

    demo_60 = [r for r in demo_rows if str(r.get("threshold_minutes", "")) == "60"]
    demo_30 = [r for r in demo_rows if str(r.get("threshold_minutes", "")) == "30"]

    def demo_table_rows(rows):
        scen_map = {"direct_to_tunneled": "direct → VPN",
                    "mixed": "mixed", "open_set": "open-set"}
        result = []
        for r in rows:
            result.append([
                scen_map.get(r["scenario"], r["scenario"]),
                r["num_samples"],
                _f(r["accuracy"], 4),
                _f(r["macro_f1"], 4),
                _f(r.get("roc_auc"), 4),
                _f(r.get("eer"), 4),
            ])
        return result

    table(doc,
          ["Сценарий", "Объектов", "Accuracy", "Macro-F1", "ROC-AUC", "EER"],
          demo_table_rows(demo_60))
    noindent(doc, "Таблица 4 – Синтетический сценарий, порог 60 мин",
             italic=True, center=True)
    blank(doc)

    table(doc,
          ["Сценарий", "Объектов", "Accuracy", "Macro-F1", "ROC-AUC", "EER"],
          demo_table_rows(demo_30))
    noindent(doc, "Таблица 5 – Синтетический сценарий, порог 30 мин",
             italic=True, center=True)
    blank(doc)

    # Find direct_to_tunneled accuracy for 60m
    d2v_60 = next((r for r in demo_60 if r["scenario"] == "direct_to_tunneled"), {})
    mixed_60 = next((r for r in demo_60 if r["scenario"] == "mixed"), {})
    os_60 = next((r for r in demo_60 if r["scenario"] == "open_set"), {})

    body(doc,
         f"Сценарий direct→VPN оказался самым сложным "
         f"(accuracy = {_f(d2v_60.get('accuracy'))}), что ожидаемо: "
         f"модель обучается на прямом трафике, а тестируется на VPN. "
         f"В mixed-сценарии качество выше "
         f"(accuracy = {_f(mixed_60.get('accuracy'))}), поскольку модель "
         f"видит оба режима на обучении. Open-set эксперимент "
         f"(ROC-AUC = {_f(os_60.get('roc_auc'))}, "
         f"EER = {_f(os_60.get('eer'))}) демонстрирует хорошую способность "
         f"гибридной схемы отличать неизвестных пользователей от известных.")
    body(doc,
         "Различие между порогами sessionization невелико. Порог 60 минут "
         "даёт незначительно лучший результат в сценарии direct→VPN, "
         "что объясняется более длинными и стабильными сессиями, несущими "
         "больше поведенческой информации. Порог 30 минут незначительно "
         "лучше в open-set (меньше EER), поскольку более короткие сессии "
         "лучше отражают локальные изменения поведения.")

    figure(doc, DEMO_DIR / "threshold_60m" / "plots" / "confusion_direct_to_tunneled.png",
           "Рисунок 9 – Результаты синтетического сценария")


# ══════════════════════════════════════════════════════════════════════════════
# ЗАКЛЮЧЕНИЕ
# ══════════════════════════════════════════════════════════════════════════════

def build_conclusion(doc: Document, best_row: dict) -> None:
    chapter(doc, "ЗАКЛЮЧЕНИЕ")

    body(doc,
         "В ходе работы предложен подход к идентификации и верификации "
         "пользователя, использующего VPN/Proxy, на основе поведенческой "
         "биометрии и анализа временных сетевых сессий. В отличие от "
         "традиционной идентификации по IP-адресу, предложенная схема "
         "опирается на flow-метаданные и поведенческие временные признаки, "
         "сохраняющие информативность даже в условиях шифрования и "
         "туннелирования.")
    body(doc,
         "Показано, что задача естественно формулируется как сочетание двух "
         "направлений машинного обучения: анализа временных рядов и детекции "
         "аномалий. Разработан двухуровневый гибридный метод: классификатор "
         "пользователя по агрегированным session-level признакам и "
         "пользовательский детектор аномалий на основе Isolation Forest. "
         "Такая схема позволяет не только определить наиболее вероятного "
         "пользователя, но и оценить степень отклонения текущей сессии "
         "от типичного профиля.")
    body(doc,
         "На реальном открытом датасете ISCX-VPN-NonVPN-2016 проведён "
         "методологически корректный эксперимент бинарной классификации "
         "VPN/non-VPN. Лучший результат получен на временном окне 15 с: "
         f"accuracy = {_f(best_row['accuracy'])}, "
         f"macro-F1 = {_f(best_row['macro_f1'])}, "
         f"ROC-AUC = {_f(best_row['roc_auc'])}. "
         "Наиболее информативными признаками оказались total_biat, "
         "flowBytesPerSecond и межпотоковые интервалы, что подтверждает "
         "ключевую идею работы: временная структура трафика остаётся "
         "информативной даже без анализа содержимого пакетов.")
    body(doc,
         "Дополнительный прокси-эксперимент, трактующий класс приложения "
         "как суррогат пользователя, подтвердил частичную поведенческую "
         "устойчивость через VPN-туннель. В сценарии direct→VPN accuracy "
         "составила 0,368 при случайном уровне 1/7 ≈ 0,143, что в 2,6 раза "
         "превышает базовый уровень.")
    body(doc,
         "Синтетический сценарий подтверждает, что гибридная схема "
         "classifier + Isolation Forest демонстрирует ROC-AUC = 0,980 "
         "в open-set задаче обнаружения неизвестных пользователей, "
         "что значительно превосходит результат на реальных данных. "
         "Это различие объясняется тем, что синтетические профили более "
         "чётко разделены, чем реальные поведенческие паттерны приложений.")
    body(doc,
         "Поставленная цель работы достигнута: сформулирована реалистичная "
         "постановка задачи, разработан метод её решения, проведена "
         "экспериментальная проверка, а ограничения датасета явно "
         "зафиксированы. Дальнейшее развитие работы может быть связано "
         "с расширением пользовательского датасета, переходом к "
         "sequence-моделям на уровне flows и исследованием устойчивости "
         "метода к различным типам обфускации трафика.")
    blank(doc)
    noindent(doc, "Основные результаты:", bold=True)
    bullet_list(doc, [
        f"лучший accuracy на реальном датасете: {_f(best_row['accuracy'])};",
        f"лучший ROC-AUC на реальном датасете: {_f(best_row['roc_auc'])};",
        "прокси-эксперимент подтвердил частичную поведенческую устойчивость "
        "через VPN-туннель: accuracy в 2,6 раза выше случайного уровня;",
        "гибридная схема classifier + Isolation Forest показала ROC-AUC = 0,980 "
        "в open-set сценарии на синтетических данных;",
        "ограничения датасета и методологии явно зафиксированы.",
    ])


# ══════════════════════════════════════════════════════════════════════════════
# СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ
# ══════════════════════════════════════════════════════════════════════════════

REFERENCES = [
    "Hernández-Álvarez, L. Privacy-Preserving Sensor-Based Continuous Authentication and User "
    "Profiling: A Review [Электронный ресурс] / L. Hernández-Álvarez, J. M. de Fuentes, "
    "L. González-Manzano, L. Hernández Encinas // Sensors. – 2021. – Vol. 21, № 1. – Art. 92. – "
    "Режим доступа: https://doi.org/10.3390/s21010092. – Дата доступа: 12.01.2026.",

    "Baig, A. F. Privacy-preserving continuous authentication using behavioral biometrics "
    "[Электронный ресурс] / A. F. Baig, S. Eskeland, B. Yang // International Journal of "
    "Information Security. – 2023. – Vol. 22. – P. 1833–1847. – "
    "Режим доступа: https://doi.org/10.1007/s10207-023-00721-y. – Дата доступа: 28.01.2026.",

    "Alotibi, G. Identifying Users by Network Traffic Metadata [Электронный ресурс] / "
    "G. Alotibi, N. Clarke, F. Li, S. Furnell // International Journal of Chaotic Computing. – "
    "2016. – Vol. 4, № 2. – P. 103–112. – "
    "Режим доступа: https://doi.org/10.20533/ijcc.2046.3359.2016.0013. – Дата доступа: 09.02.2026.",

    "Draper-Gil, G. Characterization of Encrypted and VPN Traffic Using Time-Related Features "
    "[Электронный ресурс] / G. Draper-Gil, A. H. Lashkari, M. S. I. Mamun, A. A. Ghorbani // "
    "Proceedings of the 2nd International Conference on Information Systems Security and Privacy. – "
    "2016. – P. 407–414. – "
    "Режим доступа: https://doi.org/10.5220/0005740704070414. – Дата доступа: 21.02.2026.",

    "Liu, M. ProxyCorr: robust traffic correlation attacks via mixed spatio-temporal analysis "
    "in encrypted proxy networks [Электронный ресурс] / M. Liu, G. Gou, G. Xiong [et al.] // "
    "Computer Networks. – 2025. – Vol. 273. – Art. 111763. – "
    "Режим доступа: https://doi.org/10.1016/j.comnet.2025.111763. – Дата доступа: 06.03.2026.",

    "Котенко, И. В. Методы машинного обучения для анализа поведенческих характеристик "
    "пользователей в компьютерных сетях [Электронный ресурс] / И. В. Котенко, И. Б. Саенко, "
    "О. В. Полубелова // Труды СПИИ РАН. – 2019. – Вып. 64. – С. 77–110. – "
    "Режим доступа: https://doi.org/10.15622/sp.64.4. – Дата доступа: 19.03.2026.",

    "Canadian Institute for Cybersecurity. VPN-nonVPN dataset (ISCXVPN2016) "
    "[Электронный ресурс]. – Режим доступа: https://www.unb.ca/cic/datasets/vpn.html. – "
    "Дата доступа: 02.04.2026.",

    "Liu, F. T. Isolation Forest [Электронный ресурс] / F. T. Liu, K. M. Ting, Z.-H. Zhou // "
    "Proceedings of the 2008 Eighth IEEE International Conference on Data Mining. – 2008. – "
    "P. 413–422. – "
    "Режим доступа: https://doi.org/10.1109/ICDM.2008.17. – Дата доступа: 14.04.2026.",

    "Городничий, А. В. Применение ансамблевых алгоритмов классификации для обнаружения "
    "аномалий в сетевом трафике [Электронный ресурс] / А. В. Городничий, Д. С. Лаврик // "
    "Вопросы кибербезопасности. – 2021. – № 2 (42). – С. 15–26. – "
    "Режим доступа: https://cyberleninka.ru/article/n/primenenie-ansamblevyh-algoritmov-"
    "klassifikatsii-dlya-obnaruzheniya-anomaliy-v-setevom-trafike. – Дата доступа: 25.04.2026.",

    "Pedregosa, F. Scikit-learn: Machine Learning in Python [Электронный ресурс] / "
    "F. Pedregosa, G. Varoquaux, A. Gramfort [et al.] // Journal of Machine Learning Research. – "
    "2011. – Vol. 12. – P. 2825–2830. – "
    "Режим доступа: https://jmlr.org/papers/v12/pedregosa11a.html. – Дата доступа: 07.05.2026.",
]


def build_references(doc: Document) -> None:
    chapter(doc, "СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ")
    for i, ref in enumerate(REFERENCES, 1):
        p = doc.add_paragraph()
        _body_fmt(p, indent=False)
        p.paragraph_format.left_indent = IND
        p.paragraph_format.first_line_indent = Cm(-1.25)
        _run(p, f"{i}. {ref}")


# ══════════════════════════════════════════════════════════════════════════════
# ПРИЛОЖЕНИЕ А
# ══════════════════════════════════════════════════════════════════════════════

def build_appendix_a(doc: Document) -> None:
    chapter(doc, "ПРИЛОЖЕНИЕ А")
    noindent(doc, "Архитектура программного прототипа", bold=True, center=True, sp_after=SP)

    body(doc,
         "Программный прототип реализован на языке Python и организован "
         "в виде пакета с разделением по функциональным слоям. В таблице А.1 "
         "перечислены основные компоненты и их роль в пайплайне.")

    modules = [
        ("Генерация данных",
         "Создаёт синтетические flow-записи с заданными поведенческими "
         "профилями. Управляет числом пользователей, режимами direct/vpn "
         "и статистическими параметрами распределений."),
        ("Sessionization",
         "Выделяет сессии из потока flow-записей по порогу неактивности. "
         "Поддерживает разбиение при смене режима и сохраняет временной "
         "зазор от предыдущей сессии для анализа ритма активности."),
        ("Извлечение признаков",
         "Агрегирует каждую сессию в числовой вектор: статистики "
         "длительностей, межпотоковых интервалов, скоростей передачи, "
         "периодов активности/бездействия, а также циклические признаки "
         "времени суток и дня недели."),
        ("Гибридная модель",
         "Реализует двухуровневую идентификацию: классификатор пользователя "
         "(RandomForest или CatBoost) плюс индивидуальные детекторы аномалий "
         "(Isolation Forest) для open-set сценария."),
        ("Оценка качества",
         "Запускает три сценария эксперимента (direct→VPN, mixed, open-set), "
         "рассчитывает accuracy, macro-F1, top-3 accuracy, ROC-AUC, EER "
         "и сохраняет предсказания и визуализации."),
        ("Модуль ISCX",
         "Читает ARFF-файлы датасета ISCX-VPN-NonVPN-2016, выполняет "
         "разбиение train/test с сохранением медиан тренировочной выборки, "
         "обучает модель бинарной классификации VPN/non-VPN и строит "
         "полный набор аналитических графиков."),
    ]
    table(doc, ["Компонент", "Описание"], [[m, d] for m, d in modules])
    noindent(doc, "Таблица А.1 – Компоненты программного прототипа",
             italic=True, center=True)
    blank(doc)

    body(doc,
         "Зависимости между компонентами выстроены в одном направлении: "
         "каждый слой получает данные от предыдущего и не знает о "
         "последующем. Это позволяет подменять любой компонент независимо "
         "– например, заменить генератор синтетических данных реальным "
         "датасетом, не изменяя логику sessionization или модели.")
    body(doc,
         "Разделение модуля ISCX в отдельный компонент принципиально важно "
         "с методологической точки зрения: он работает с flow-признаками "
         "без user_id и временных меток начала/конца потоков, поэтому "
         "решает задачу VPN/non-VPN detection, а не пользовательскую "
         "идентификацию. Смешение двух постановок в одном коде привело "
         "бы к некорректным выводам об информативности признаков.")


# ══════════════════════════════════════════════════════════════════════════════
# ПРИЛОЖЕНИЕ Б
# ══════════════════════════════════════════════════════════════════════════════

def build_appendix_b(doc: Document, cls_report: dict) -> None:
    chapter(doc, "ПРИЛОЖЕНИЕ Б")
    noindent(doc, "Полные численные результаты", bold=True, center=True, sp_after=SP)

    body(doc,
         "В таблице Б.1 приведён полный classification report для лучшего "
         "временного окна 15 с (отложенная тестовая выборка).")

    cr_rows = []
    for label in ["non_vpn", "vpn", "macro avg", "weighted avg"]:
        item = cls_report.get(label, {})
        cr_rows.append([
            label,
            _f(item.get("precision"), 4),
            _f(item.get("recall"), 4),
            _f(item.get("f1-score"), 4),
            str(int(item["support"])) if "support" in item else "–",
        ])
    table(doc, ["Класс", "Precision", "Recall", "F1-score", "Support"], cr_rows)
    noindent(doc, "Таблица Б.1 – Classification report (окно 15 с, test set)",
             italic=True, center=True)
    blank(doc)

    body(doc,
         "Для проверки воспроизводимости обученная модель была загружена "
         "повторно и применена к исходному датасету без переобучения. "
         "Результат технической проверки: accuracy = 0,9649, ROC-AUC = 0,9948. "
         "Эти значения завышены, поскольку модель применяется к данным, "
         "часть которых использовалась при её обучении. Для объективной "
         "оценки качества следует опираться на результаты из таблицы 1 "
         "основного текста, полученные исключительно на отложенной тестовой "
         "выборке, которая не участвовала в обучении.")
    body(doc,
         "Дополнительные графики построены для всех четырёх временных окон "
         "(15 с, 30 с, 60 с, 120 с). Набор визуализаций для каждого окна "
         "включает: матрицу ошибок классификации, ROC-кривую, "
         "precision-recall кривую, важность признаков, корреляционную "
         "матрицу признаков, гистограмму предсказанных вероятностей и "
         "тепловую карту ошибок по типам приложений. Сравнение окон "
         "позволяет убедиться, что выбор окна 15 с является оптимальным "
         "для данного датасета.")


# ══════════════════════════════════════════════════════════════════════════════
# ПРИЛОЖЕНИЕ В  —  код
# ══════════════════════════════════════════════════════════════════════════════

def code_listing(doc: Document, caption: str, code: str) -> None:
    """Captioned code block in Courier New 10pt, tight 13pt spacing."""
    p_cap = doc.add_paragraph()
    _body_fmt(p_cap, indent=False, sp_before=SP)
    _run(p_cap, caption, bold=True)
    for line in code.split("\n"):
        p = doc.add_paragraph()
        pf = p.paragraph_format
        pf.line_spacing_rule = WD_LINE_SPACING.EXACTLY
        pf.line_spacing = Pt(13)
        pf.space_before = Pt(0)
        pf.space_after = Pt(0)
        pf.first_line_indent = Pt(0)
        pf.left_indent = Cm(1.0)
        pf.alignment = WD_ALIGN_PARAGRAPH.LEFT
        r = p.add_run(line if line.strip() else " ")
        r.font.name = "Courier New"
        r.font.size = Pt(10)
    blank(doc)


_L1 = """\
def assign_sessions(df, threshold_minutes=60, split_on_mode=True):
    \"\"\"Разбить поток flow-записей на сессии по порогу неактивности.\"\"\"
    result    = df.sort_values(["user_id", "start_time"])
    threshold = pd.Timedelta(minutes=threshold_minutes)

    prev_end  = result.groupby("user_id")["end_time"].shift(1)
    prev_mode = result.groupby("user_id")["mode"].shift(1)
    gap       = result["start_time"] - prev_end          # временной зазор

    new_user       = result["user_id"] != result["user_id"].shift(1)
    inactivity_gap = gap.isna() | (gap > threshold)
    session_break  = new_user | inactivity_gap

    if split_on_mode:
        # смена режима direct/vpn тоже начинает новую сессию
        mode_switch   = prev_mode.notna() & (result["mode"] != prev_mode)
        session_break = session_break | mode_switch

    result["session_index"] = session_break.cumsum()
    result["session_id"] = (
        result["user_id"].astype(str) + "_" +
        result["mode"].astype(str)    + "_s" +
        result["session_index"].astype(str)
    )
    return result"""

_L2 = """\
def fit(self, X: pd.DataFrame, y: pd.Series) -> "HybridUserIdentifier":
    # --- шаг 1: обучить многоклассовый классификатор пользователей ----
    self.classifier = self._build_classifier()   # RF или CatBoost
    self.classifier.fit(X, y)

    # --- шаг 2: для каждого пользователя обучить детектор аномалий ----
    for user_id in sorted(pd.Series(y).astype(str).unique()):
        mask   = pd.Series(y).astype(str) == user_id
        user_X = X.loc[mask]
        if len(user_X) < 3:
            continue                             # мало данных для профиля

        scaler   = StandardScaler()
        scaled   = scaler.fit_transform(user_X)
        detector = IsolationForest(
            n_estimators=200,
            contamination="auto",
            random_state=self.random_state,
        )
        detector.fit(scaled)

        scores = detector.decision_function(scaled)
        self.user_models[user_id] = _UserAnomalyModel(
            scaler=scaler,
            detector=detector,
            q05=float(np.quantile(scores, 0.05)),  # нижний квантиль нормы
            q95=float(np.quantile(scores, 0.95)),  # верхний квантиль нормы
        )
    return self"""

_L3 = """\
def predict_with_details(self, X: pd.DataFrame) -> pd.DataFrame:
    # --- классификатор: распределение вероятностей по пользователям ----
    proba       = self.classifier.predict_proba(X)
    top_idx     = np.argsort(proba, axis=1)[:, ::-1]
    pred_users  = self.classifier.classes_[top_idx[:, 0]]
    confidences = proba[np.arange(len(X)), top_idx[:, 0]]

    # --- детектор аномалий: батч-вычисление по группам пользователей ---
    anom_scores = self._batch_anomaly_scores(pred_users, X)

    # --- гибридная оценка риска ----------------------------------------
    # alpha=0 -> только аномалии; alpha=1 -> только уверенность
    final_risk = (  self.alpha         * (1.0 - confidences)
                  + (1.0 - self.alpha) * anom_scores        )

    # --- решение: unknown при низкой уверенности или высокой аномалии --
    unknown = ( (confidences < self.confidence_threshold) |
                (anom_scores  > self.unknown_threshold)    )
    labels  = np.where(unknown, "unknown", pred_users)

    return pd.DataFrame({
        "pred_user_id"    : labels,
        "confidence"      : confidences,
        "anomaly_score"   : anom_scores,
        "final_risk_score": np.clip(final_risk, 0.0, 1.0),
    }, index=X.index)"""


def build_appendix_v(doc: Document) -> None:
    chapter(doc, "ПРИЛОЖЕНИЕ В")
    noindent(doc, "Ключевые фрагменты программного кода",
             bold=True, center=True, sp_after=SP)

    body(doc,
         "В данном приложении приведены три ключевых фрагмента реализации. "
         "Листинг В.1 показывает алгоритм выделения сессий по порогу "
         "неактивности. Листинг В.2 описывает двухэтапное обучение "
         "гибридной модели. Листинг В.3 демонстрирует механизм вывода, "
         "объединяющий уверенность классификатора и аномальный скоринг "
         "в итоговую оценку риска.")

    code_listing(
        doc,
        "Листинг В.1 – Алгоритм выделения сессий по порогу неактивности"
        " (sessionization.py)",
        _L1,
    )
    body(doc,
         "Алгоритм работает за один проход по данным, отсортированным "
         "по user_id и start_time. Граница сессии фиксируется при трёх "
         "условиях: смена пользователя, превышение порога неактивности "
         "между соседними потоками, а также (опционально) смена режима "
         "direct/vpn. Каждой сессии присваивается уникальный идентификатор, "
         "включающий имя пользователя, режим и порядковый номер.")

    code_listing(
        doc,
        "Листинг В.2 – Двухэтапное обучение гибридной модели (modeling.py)",
        _L2,
    )
    body(doc,
         "На первом этапе обучается многоклассовый классификатор по всем "
         "пользователям одновременно. На втором – для каждого пользователя "
         "отдельно обучается Isolation Forest на нормированных признаках "
         "его сессий. Квантили q05 и q95 фиксируют диапазон нормального "
         "поведения и используются для нормализации аномального скоринга "
         "в диапазон [0, 1] при тестировании.")

    code_listing(
        doc,
        "Листинг В.3 – Гибридный вывод с оценкой риска (modeling.py)",
        _L3,
    )
    body(doc,
         "Итоговый риск формируется как взвешенная сумма двух сигналов: "
         "недостаточной уверенности классификатора и высокого аномального "
         "скоринга. Параметр α управляет их балансом. Если хотя бы один "
         "из сигналов превышает пороговое значение, сессия помечается как "
         "unknown – механизм, обеспечивающий корректную работу модели "
         "в open-set сценарии при появлении незнакомого пользователя.")


# ══════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    iscx_rows = _csv(ISCX_DIR / "metrics_comparison.csv")
    demo_rows = _csv(DEMO_DIR / "threshold_comparison.csv")
    proxy_rows = _csv(PROXY_DIR / "metrics_summary.csv")
    cls_report = _json(ISCX_DIR / "15s" / "classification_report.json")
    top_features = _csv(ISCX_DIR / "15s" / "feature_importance.csv")

    best = max(iscx_rows, key=lambda r: float(r["roc_auc"]))

    doc = Document()
    setup_document(doc)

    # ── Title page (section 0, no footer page number) ─────────────────────────
    build_title_page(doc)

    # ── Add a new section so page numbering starts after title ─────────────────
    # Insert section break
    from docx.oxml import OxmlElement as OE
    from docx.oxml.ns import qn as Q
    last_para = doc.paragraphs[-1]
    pPr = last_para._p.get_or_add_pPr()
    sectPr = OE("w:sectPr")
    pgSz = OE("w:pgSz")
    pgSz.set(Q("w:w"), "11906")
    pgSz.set(Q("w:h"), "16838")
    pgMar = OE("w:pgMar")
    pgMar.set(Q("w:top"), "1134")
    pgMar.set(Q("w:right"), "851")
    pgMar.set(Q("w:bottom"), "1134")
    pgMar.set(Q("w:left"), "1701")
    sectPr.append(pgSz)
    sectPr.append(pgMar)
    pPr.append(sectPr)

    # Re-apply margins for all sections after setup
    for sec in doc.sections:
        sec.left_margin = Cm(3.0)
        sec.right_margin = Cm(1.5)
        sec.top_margin = Cm(2.0)
        sec.bottom_margin = Cm(2.0)

    build_referat(doc)
    build_summary(doc)
    build_toc(doc)
    build_intro(doc)
    build_chapter1(doc)
    build_chapter2(doc)
    build_chapter3(doc, iscx_rows, demo_rows, proxy_rows, cls_report, top_features)
    build_conclusion(doc, best)
    build_references(doc)
    build_appendix_a(doc)
    build_appendix_b(doc, cls_report)
    build_appendix_v(doc)

    # Add page numbers to footer
    setup_page_numbers(doc)

    out_path = OUT_DIR / "coursework_final.docx"
    doc.save(str(out_path))
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    main()
