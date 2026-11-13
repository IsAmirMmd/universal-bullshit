"""Render Windows-Terminal-style snapshots of the expected outputs as PNG.

Each snapshot is built as HTML (Windows Terminal chrome, WSL Ubuntu tab,
Campbell color scheme, Cascadia Mono) and screenshotted with headless Chrome,
then cropped to the window.

Usage:  python make_terminals.py
"""
import html
import pathlib
import subprocess
import tempfile

from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
REPORT = HERE.parent
IMG = REPORT / "img"
FONTS = REPORT / "fonts"
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

USER, HOST, CWD = "amir", "ASUS", "~/os-lab"
TITLE = f"{USER}@{HOST}: {CWD}"

# Campbell scheme (Windows Terminal default)
FG = "#CCCCCC"
BG = "#0C0C0C"
GREEN = "#16C60C"   # bright green: bold user@host in Ubuntu's PS1
BLUE = "#3B78FF"    # bright blue: bold path in Ubuntu's PS1
RED = "#E74856"     # bright red: grep --color match


def prompt(cmd=None):
    """An Ubuntu bash prompt line, optionally followed by a typed command."""
    s = (f'<span style="color:{GREEN}">{USER}@{HOST}</span>:'
         f'<span style="color:{BLUE}">{CWD}</span>$ ')
    if cmd is not None:
        s += html.escape(cmd)
    return s


def text(line):
    """Plain output line. {Z} marks a grep match that grep colors red."""
    out = html.escape(line)
    return out.replace("{Z}", f'<span style="color:{RED}">Z</span>')


CURSOR = '<span class="cursor"></span>'


SNAPSHOTS = {
    "zombie": [
        [  # top pane: the program, still inside sleep(10)
            prompt("gcc -Wall -g ex2_zombie_example.c -o zombie_example"),
            prompt("./zombie_example"),
            text("Parent: Sleeping 10 seconds..."),
            text("Child: I'm done."),
        ],
        [  # bottom pane (focused): second terminal
            prompt("ps aux | grep Z"),
            text("amir        4823  0.0  0.0      0     0 pts/0    {Z}+   21:10   0:00 [zombie_example] <defunct>"),
            text("amir        4830  0.0  0.0   6480  2280 pts/1    S+   21:10   0:00 grep --color=auto {Z}"),
            prompt("ps -o pid,ppid,stat,cmd -C zombie_example"),
            text("    PID    PPID STAT CMD"),
            text("   4822    4790 S+   ./zombie_example"),
            text("   4823    4822 Z+   [zombie_example] <defunct>"),
            prompt() + CURSOR,
        ],
    ],
    "zombie_fixed": [
        [
            prompt("gcc -Wall -g ex2_zombie_fixed.c -o zombie_fixed"),
            prompt("./zombie_fixed"),
            text("Child (PID=4901): I'm done."),
            text("Parent: Collected child 4901 (exit code 0)."),
            text("Parent: Sleeping 10 seconds..."),
        ],
        [
            prompt("ps aux | grep Z"),
            text("amir        4910  0.0  0.0   6480  2280 pts/1    S+   21:15   0:00 grep --color=auto {Z}"),
            prompt("ps -o pid,ppid,stat,cmd -C zombie_fixed"),
            text("    PID    PPID STAT CMD"),
            text("   4900    4790 S+   ./zombie_fixed"),
            prompt() + CURSOR,
        ],
    ],
    "two_children": [
        [
            prompt("gcc -Wall -g ex3_two_children.c -o two_children"),
            prompt("time ./two_children"),
            text("Parent (PID=5210): child1 PID=5211 (sleep 5), child2 PID=5212 (date)"),
            text("Fri Nov 13 21:30:12 +0330 2026"),
            text("Parent: child PID 5212 (date) finished, exit code 0"),
            text("Parent: child PID 5211 (sleep 5) finished, exit code 0"),
            text("Parent: both children are done."),
            "",
            text("real    0m5.006s"),
            text("user    0m0.002s"),
            text("sys     0m0.004s"),
            prompt() + CURSOR,
        ],
    ],
    "minishell": [
        [
            prompt("gcc -Wall -g ex4_minishell.c -o minishell"),
            prompt("./minishell"),
            text("mysh> pwd"),
            text("/home/amir/os-lab"),
            text("mysh> cd /tmp"),
            text("mysh> pwd"),
            text("/tmp"),
            text("mysh> sleep 10 &"),
            text("[bg] started PID 6120"),
            text("mysh> echo shell-is-ready"),
            text("shell-is-ready"),
            text("mysh> cd /not-exist"),
            text("cd: No such file or directory"),
            text("mysh> "),
            text("[done] background PID 6120"),
            text("mysh> exit"),
            prompt() + CURSOR,
        ],
    ],
}

