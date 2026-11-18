---
name: fpga-lab-report
description: Build a Persian FPGA/VHDL lab report as a published HTML artifact from a design file and its testbench - short code explanation, full code with highlighting, and a drawn ModelSim-style waveform. Use when the user uploads a .vhd and tb_*.vhd and asks for a lab report (گزارش آزمایش).
---

# FPGA lab report (Persian, HTML artifact)

Note: this skill was written after the fact from how the lab 3 (alu3) report was built. It describes that workflow; it is not an official or earlier file.

## Inputs
- design file (`alu3.vhd`) and testbench (`tb_alu3.vhd`) in /mnt/user-data/uploads
- optional: an earlier explainer HTML the user liked, as a style reference

## Output
One self-contained .html, published with the Artifact tool (do not also call present_files). RTL page, LTR islands for code and waveform, light/dark tokens, viewport-fit=cover with safe-area padding, Vazirmatn + IBM Plex Mono from Google Fonts.

## Report structure (in this order)
1. Header: plain title ("گزارش آزمایش N، <name>") and the two file names. No slogan.
2. Code explanation: exactly as many lines as the user asked (lab 3 = 4 lines). Each line one or two sentences. English technical terms stay English and are wrapped in `<code class="m">` (isolated LTR).
3. Main design code, full, no edits.
4. Testbench code, full, no edits.
5. Waveform, always last. One short caption only (range, cursor position). No waveform walkthrough unless asked.

## Persian text rules
- Keep computing terms in English (signal, process, testbench, carry...). No Persian gloss in parentheses.
- Correct ZWNJ (می‌گیرد، سه‌بیتی، بیت‌به‌بیت). In the script, write `~` and replace it with U+200C.
- No em dash, no «در نهایت / شایان ذکر است», no closing summary, no «یک» as an article.
- Follow the humanized-writing skill; user does not want AI-detectable text.

## Code blocks
`<pre class="code" dir="ltr">`, tab-size 4, overflow-x auto. Highlight with one regex pass over the raw line (comments split off first, then strings/char literals, keywords, type names), escaping each piece. Classes: k keyword, t type, s string, c comment.

## Waveform (hand-drawn inline SVG, always ModelSim theme)
- Black background, fixed regardless of page theme.
- Columns: Name (blue diamond icon + full path `/tb_<entity>/<sig>`), Msgs (gray, values at the cursor), wave area.
- Inputs green, outputs cyan, enable-type signals (`en`) orange.
- Buses: binary values centered in the segment, X-shaped transitions (3px), consecutive equal values merged into one segment. Scalars: step lines, high/low at +-9px of the row center.
- Gray vertical grid at every step (solid every 2nd, dashed between).
- Yellow cursor line with a yellow time box; pick a time in the middle of an interesting interval.
- Bottom: green timeline with ticks and "N ns" labels, plus "Now" and "Cursor 1" cells on the left.
- Scale 4 px/ns, 12 rows of 15 ns = 0-180 ns for the hand-picked part of the testbench. Wrap the SVG in a scroll container with min-width ~760px for phones.
- Values are computed in Python with the same reference model the testbench uses, then checked against the case comments in the testbench before drawing.

## Steps
1. Read both .vhd files; read the explainer HTML only for style.
2. List the testbench's hand-picked cases (a, b, op, delay) and compute all outputs with a reference model.
3. Run scripts/build_report.py (edit `cases`, `sigs`, the 4 explanation lines, file names).
4. Publish; reply briefly with the link.
