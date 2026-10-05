#!/usr/bin/env python3
"""Render HW1_report.md to a clean PDF with plain-text formulas (no LaTeX commands)."""
from __future__ import annotations

import base64
import re
from pathlib import Path

import markdown
from xhtml2pdf import pisa

ROOT = Path(__file__).resolve().parents[1]
MD = ROOT / "reports" / "HW1_report.md"
HTML = ROOT / "reports" / "HW1_report.html"
PDF = ROOT / "reports" / "HW1_report.pdf"


def strip_latex(text: str) -> str:
    """Convert LaTeX math to readable plain text for Helvetica PDF."""

    def frac(m: re.Match) -> str:
        return f"({m.group(1)})/({m.group(2)})"

    def inline(m: re.Match) -> str:
        t = m.group(1)
        t = re.sub(r"\\frac\{([^{}]+)\}\{([^{}]+)\}", frac, t)
        repl = [
            (r"\\mathrm\{([^{}]*)\}", r"\1"),
            (r"\\operatorname\{([^{}]*)\}", r"\1"),
            (r"\\left", ""),
            (r"\\right", ""),
            (r"\\bigl", ""),
            (r"\\bigr", ""),
            (r"\\,", " "),
            (r"\\;", " "),
            (r"\\quad", "  "),
            (r"\\qquad", "   "),
            (r"\\times", " x "),
            (r"\\cdot", "*"),
            (r"\\min", "min"),
            (r"\\max", "max"),
            (r"\\lfloor", "floor("),
            (r"\\rfloor", ")"),
            (r"\\hat\{([^{}]*)\}", r"\1-hat"),
            (r"\\hat", ""),
            (r"\\alpha", "alpha"),
            (r"\\beta", "beta"),
            (r"\\sigma", "sigma"),
            (r"\\approx", "~"),
            (r"_\{([^{}]+)\}", r"_\1"),
            (r"\^\{([^{}]+)\}", r"^\1"),
            (r"[{}]", ""),
        ]
        for pat, rep in repl:
            t = re.sub(pat, rep, t)
        t = t.replace("\\", "")
        return f"<code>{t}</code>"

    def display(m: re.Match) -> str:
        inner = m.group(1).strip()
        # reuse inline converter without wrapping each piece
        fake = f"\\({inner}\\)"
        converted = re.sub(r"\\\((.+?)\\\)", inline, fake, flags=re.S)
        # unwrap code to pre
        converted = converted.replace("<code>", "").replace("</code>", "")
        return f"<pre style='white-space:pre-wrap;font-size:9pt;background:#f4f4f4;padding:6pt;margin:8pt 0;'>{converted}</pre>"

    text = re.sub(r"\\\[(.+?)\\\]", display, text, flags=re.S)
    text = re.sub(r"\\\((.+?)\\\)", inline, text, flags=re.S)
    # leftover $$ blocks
    text = re.sub(r"\$\$(.+?)\$\$", display, text, flags=re.S)
    text = re.sub(r"(?<!\$)\$(.+?)(?<!\$)\$", inline, text)
    return text


def ascii_safe(text: str) -> str:
    repl = {
        "→": "->",
        "←": "<-",
        "≠": "!=",
        "≤": "<=",
        "≥": ">=",
        "≈": "~",
        "−": "-",
        "–": "-",
        "—": "-",
        "×": "x",
        "·": "*",
        "Δ": "Delta",
        "α": "alpha",
        "β": "beta",
        "σ": "sigma",
        "“": '"',
        "”": '"',
        "’": "'",
        "‘": "'",
        "…": "...",
    }
    for a, b in repl.items():
        text = text.replace(a, b)
    return text


