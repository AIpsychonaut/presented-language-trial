"""Build Apart-template REPORT.pdf from REPORT.md (xelatex + Old Standard TT)."""

from __future__ import annotations

import re
import subprocess
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
FONT_DIR = HERE / "fonts"
MD = HERE / "REPORT.md"
TEX = HERE / "REPORT.tex"
PDF = HERE / "REPORT.pdf"
FIG = HERE / "figure1_taglaw.png"

FONT_URLS = {
    "OldStandardTT-Regular.otf": "https://github.com/google/fonts/raw/main/ofl/oldstandardtt/OldStandard-Regular.ttf",
    "OldStandardTT-Bold.otf": "https://github.com/google/fonts/raw/main/ofl/oldstandardtt/OldStandard-Bold.ttf",
    "OldStandardTT-Italic.otf": "https://github.com/google/fonts/raw/main/ofl/oldstandardtt/OldStandard-Italic.ttf",
}
MIKTEX_OTF = Path(r"C:\Users\Akanksha Gupta\AppData\Local\Programs\MiKTeX\fonts\opentype\public\oldstandard")

SPRINT_URL = "https://apartresearch.com/sprints/ai-incident-response-sprint-2026-09-11-to-2026-09-13"


def ensure_fonts() -> None:
    FONT_DIR.mkdir(exist_ok=True)
    mapping = {
        "OldStandardTT-Regular.otf": "OldStandard-Regular.otf",
        "OldStandardTT-Bold.otf": "OldStandard-Bold.otf",
        "OldStandardTT-Italic.otf": "OldStandard-Italic.otf",
    }
    for dest_name, src_name in mapping.items():
        dest = FONT_DIR / dest_name
        src = MIKTEX_OTF / src_name
        if dest.exists() and dest.stat().st_size > 50000:
            continue
        if src.exists():
            dest.write_bytes(src.read_bytes())
            print("copied", dest, dest.stat().st_size)
            continue
        url = FONT_URLS[dest_name]
        print("downloading", dest_name)
        urllib.request.urlretrieve(url, dest)


def escape_tex(s: str) -> str:
    repl = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(repl.get(ch, ch) for ch in s)


def tex_tt(inner: str) -> str:
    esc = escape_tex(inner)
    esc = esc.replace(">", r">\allowbreak{}").replace("/", r"/\allowbreak{}")
    return r"\texttt{" + esc + "}"


def href_url(url: str, label: str | None = None) -> str:
    shown = label if label is not None else url
    if shown == url:
        return r"\href{" + url + r"}{\nolinkurl{" + url + "}}"
    return r"\href{" + url + "}{" + inline(shown) + "}"


def inline(s: str) -> str:
    parts: list[str] = []
    i = 0
    n = len(s)
    while i < n:
        if s.startswith("\\(", i):
            j = s.find("\\)", i + 2)
            if j == -1:
                parts.append(escape_tex(s[i:]))
                break
            parts.append("$" + s[i + 2 : j] + "$")
            i = j + 2
            continue
        if s.startswith("`", i):
            j = s.find("`", i + 1)
            if j == -1:
                parts.append(escape_tex(s[i:]))
                break
            parts.append(tex_tt(s[i + 1 : j]))
            i = j + 1
            continue
        if s.startswith("[", i):
            m = re.match(r"\[([^\]]+)\]\(([^)]+)\)", s[i:])
            if m:
                parts.append(href_url(m.group(2), m.group(1)))
                i += m.end()
                continue
        if s.startswith("http://", i) or s.startswith("https://", i):
            m = re.match(r"https?://[^\s\]\)>,]+", s[i:])
            if m:
                url = m.group(0).rstrip(".,;:")
                parts.append(href_url(url))
                i += len(url)
                continue
        if s.startswith("**", i):
            j = s.find("**", i + 2)
            if j != -1:
                parts.append(r"\textbf{" + inline(s[i + 2 : j]) + "}")
                i = j + 2
                continue
        if s.startswith("*", i) and not s.startswith("**", i):
            j = s.find("*", i + 1)
            if j != -1:
                parts.append(r"\textit{" + inline(s[i + 1 : j]) + "}")
                i = j + 1
                continue
        parts.append(escape_tex(s[i]))
        i += 1
    return "".join(parts)


def is_table_sep(line: str) -> bool:
    t = line.strip().replace(" ", "")
    return bool(t) and set(t) <= {"|", "-", ":"}


