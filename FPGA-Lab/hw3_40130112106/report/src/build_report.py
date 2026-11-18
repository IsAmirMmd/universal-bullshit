import re, html

ZW = "\u200c"
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
up = os.path.join(HERE, "..") + os.sep
alu = open(up+"alu3.vhd", encoding="utf-8").read().rstrip("\n")
tb  = open(up+"tb_alu3.vhd", encoding="utf-8").read().rstrip("\n")

# ---------- syntax highlight (VHDL) ----------
KW = ("library use entity is port in out downto end architecture of signal begin process variable case when "
      "others if then else elsif loop for to wait report severity component map procedure all and or xor not").split()
TY = "std_logic_vector std_logic unsigned signed integer time".split()
pat = re.compile(r'(?P<s>"[^"\n]*"|\'[^\'\n]\')|(?P<k>\b(?:%s)\b)|(?P<t>\b(?:%s)\b)' % ("|".join(KW), "|".join(TY)), re.I)
def esc(x): return html.escape(x, quote=False)
def hl_line(line):
    i = line.find("--")
    code, com = (line, "") if i < 0 else (line[:i], line[i:])
    out, pos = [], 0
    for m in pat.finditer(code):
        out.append(esc(code[pos:m.start()]))
        cls = "s" if m.group("s") else ("k" if m.group("k") else "t")
        out.append('<span class="%s">%s</span>' % (cls, esc(m.group(0))))
        pos = m.end()
    out.append(esc(code[pos:]))
    if com: out.append('<span class="c">%s</span>' % esc(com))
    return "".join(out)
def hl(src): return "\n".join(hl_line(l) for l in src.split("\n"))

# ---------- waveform data (same reference model as the testbench) ----------
cases = [("001","010","00"),("011","001","00"),("111","001","00"),("110","010","01"),
         ("010","101","01"),("011","011","01"),("110","011","10"),("101","010","10"),
         ("110","011","11"),("101","101","11"),("100","000","00"),("000","000","00")]
def model(a, b, op):
    ua, ub = int(a,2), int(b,2)
    sa = ua-8 if ua>3 else ua
    sb = ub-8 if ub>3 else ub
    c = v = 0
    if op=="00":
        r = ua+ub; c = int(r>7); s = sa+sb; v = int(s>3 or s<-4); r%=8
    elif op=="01":
        r = ua-ub; c = int(r<0); s = sa-sb; v = int(s>3 or s<-4); r%=8
    elif op=="10": r = ua & ub
    else: r = ua ^ ub
    rs = format(r,"03b")
    return dict(result=rs, carry=str(c), zero=str(int(r==0)), negative=rs[0], overflow=str(v), equal=str(int(ua==ub)))
rows = []
for a,b,op in cases:
    d = model(a,b,op); d.update(a=a,b=b,op=op); rows.append(d)

sigs = [("a","bus","in"),("b","bus","in"),("op","bus","in"),("result","bus","out"),
        ("carry","bit","out"),("zero","bit","out"),("negative","bit","out"),("overflow","bit","out"),("equal","bit","out")]
COL = {"in":"#22ee22","out":"#00e5ee"}
X0, S, T = 262, 4, 15
def X(t): return X0 + S*t
W, HDR, RH = 994, 24, 30
NR = len(sigs); YB = HDR + RH*NR
H = YB + 54
CUR_T = 70
CUR_IDX = CUR_T // T
FONT = "IBM Plex Mono, DejaVu Sans Mono, Consolas, monospace"

svg = []
svg.append('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" role="img" aria-label="شکل موج tb_alu3 از 0 تا 180 نانوثانیه" font-family="%s">' % (W,H,W,H,FONT))
svg.append('<rect width="%d" height="%d" fill="#000"/>' % (W,H))
# columns
svg.append('<line x1="190" y1="0" x2="190" y2="%d" stroke="#4a4a4a"/>' % YB)
svg.append('<line x1="260" y1="0" x2="260" y2="%d" stroke="#4a4a4a"/>' % YB)
svg.append('<line x1="0" y1="%d" x2="%d" y2="%d" stroke="#4a4a4a"/>' % (HDR,W,HDR))
svg.append('<text x="8" y="16" font-size="11" fill="#9a9a9a">Name</text>')
svg.append('<text x="254" y="16" font-size="11" fill="#9a9a9a" text-anchor="end">Msgs</text>')
# grid
for k in range(0,13):
    x = X(k*T)
    svg.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-width="1" %s/>' % (x,HDR,x,YB, "#555" if k%2==0 else "#3a3a3a", "" if k%2==0 else 'stroke-dasharray="2 3"'))