UBUNTU_ICON = """<svg width="16" height="16" viewBox="0 0 16 16">
<circle cx="8" cy="8" r="8" fill="#E95420"/>
<circle cx="8" cy="8" r="3.6" fill="none" stroke="#fff" stroke-width="1.5"/>
<circle cx="3.4" cy="8" r="1.4" fill="#fff"/>
<circle cx="10.3" cy="4" r="1.4" fill="#fff"/>
<circle cx="10.3" cy="12" r="1.4" fill="#fff"/>
</svg>"""

CSS = f"""
@font-face {{ font-family: "Cascadia Mono"; src: url("{(FONTS / 'CascadiaMono-Regular.ttf').as_uri()}"); }}
html, body {{ margin: 0; background: transparent; }}
body {{ padding: 28px; display: inline-block; }}
.win {{ width: 900px; background: {BG}; border: 1px solid #3a3a3a; border-radius: 8px;
        overflow: hidden; box-shadow: 0 10px 28px rgba(0,0,0,.40), 0 2px 6px rgba(0,0,0,.25); }}
.titlebar {{ height: 40px; background: #202020; display: flex; align-items: flex-end;
             font-family: "Segoe UI Variable Text", "Segoe UI", sans-serif; }}
.icon {{ font-family: "Segoe Fluent Icons", "Segoe MDL2 Assets"; }}
.tab {{ height: 33px; margin-left: 8px; width: 236px; box-sizing: border-box;
        background: {BG}; border-radius: 8px 8px 0 0; display: flex; align-items: center;
        gap: 9px; padding: 0 8px 0 12px; color: #fff; font-size: 12px; }}
.tab .title {{ flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.tab .x {{ font-size: 9px; color: #d0d0d0; width: 20px; text-align: center; }}
.btn {{ height: 33px; width: 34px; display: flex; align-items: center; justify-content: center;
        color: #d0d0d0; font-size: 12px; }}
.spacer {{ flex: 1; }}
.ctrl {{ align-self: stretch; width: 46px; display: flex; align-items: center;
         justify-content: center; color: #fff; font-size: 10px; }}
.body {{ padding: 0; }}
.pane {{ padding: 6px 10px 10px; font: 15px/1.32 "Cascadia Mono", Consolas, monospace;
         color: {FG}; white-space: pre; min-height: 20px; border: 1px solid transparent; }}
.split .pane {{ border-color: #2a2a2a; }}
.split .pane.focused {{ border-color: #0078D4; }}
.cursor {{ display: inline-block; width: 2px; height: 1.15em; background: #FFFFFF;
           vertical-align: -0.2em; }}
"""


def build_html(panes):
    split = len(panes) > 1
    pane_html = []
    for i, lines in enumerate(panes):
        focused = " focused" if (split and i == len(panes) - 1) else ""
        pane_html.append(f'<div class="pane{focused}">' + "\n".join(lines) + "</div>")
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>{CSS}</style></head>
<body><div class="win">
  <div class="body{' split' if split else ''}">{''.join(pane_html)}</div>
</div></body></html>"""


def screenshot(page: pathlib.Path, out: pathlib.Path, scale=2):
    subprocess.run([
        CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
        "--allow-file-access-from-files", f"--force-device-scale-factor={scale}",
        "--default-background-color=00000000", "--window-size=1000,1100",
        f"--screenshot={out}", page.as_uri(),
    ], check=True, capture_output=True)
    img = Image.open(out)
    bbox = img.getchannel("A").point(lambda a: 255 if a > 8 else 0).getbbox()
    img.crop(bbox).save(out)
    return img.crop(bbox).size


def main():
    IMG.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        for name, panes in SNAPSHOTS.items():
            page = pathlib.Path(tmp) / f"{name}.html"
            page.write_text(build_html(panes), encoding="utf-8")
            out = IMG / f"term_{name}.png"
            print(out.name, screenshot(page, out))


if __name__ == "__main__":
    main()