def parse_table(lines: list[str], start: int) -> tuple[str, int]:
    rows = []
    i = start
    while i < len(lines) and lines[i].strip().startswith("|"):
        if is_table_sep(lines[i]):
            i += 1
            continue
        cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
        rows.append(cells)
        i += 1
    if not rows:
        return "", start + 1
    ncol = max(len(r) for r in rows)
    for r in rows:
        while len(r) < ncol:
            r.append("")
    if ncol == 7:
        colspec = r"lcccc>{\raggedright\arraybackslash}X>{\raggedright\arraybackslash}X"
        env = "tabularx"
        width = r"{\textwidth}"
        size = r"\footnotesize"
        sep = "2.4pt"
    elif ncol == 5:
        colspec = (
            r">{\raggedright\arraybackslash}p{0.26\textwidth}"
            r">{\raggedright\arraybackslash}p{0.18\textwidth}"
            r">{\centering\arraybackslash}p{0.15\textwidth}"
            r">{\centering\arraybackslash}p{0.15\textwidth}"
            r">{\centering\arraybackslash}p{0.14\textwidth}"
        )
        env = "longtable"
        width = ""
        size = r"\footnotesize\renewcommand{\arraystretch}{0.9}"
        sep = "3.5pt"
    elif ncol == 4:
        colspec = r"l>{\raggedright\arraybackslash}Xll"
        env = "tabularx"
        width = r"{\textwidth}"
        size = r"\small"
        sep = "4pt"
    else:
        colspec = "l" * ncol
        env = "tabular"
        width = ""
        size = r"\small"
        sep = "6pt"
    begin = rf"\begin{{{env}}}{width}{{{colspec}}}"
    end = rf"\end{{{env}}}"
    wrap = env != "longtable"
    out = []
    if wrap:
        out.append(r"\begin{center}")
    else:
        out.append(r"{\centering")
    out.extend(
        [
            size,
            rf"\setlength{{\tabcolsep}}{{{sep}}}",
            begin,
            r"\toprule",
        ]
    )
    for ri, row in enumerate(rows):
        out.append(" & ".join(inline(c) for c in row) + r" \\")
        if ri == 0:
            out.append(r"\midrule")
    out.append(r"\bottomrule")
    out.append(end)
    if wrap:
        out.append(r"\end{center}")
    else:
        out.append(r"}")
    return "\n".join(out) + "\n", i


def heading_tex(title: str) -> str:
    m = re.match(r"^(\d+)\s+(.*)$", title)
    if m:
        return r"\section{" + inline(m.group(1) + ". " + m.group(2)) + "}\n"
    if title == "Abstract":
        return ""
    if title.startswith("Appendix"):
        return r"\section{" + inline(title) + "}\n"
    return r"\section{" + inline(title) + "}\n"


PREAMBLE = r"""
\documentclass[11pt,letterpaper]{article}
\usepackage[letterpaper,margin=1in]{geometry}
\usepackage{fontspec}
\usepackage{microtype}
\usepackage{setspace}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{tabularx}
\usepackage{longtable}
\usepackage{array}
\usepackage{amsmath,amssymb}
\usepackage{xcolor}
\usepackage{enumitem}
\usepackage{needspace}
\usepackage{xurl}
\usepackage[colorlinks=true,linkcolor=blue,urlcolor=blue,citecolor=blue,breaklinks=true]{hyperref}
\urlstyle{same}
\setmainfont{Old Standard TT}[
  Path = fonts/,
  UprightFont = OldStandardTT-Regular.otf,
  BoldFont = OldStandardTT-Bold.otf,
  ItalicFont = OldStandardTT-Italic.otf,
  BoldItalicFont = OldStandardTT-Italic.otf
]
\setsansfont{Old Standard TT}[
  Path = fonts/,
  UprightFont = OldStandardTT-Regular.otf,
  BoldFont = OldStandardTT-Bold.otf,
  ItalicFont = OldStandardTT-Italic.otf
]
\IfFontExistsTF{Latin Modern Mono}{
  \setmonofont{Latin Modern Mono}[Scale=0.86]
}{
  \setmonofont{Old Standard TT}[
    Path = fonts/,
    UprightFont = OldStandardTT-Regular.otf,
    Scale = 0.90
  ]
}
\setstretch{1.08}
\setlength{\parindent}{0pt}
\setlength{\parskip}{0.48em}
\setlength{\emergencystretch}{3em}
\setlist[itemize]{leftmargin=1.4em,itemsep=0.2em,topsep=0.3em}
\pagestyle{plain}
\renewcommand{\section}[1]{%
  \par\needspace{3\baselineskip}%
  {\fontsize{14}{17}\selectfont\bfseries #1\par}%
  \vspace{0.28em}%
}
\begin{document}
\begin{center}
{\rule{\textwidth}{1.6pt}}\\[0.55em]
{\fontsize{20}{24}\selectfont\bfseries Presented Games and Wired Predicates\footnote{Research conducted at the \href{SPRINTURL}{AI Incident Response Sprint}, September 2026}}\\[0.45em]
{\rule{\textwidth}{0.7pt}}\\[1.1em]
{\fontsize{11}{14}\selectfont Akanksha Gupta}\\
{\fontsize{11}{14}\selectfont 3am Labs}\\
{\fontsize{11}{14}\selectfont \href{mailto:akanksha@3amlabs.ai}{akanksha@3amlabs.ai}}\\[1.0em]
{\fontsize{11}{14}\selectfont\bfseries With}\\
{\fontsize{11}{14}\selectfont Apart Research}\\[1.2em]
{\fontsize{14}{17}\selectfont\bfseries Abstract}
\end{center}
\vspace{0.15em}
\begin{center}
\begin{minipage}{0.92\textwidth}
\itshape
ABSTRACTBODY
\end{minipage}
\end{center}
\vspace{0.55em}
""".replace("SPRINTURL", SPRINT_URL)