def soft_wrap_fenced_blocks(text: str, width: int = 78) -> str:
    """Convert long fenced blocks (prompts) into wrapping HTML with explicit <br/> breaks."""
    import html as html_lib
    import textwrap

    parts = re.split(r"(```[^\n]*\n.*?```)", text, flags=re.S)
    out = []
    for part in parts:
        if not part.startswith("```"):
            out.append(part)
            continue
        lines = part.splitlines()
        body_lines = lines[1:]
        if body_lines and body_lines[-1].strip() == "```":
            body_lines = body_lines[:-1]
        body = "\n".join(body_lines)
        if len(body) > 500 or any(len(x) > 100 for x in body_lines):
            # Preserve blank lines as paragraph breaks; wrap each paragraph explicitly
            paras = re.split(r"\n\s*\n", body)
            html_paras = []
            for para in paras:
                flat = re.sub(r"[ \t]+", " ", para.replace("\n", " ")).strip()
                if not flat:
                    continue
                wrapped = textwrap.fill(
                    flat,
                    width=width,
                    break_long_words=True,
                    break_on_hyphens=False,
                )
                # Explicit <br/> so xhtml2pdf cannot clip long lines
                html_line = html_lib.escape(wrapped).replace("\n", "<br/>\n")
                html_paras.append(f"<p style='margin:0 0 8pt 0; line-height:1.35;'>{html_line}</p>")
            block = (
                '<div style="font-family:Courier,monospace;font-size:9pt;'
                "background:#f3f3f3;padding:8pt;margin:8pt 0;\">"
                + "".join(html_paras)
                + "</div>\n"
            )
            out.append(block)
        else:
            wrapped = []
            for raw in body_lines:
                if raw.strip() == "":
                    wrapped.append("")
                    continue
                wrapped.extend(
                    textwrap.wrap(
                        raw,
                        width=width,
                        replace_whitespace=False,
                        drop_whitespace=False,
                        break_long_words=True,
                        break_on_hyphens=False,
                    )
                    or [""]
                )
            out.append("```\n" + "\n".join(wrapped) + "\n```")
    return "".join(out)


def embed_images(text: str) -> str:
    out = []
    for line in text.splitlines():
        if line.startswith("![") and "](assets/" in line:
            alt = line.split("![", 1)[1].split("]", 1)[0]
            rel = line.split("](", 1)[1].rstrip(")")
            img = (ROOT / "reports" / rel).resolve()
            if img.exists():
                b64 = base64.b64encode(img.read_bytes()).decode("ascii")
                out.append(
                    f'<p style="text-align:center"><img alt="{alt}" '
                    f'src="data:image/png;base64,{b64}" width="480"/></p>'
                )
            else:
                out.append(f"<p><em>[Missing figure: {rel}]</em></p>")
        else:
            out.append(line)
    return "\n".join(out)


def main() -> int:
    md = MD.read_text(encoding="utf-8")
    md = ascii_safe(md)
    md = soft_wrap_fenced_blocks(md, width=88)
    md = strip_latex(md)
    md = embed_images(md)
    body = markdown.markdown(md, extensions=["tables", "fenced_code", "sane_lists"])
    # Force wrapping inside <pre> for xhtml2pdf
    body = body.replace("<pre>", '<pre style="white-space:pre-wrap; word-wrap:break-word; overflow-wrap:break-word;">')
    body = body.replace("<code>", '<code style="white-space:pre-wrap; word-wrap:break-word;">')
    css = """
    @page { size: letter; margin: 0.6in 0.55in; }
    body {
      font-family: Helvetica, Arial, sans-serif;
      font-size: 9.5pt;
      line-height: 1.38;
      color: #111;
    }
    h1 { font-size: 14pt; margin: 0 0 8pt 0; }
    h2 { font-size: 11.5pt; margin: 14pt 0 6pt 0; }
    h3 { font-size: 10pt; margin: 10pt 0 4pt 0; }
    p { margin: 0 0 6pt 0; }
    ul, ol { margin: 0 0 8pt 18pt; }
    li { margin-bottom: 2pt; }
    table {
      width: 100%;
      font-size: 7.5pt;
      margin: 6pt 0 10pt 0;
      border-collapse: collapse;
      table-layout: fixed;
      word-wrap: break-word;
    }
    th, td {
      border: 1px solid #777;
      padding: 3pt 3pt;
      vertical-align: top;
      text-align: left;
    }
    th { background: #ececec; font-weight: bold; }
    code, pre {
      font-family: Courier, monospace;
      font-size: 9pt;
    }
    pre {
      background: #f3f3f3;
      padding: 6pt;
      white-space: pre-wrap;
      word-wrap: break-word;
      overflow-wrap: break-word;
    }
    img { max-width: 100%; }
    hr { border: none; border-top: 1px solid #bbb; margin: 10pt 0; }
    strong { font-weight: bold; }
    """
    html = (
        "<!DOCTYPE html><html><head><meta charset='utf-8'/>"
        f"<title>B9339 HW1 - Young Kim</title><style>{css}</style></head>"
        f"<body>{body}</body></html>"
    )
    HTML.write_text(html, encoding="utf-8")
    with open(PDF, "wb") as f:
        status = pisa.CreatePDF(html, dest=f, encoding="utf-8")
    print(f"wrote {HTML} ({HTML.stat().st_size} bytes)")
    print(f"wrote {PDF} ({PDF.stat().st_size} bytes) err={status.err}")
    return 0 if not status.err else 1


if __name__ == "__main__":
    raise SystemExit(main())
