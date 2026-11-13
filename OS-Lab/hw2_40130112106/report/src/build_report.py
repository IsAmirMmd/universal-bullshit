"""Build report.html from the template, inlining the exercise source files
(comments stripped).

Usage:  python build_report.py          -> report.html
        python build_report.py --pdf    -> report.html + report.pdf (headless Chrome)
"""
import html
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPORT = HERE.parent
HW = REPORT.parent
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"


def strip_comments(src: str) -> str:
    """Remove /* ... */ comments; drop lines that held nothing else."""
    out = []
    for line in src.split("\n"):
        new = re.sub(r"/\*.*?\*/", "", line).rstrip()
        if new or not line.strip():
            out.append(new)
    text = "\n".join(out)
    return re.sub(r"\n{3,}", "\n\n", text).strip("\n")


def build():
    tpl = (HERE / "report.template.html").read_text(encoding="utf-8")

    def inline(m):
        src = (HW / m.group(1)).read_text(encoding="utf-8")
        return html.escape(strip_comments(src), quote=False)

    out = re.sub(r"\{\{([\w.]+\.c)\}\}", inline, tpl)
    (REPORT / "report.html").write_text(out, encoding="utf-8", newline="\n")
    print("wrote", REPORT / "report.html")


def pdf():
    out = REPORT / "report.pdf"
    subprocess.run([
        CHROME, "--headless=new", "--disable-gpu", "--allow-file-access-from-files",
        "--no-pdf-header-footer", "--virtual-time-budget=5000",
        f"--print-to-pdf={out}", (REPORT / "report.html").as_uri(),
    ], check=True, capture_output=True)
    print("wrote", out)


if __name__ == "__main__":
    build()
    if "--pdf" in sys.argv:
        pdf()