def convert() -> str:
    raw = MD.read_text(encoding="utf-8")
    lines = raw.splitlines()
    # drop title + byline
    i = 0
    while i < len(lines) and not lines[i].startswith("## Abstract"):
        i += 1
    if i >= len(lines):
        raise SystemExit("Abstract heading missing")
    i += 1
    abstract_lines: list[str] = []
    while i < len(lines) and not lines[i].startswith("## "):
        if lines[i].strip():
            abstract_lines.append(lines[i].strip())
        i += 1
    abstract = inline(" ".join(abstract_lines))
    body: list[str] = []
    para: list[str] = []

    def flush_para() -> None:
        nonlocal para
        if para:
            body.append(inline(" ".join(para)) + "\n")
            para = []

    while i < len(lines):
        line = lines[i]
        if line.strip() == "---":
            flush_para()
            i += 1
            continue
        if line.startswith("## "):
            flush_para()
            title = line[3:].strip()
            if title == "Author Contributions":
                i += 1
                while i < len(lines) and not lines[i].startswith("## "):
                    i += 1
                continue
            body.append(heading_tex(title))
            i += 1
            continue
        if line.strip().startswith("![") and "](" in line:
            flush_para()
            body.append(
                r"\begin{center}\includegraphics[width=0.92\textwidth,keepaspectratio]{figure1_taglaw.png}\end{center}"
                + "\n"
            )
            i += 1
            continue
        if line.strip().startswith("|"):
            flush_para()
            tex, i = parse_table(lines, i)
            body.append(tex)
            continue
        if line.startswith("- "):
            flush_para()
            items = []
            while i < len(lines) and lines[i].startswith("- "):
                items.append(r"\item " + inline(lines[i][2:].strip()))
                i += 1
            body.append(r"\begin{itemize}" + "\n" + "\n".join(items) + "\n" + r"\end{itemize}" + "\n")
            continue
        if not line.strip():
            flush_para()
            i += 1
            continue
        para.append(line.strip())
        i += 1
    flush_para()
    tex = PREAMBLE.replace("ABSTRACTBODY", abstract) + "\n".join(body) + "\n\\end{document}\n"
    return tex


def compile_tex() -> None:
    TEX.write_text(convert(), encoding="utf-8")
    cmd = [
        "xelatex",
        "-interaction=nonstopmode",
        "-halt-on-error",
        TEX.name,
    ]
    for _ in range(2):
        r = subprocess.run(
            cmd,
            cwd=HERE,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if r.returncode != 0:
            print(r.stdout[-4000:] if r.stdout else "")
            print(r.stderr[-2000:] if r.stderr else "")
            raise SystemExit("xelatex failed")
    print("wrote", PDF)


def main() -> None:
    if "Author Contributions" in MD.read_text(encoding="utf-8"):
        raise SystemExit("Author Contributions still in REPORT.md")
    if not FIG.exists():
        subprocess.check_call([sys.executable, str(HERE / "make_figure1.py")])
    ensure_fonts()
    compile_tex()
    sub = HERE / "Presented_Games_and_Wired_Predicates.pdf"
    sub.write_bytes(PDF.read_bytes())
    print("copied", sub)


if __name__ == "__main__":
    main()