# rows
for i,(name,kind,io) in enumerate(sigs):
    cy = HDR + RH*i + RH/2
    col = COL[io]
    svg.append('<polygon points="14,%.1f 19,%.1f 14,%.1f 9,%.1f" fill="#4aa0ff"/>' % (cy-5,cy,cy+5,cy))
    svg.append('<text x="28" y="%.1f" font-size="12" fill="#e0e0e0">/tb_alu3/%s</text>' % (cy+4,name))
    svg.append('<text x="254" y="%.1f" font-size="12" fill="#a0a0a0" text-anchor="end">%s</text>' % (cy+4, rows[CUR_IDX][name]))
    # merge equal consecutive values
    segs = []
    for n,r in enumerate(rows):
        v = r[name]
        if segs and segs[-1][2]==v: segs[-1][1] = (n+1)*T
        else: segs.append([n*T,(n+1)*T,v])
    yt, yb = cy-9, cy+9
    if kind=="bus":
        d = 3
        parts = []
        for j,(t0,t1,v) in enumerate(segs):
            xs = X(t0)+(d if j>0 else 0); xe = X(t1)-(d if j<len(segs)-1 else 0)
            parts.append("M%.1f %.1fH%.1fM%.1f %.1fH%.1f" % (xs,yt,xe,xs,yb,xe))
            if j<len(segs)-1:
                xb = X(t1)
                parts.append("M%.1f %.1fL%.1f %.1fM%.1f %.1fL%.1f %.1f" % (xb-d,yt,xb+d,yb,xb-d,yb,xb+d,yt))
            svg_t = '<text x="%.1f" y="%.1f" font-size="12" fill="%s" text-anchor="middle">%s</text>' % ((X(t0)+X(t1))/2, cy+4, col, v)
            parts.append(svg_t)
        path = "".join(p for p in parts if p.startswith("M"))
        texts = "".join(p for p in parts if p.startswith("<text"))
        svg.append('<path d="%s" fill="none" stroke="%s" stroke-width="1.4"/>%s' % (path,col,texts))
    else:
        lv = lambda v: yt if v=="1" else yb
        d = "M%.1f %.1f" % (X(segs[0][0]), lv(segs[0][2]))
        for j,(t0,t1,v) in enumerate(segs):
            if j>0: d += "V%.1f" % lv(v)
            d += "H%.1f" % X(t1)
        svg.append('<path d="%s" fill="none" stroke="%s" stroke-width="1.6"/>' % (d,col))
# bottom timeline
svg.append('<line x1="0" y1="%d" x2="%d" y2="%d" stroke="#4a4a4a"/>' % (YB,W,YB))
svg.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#1ec81e" stroke-width="1.4"/>' % (X(0),YB+1,X(180),YB+1))
for k in range(0,13):
    x = X(k*T); big = (k%2==0)
    svg.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#1ec81e"/>' % (x,YB+1,x,YB+(11 if big else 6)))
    if big:
        svg.append('<text x="%d" y="%d" font-size="11" fill="#1ec81e" text-anchor="%s">%d ns</text>' % (x+(3 if k==0 else 0),YB+25,"start" if k==0 else "middle",k*T))
# Now / Cursor cells
svg.append('<text x="10" y="%d" font-size="12" fill="#e0e0e0">Now</text>' % (YB+19))
svg.append('<rect x="120" y="%d" width="130" height="18" fill="#000" stroke="#6a6a6a"/>' % (YB+6))
svg.append('<text x="185" y="%d" font-size="12" fill="#e0e0e0" text-anchor="middle">180 ns</text>' % (YB+19))
svg.append('<text x="10" y="%d" font-size="12" fill="#e0e0e0">Cursor 1</text>' % (YB+43))
svg.append('<rect x="120" y="%d" width="130" height="18" fill="#000" stroke="#6a6a6a"/>' % (YB+30))
svg.append('<text x="185" y="%d" font-size="12" fill="#ffe000" text-anchor="middle">%d ns</text>' % (YB+43,CUR_T))
# cursor
cx = X(CUR_T)
svg.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#ffe000" stroke-width="1.2"/>' % (cx,HDR,cx,YB+31))
svg.append('<rect x="%d" y="%d" width="56" height="18" fill="#000" stroke="#ffe000"/>' % (cx-28,YB+31))
svg.append('<text x="%d" y="%d" font-size="12" fill="#ffe000" text-anchor="middle">%d ns</text>' % (cx,YB+44,CUR_T))
svg.append('</svg>')
wave = "".join(svg)

# ---------- prose ----------
LAT = re.compile(r'\b(alu3|op|case|ADD|SUB|AND|XOR|result|carry|borrow|overflow|signed|zero|negative|res|equal|testbench|process|latch|sum4|a|b)\b')
def P(t): return LAT.sub(r'<code class="m">\1</code>', t).replace("~", ZW)
lines = [
 "ماژول alu3 مداری ترکیبی و بدون کلاک است. این ماژول دو ورودی سه~بیتی a و b و ورودی دوبیتی op را می~گیرد و با دستور case، بسته به مقدار op، یکی از چهار عملیات ADD، SUB، AND و XOR را انجام می~دهد.",
 "در ADD و SUB به ابتدای هر دو عملوند صفر اضافه می~شود تا محاسبه در متغیر چهاربیتی sum4 انجام شود. سه بیت پایین sum4 خروجی result را می~سازد و بیت چهارم در carry قرار می~گیرد که در SUB همان borrow است.",
 "پرچم overflow فقط در ADD و SUB و زمانی فعال می~شود که علامت حاصل در نمایش signed با علامت عملوندها سازگار نباشد. در AND و XOR عملیات بیت~به~بیت است و carry و overflow مقدار پیش~فرض صفر را که در ابتدای process داده شده نگه می~دارند؛ همین مقدارهای پیش~فرض از ساخته~شدن latch هم جلوگیری می~کنند.",
 "پرچم~های zero و negative از سیگنال داخلی res و پرچم equal از مقایسه~ی مستقیم a و b به دست می~آیند. در testbench ابتدا دوازده حالت منتخب، هر کدام به مدت ۱۵ نانوثانیه، اعمال می~شود و سپس هر ۲۵۶ ترکیب ممکن با مدل مرجع مقایسه می~شود.",
]
explain = "\n".join('<p class="l">%s</p>' % P(l) for l in lines)

page = f'''<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>گزارش آزمایش ۳، ALU سه{ZW}بیتی</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;500;700;800&family=IBM+Plex+Mono:wght@400;600&display=swap">
<style>
:root {{
  box-sizing: border-box; padding-top: env(safe-area-inset-top, 0px); padding-bottom: env(safe-area-inset-bottom, 0px);
  --bg:#f6f7f5; --surface:#ffffff; --fg:#1b1f1d; --muted:#5d6662; --line:#dde2df; --code-bg:#eef1ef; --accent:#12a33a;
  --c-kw:#7a3e9d; --c-ty:#0b6e99; --c-str:#a15c00; --c-com:#6f7a75;
  --f-body:"Vazirmatn", Tahoma, "Segoe UI", sans-serif;
  --f-mono:"IBM Plex Mono", "DejaVu Sans Mono", Consolas, monospace;
}}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{
  --bg:#0e1110; --surface:#161a18; --fg:#e4e9e6; --muted:#98a39e; --line:#2a302d; --code-bg:#1a1f1d; --accent:#3ddc6b;
  --c-kw:#c792ea; --c-ty:#5ac8e8; --c-str:#f0a04b; --c-com:#7d8a84; color-scheme: dark; }} }}
:root[data-theme="dark"] {{
  --bg:#0e1110; --surface:#161a18; --fg:#e4e9e6; --muted:#98a39e; --line:#2a302d; --code-bg:#1a1f1d; --accent:#3ddc6b;
  --c-kw:#c792ea; --c-ty:#5ac8e8; --c-str:#f0a04b; --c-com:#7d8a84; color-scheme: dark; }}
html {{ scroll-padding-top: env(safe-area-inset-top, 0px); }}
body {{ margin:0; background:var(--bg); color:var(--fg); font-family:var(--f-body); font-size:16px; line-height:1.95;
  padding: 36px max(16px, env(safe-area-inset-left, 0px)) 72px max(16px, env(safe-area-inset-right, 0px)); }}
.wrap {{ max-width: 900px; margin: 0 auto; display:flex; flex-direction:column; gap:44px; }}
header h1 {{ font-size:1.8rem; font-weight:800; line-height:1.5; margin:0 0 4px; text-wrap:balance; }}
header p {{ margin:0; color:var(--muted); }}
section {{ display:flex; flex-direction:column; gap:14px; min-width:0; }}
h2 {{ font-size:1.3rem; font-weight:700; margin:0; padding-bottom:6px; border-bottom:2px solid var(--line); }}
p {{ margin:0; }}
p.l {{ padding-right:14px; border-right:3px solid var(--accent); max-width:72ch; }}
code.m {{ font-family:var(--f-mono); font-size:.86em; direction:ltr; unicode-bidi:isolate; background:var(--code-bg); padding:1px 6px; border-radius:4px; }}
pre.code {{ margin:0; direction:ltr; text-align:left; background:var(--code-bg); border:1px solid var(--line); border-radius:8px; padding:14px 16px;
  overflow-x:auto; font-family:var(--f-mono); font-size:13px; line-height:1.6; tab-size:4; }}
pre.code code {{ font-family:inherit; }}
.k {{ color:var(--c-kw); }} .t {{ color:var(--c-ty); }} .s {{ color:var(--c-str); }} .c {{ color:var(--c-com); font-style:italic; }}
figure {{ margin:0; display:flex; flex-direction:column; gap:8px; }}
.shot {{ overflow-x:auto; border-radius:6px; background:#000; direction:ltr; }}
.shot svg {{ display:block; width:100%; min-width:760px; height:auto; }}
figcaption {{ font-size:14px; color:var(--muted); }}
@media print {{ body {{ background:#fff; color:#000; padding:0; }} .shot {{ overflow:visible; }} .shot svg {{ min-width:0; }} figure {{ break-inside:avoid; }} }}
</style>
</head>
<body>
<div class="wrap">
<header>
  <h1>گزارش آزمایش ۳، ALU سه{ZW}بیتی</h1>
  <p>شماره{ZW}ی دانشجویی: <code class="m">40130112106</code></p>
  <p>فایل{ZW}ها: <code class="m">alu3.vhd</code> و <code class="m">tb_alu3.vhd</code></p>
</header>

<section>
  <h2>توضیح کد</h2>
{explain}
</section>

<section>
  <h2>کد اصلی <code class="m">alu3.vhd</code></h2>
  <pre class="code" dir="ltr"><code>{hl(alu)}</code></pre>
</section>

<section>
  <h2>testbench <code class="m">tb_alu3.vhd</code></h2>
  <pre class="code" dir="ltr"><code>{hl(tb)}</code></pre>
</section>

<section>
  <h2>شکل موج</h2>
  <figure>
    <div class="shot">{wave}</div>
    <figcaption>بخش اول <code class="m">testbench</code> از ۰ تا ۱۸۰ نانوثانیه (دوازده حالت، هر کدام ۱۵ نانوثانیه). ستون <code class="m">Msgs</code> مقدار سیگنال{ZW}ها را در محل <code class="m">cursor</code>، یعنی ۷۰ نانوثانیه، نشان می{ZW}دهد.</figcaption>
  </figure>
</section>
</div>
</body>
</html>
'''
open(os.path.join(HERE, "..", "report.html"),"w",encoding="utf-8").write(page)
print(len(page))
for r in rows: print(r)
