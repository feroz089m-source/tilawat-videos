"""Daily Peaceful Tilawat short builder.
usage: python3 build.py [S A B]   (no args: next item from plan.json / state.json)
Writes work/<slug>.mp4 and work/meta.json. Does not touch git or upload anything."""
import json, re, os, sys, math, subprocess, asyncio, shutil
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
H = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, f'{H}/data')
from surahs import SURAH, juz
W, HH, FPS = 1080, 1920, 30
TEMPO, GAP, OUTRO = 1.06, 0.0, 0.5   # continuous recitation: next ayah starts right after the previous one
WORK = f'{H}/work'; os.makedirs(WORK, exist_ok=True)
AUD = os.environ.get('AUDIO_REPO', '/tmp/aa')

def run(*a): subprocess.run(a, check=True)
def norm(s):
    s = s.replace('‏', '').strip(); s = re.sub(r'([ࣰࣱࣲ]) (ا)', r'\1\2', s)
    return re.sub(r'\s+', ' ', s.replace('ࣰ', 'ً').replace('ࣱ', 'ٌ').replace('ࣲ', 'ٍ'))

# ---------- choose item ----------
plan = json.load(open(f'{H}/plan.json'))
st_path = f'{H}/state.json'
state = json.load(open(st_path)) if os.path.exists(st_path) else {'next': 0, 'done': []}
if len(sys.argv) == 4: S, A, B = map(int, sys.argv[1:])
else:
    it = plan[state['next'] % len(plan)]; S, A, B = it['s'], it['a'], it['b']
EN, ARN = SURAH[S]
print('building', S, A, B, EN)

AR, UR = {}, {}
for line in open(f'{H}/data/ara-quranuthmanihaf.txt', encoding='utf-8'):
    q = line.rstrip('\n').split('|')
    if len(q) == 3 and int(q[0]) in (1, S): AR[(int(q[0]), int(q[1]))] = norm(q[2]).split(' ')
for line in open(f'{H}/data/urd-fatehmuhammadja.txt', encoding='utf-8'):
    q = line.rstrip('\n').split('|')
    if len(q) == 3 and int(q[0]) == S: UR[(S, int(q[1]))] = q[2].replace('ﷺ', ' صلی اللہ علیہ وسلم ').replace('  ', ' ').strip()
QA = {(e['surah'], e['ayah']): e['segments'] for e in json.load(open(f'{H}/data/Alafasy_128kbps.json')) if e['surah'] in (1, S)}
BISMILLAH = A == 1 and S not in (1, 9)
AY = ([(1, 1)] if BISMILLAH else []) + [(S, a) for a in range(A, B + 1)]

# ---------- audio (Mishary Alafasy per-ayah, fawazahmed0/audio-ayah-arabic-1) ----------
if not os.path.isdir(f'{AUD}/.git'):
    run('git', 'clone', '--depth', '1', '--filter=blob:none', '--no-checkout', 'https://github.com/fawazahmed0/audio-ayah-arabic-1', AUD)
files = [f'{s:03d}{a:03d}.mp3' for s, a in AY]
run('git', '-C', AUD, 'checkout', 'HEAD', '--', *files)

run('ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-t', str(max(GAP, 0.05)), '-i', 'anullsrc=r=44100:cl=mono', f'{WORK}/gap.wav')
run('ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-t', str(OUTRO + 1.2), '-i', 'anullsrc=r=44100:cl=mono', f'{WORK}/sil.wav')
segs, alist, t = [], [], 0.0
for n, k in enumerate(AY):
    sg = QA[k]; K = len(AR[k]); assert len(sg) == K, (k, len(sg), K)
    fn = f'{AUD}/{files[n]}'
    d0 = float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', fn]))
    o0 = max(0, sg[0][2] / 1000 - 0.05); o1 = min(d0, sg[-1][3] / 1000 + 0.15)
    WT = [[(sg[j][2] / 1000 - o0) / TEMPO, ((sg[j + 1][2] / 1000 if j + 1 < K else sg[j][3] / 1000 + 0.1) - o0) / TEMPO, j] for j in range(K)]
    d = (o1 - o0) / TEMPO
    run('ffmpeg', '-v', 'error', '-y', '-ss', str(o0), '-t', str(o1 - o0), '-i', fn, '-af',
        f'atempo={TEMPO},afade=t=in:d=0.02,afade=t=out:st={max(0, d - 0.12)}:d=0.12', '-ar', '44100', '-ac', '1', f'{WORK}/r{n}.wav')
    alist.append(f"file '{WORK}/r{n}.wav'")
    if n < len(AY) - 1 and GAP > 0: alist.append(f"file '{WORK}/gap.wav'")
    segs.append({'k': list(k), 'n': 0 if k == (1, 1) and BISMILLAH else k[1], 's': t, 'e': t + d,
                 'words': [[t + x, t + y, j] for x, y, j in WT]})
    t += d + (GAP if n < len(AY) - 1 else 0)
alist.append(f"file '{WORK}/sil.wav'")
TOTAL = t + OUTRO
open(f'{WORK}/alist.txt', 'w').write('\n'.join(alist) + '\n')
run('ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', f'{WORK}/alist.txt', '-af',
    'aecho=0.8:0.85:60|120:0.18|0.10,loudnorm=I=-15:TP=-1.5', '-t', str(TOTAL), '-ar', '44100', '-ac', '2', f'{WORK}/raw.wav')
print('audio', round(TOTAL, 1), 's')

# ---------- text pages ----------
DIG = '٠١٢٣٤٥٦٧٨٩'
def ard(n): return ''.join(DIG[int(c)] for c in str(n))
F = f'{H}/fonts'
CSS = f"""@font-face{{font-family:AQ;src:url('file://{F}/AmiriQuran.ttf')}}@font-face{{font-family:AB;src:url('file://{F}/Amiri-Bold.ttf')}}@font-face{{font-family:NQ;src:url('file://{F}/nastaliq.ttf')}}
html,body{{margin:0;width:1080px;height:1920px;background:transparent;overflow:hidden}}
.wrap{{position:absolute;left:60px;right:60px;top:500px;height:900px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:36px}}
.ar{{direction:rtl;text-align:center;font-family:AQ;font-size:100px;line-height:1.85;color:#fff;text-shadow:0 0 10px rgba(255,230,180,.45),0 3px 10px rgba(0,0,0,.85)}}
.m{{color:#ffd77a}}
.ur{{direction:rtl;text-align:center;font-family:NQ;font-size:52px;line-height:1.9;color:#e8f1ff;text-shadow:0 2px 6px rgba(0,0,0,.9);background:rgba(5,10,30,.35);border-radius:30px;padding:0 30px 16px}}
.hd{{position:absolute;top:150px;left:0;right:0;text-align:center;font-family:AB;font-size:100px;color:#ffe08a;text-shadow:0 0 14px rgba(255,210,140,.5),0 4px 8px #000}}
.sub{{position:absolute;top:290px;left:0;right:0;text-align:center;font-family:NQ;font-size:42px;color:#dfe9ff;text-shadow:0 2px 6px #000;direction:rtl}}
.line{{position:absolute;top:380px;left:50%;transform:translateX(-50%);width:420px;height:2px;background:linear-gradient(90deg,transparent,#ffe08a,transparent)}}"""
FIT = """()=>{const a=document.querySelector('.ar'),u=document.querySelector('.ur');let fa=100,fu=52;
for(let i=0;i<60;i++){if(a.offsetHeight+u.offsetHeight+36<=900&&a.offsetHeight<=600)break;
 if(a.offsetHeight>600||fa/100>fu/52){fa-=4;a.style.fontSize=fa+'px'}else{fu-=2;u.style.fontSize=fu+'px'}}}"""
NAY = max(a for s, a in AR if s == S)
whole = A == 1 and B == NAY
subtxt = ('مکمل سورت' if whole else f'آیات {ard(A)} تا {ard(B)}') + f' • پارہ {ard(juz(S, A))} • شیخ مشاری العفاسی'
BISM_UR = 'شروع اللہ کے نام سے جو بڑا مہربان نہایت رحم والا ہے'
def page(sgm):
    k = tuple(sgm['k']); ws = [f'<span class="w">{w}</span>' for w in AR[k]]
    if sgm['n']: ws[-1] = f'<span style="white-space:nowrap">{ws[-1]} <span class="m">۝{ard(sgm["n"])}</span></span>'
    u = BISM_UR if sgm['n'] == 0 else UR[k]
    return f'<!DOCTYPE html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body><div class="wrap"><div class="ar">{" ".join(ws)}</div><div class="ur">{u}</div></div></body></html>'
head = f'<!DOCTYPE html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body><div class="hd">سورة {ARN}</div><div class="sub">{subtxt}</div><div class="line"></div></body></html>'
first = AR[(S, A)]
snip = ' '.join(first[:5]) + (' …' if len(first) > 5 else '')
rng = 'FULL' if whole else f'{A}-{B}'
thumb = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
@font-face{{font-family:AB;src:url('file://{F}/Amiri-Bold.ttf')}}@font-face{{font-family:AQ;src:url('file://{F}/AmiriQuran.ttf')}}@font-face{{font-family:NQ;src:url('file://{F}/nastaliq.ttf')}}
html,body{{margin:0;width:1080px;height:1920px;overflow:hidden;background:url('file://{WORK}/thumbbg.jpg')}}
.t1{{position:absolute;top:470px;left:0;right:0;text-align:center;font-family:AB;font-size:{230 if len(ARN) <= 7 else 170}px;line-height:1.3;color:#ffe3a0;direction:rtl;text-shadow:0 6px 0 #5a4010,0 0 30px rgba(255,210,120,.55)}}
.q{{position:absolute;top:840px;left:60px;right:60px;text-align:center;font-family:AQ;font-size:84px;color:#fff;direction:rtl;text-shadow:0 3px 8px #000}}
.b{{position:absolute;top:1130px;left:160px;right:160px;background:rgba(10,20,40,.7);border:3px solid #ffe3a0;border-radius:60px;text-align:center;font-family:NQ;font-size:56px;color:#fff;padding:4px 0 28px;direction:rtl}}
.en{{position:absolute;top:1320px;left:0;right:0;text-align:center;font:800 64px Arial;color:#ffe3a0;letter-spacing:4px;text-shadow:0 3px 6px #000}}
.r{{position:absolute;top:1420px;left:0;right:0;text-align:center;font:600 44px Arial;color:#dfe8ff;text-shadow:0 3px 6px #000}}
</style></head><body><div class="t1">{ARN}</div><div class="q">{snip}</div><div class="b">{subtxt.split(' • ')[0]} • اردو ترجمہ</div>
<div class="en">SURAH {EN.upper()} {'' if whole else rng}</div><div class="r">Sheikh Mishary Alafasy</div></body></html>"""

PHOTOS = sorted(os.listdir(f'{H}/photos'))
CATS = {}
for p in PHOTOS: CATS.setdefault(p.split('_')[0], []).append(p)
# background follows the meaning of each ayah (keywords in the Urdu translation) -> photo category
THEME = [(['garden', 'waterfall'], ['جنت', 'باغ', 'نہر', 'پھل', 'نعمت', 'درخت', 'کھیتی', 'سبز', 'چشم']),
         (['sea', 'waterfall'], ['سمندر', 'دریا', 'پانی', 'کشتی', 'بارش', 'مینہ']),
         (['sea'], ['صبح', 'سورج', 'روشنی', 'نور', 'چاشت', 'فجر']),
         (['desert', 'clouds'], ['آگ', 'دوزخ', 'جہنم', 'عذاب', 'قیامت', 'ہلاک', 'ریت', 'صحرا', 'اونٹ', 'سختی', 'مشکل']),
         (['night', 'stars'], ['رات', 'چاند', 'ستار', 'تاریک', 'اندھیر']),
         (['stars', 'clouds'], ['آسمان', 'کائنات', 'بادل', 'ہوا']),
         (['mountain'], ['پہاڑ', 'زمین', 'پتھر']),
         (['mosque', 'clouds', 'forest'], ['ہدایت', 'نماز', 'مسجد', 'عبادت', 'سجد', 'ذکر', 'دعا', 'رحمت', 'بخش'])]
DEFAULT = ['mountain', 'forest', 'clouds', 'stars', 'night', 'sea']
def ss(x): x = max(0, min(1, x)); return x * x * (3 - 2 * x)
def pick_photos():
    seed = S * 31 + A * 7
    used, PB, last = set(), [], None
    for i, sg in enumerate(segs):
        k = tuple(sg['k']); u = BISM_UR if sg['n'] == 0 else UR.get(k, '')
        best = max(THEME, key=lambda th: sum(u.count(w) for w in th[1]))
        cats = best[0] if sum(u.count(w) for w in best[1]) else None
        if cats is None and last is not None and i % 2 == 1: PB.append(last); continue   # keep scene for 2 ayahs
        cats = [c for c in (cats or [DEFAULT[(seed + i) % len(DEFAULT)]]) if c in CATS] or DEFAULT
        pool = [p for c in cats for p in CATS.get(c, [])]
        fresh = [p for p in pool if p not in used] or pool
        p = fresh[(seed + i * 3) % len(fresh)]
        if p == last and len(pool) > 1: p = [q for q in pool if q != last][0]
        used.add(p); PB.append(p); last = p
    return PB
PB0 = pick_photos()
_tb = Image.open(f'{H}/photos/{PB0[min(1, len(PB0) - 1)]}').convert('RGB').resize((W, HH))
Image.blend(_tb, Image.new('RGB', (W, HH)), 0.45).save(f'{WORK}/thumbbg.jpg', quality=90)
async def render():
    from playwright.async_api import async_playwright
    BX = []
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page(viewport={'width': W, 'height': HH})
        jobs = [('head', head, True), ('thumb', thumb, False)] + [(f't{i}', page(s), True) for i, s in enumerate(segs)]
        for name, html, transp in jobs:
            open(f'{WORK}/{name}.html', 'w').write(html); await pg.goto(f'file://{WORK}/{name}.html'); await pg.wait_for_timeout(400)
            if name.startswith('t') and name != 'thumb': await pg.evaluate(FIT)
            await pg.screenshot(path=f'{WORK}/{name}.png', omit_background=transp)
            if name.startswith('t') and name != 'thumb':
                BX.append(await pg.evaluate("()=>[...document.querySelectorAll('.w')].map(e=>{const r=e.getBoundingClientRect();return [r.left,r.top,r.width,r.height]})"))
        await b.close()
    return BX
BX = asyncio.run(render())
json.dump({'segs': segs, 'total': TOTAL, 'boxes': BX, 'S': S, 'A': A, 'B': B}, open(f'{WORK}/timings.json', 'w'))

# ---------- frames ----------
def make_frame_fn():
    TX = [Image.open(f'{WORK}/t{i}.png').convert('RGBA') for i in range(len(segs))]
    HEAD = Image.open(f'{WORK}/head.png').convert('RGBA')
    PB = pick_photos()
    IMG = {}
    for p in set(PB):
        im = Image.open(f'{H}/photos/{p}').convert('RGB')
        # darken + slight vignette so Arabic/Urdu text stays readable
        dark = Image.new('RGB', im.size, (0, 0, 0)); im = Image.blend(im, dark, 0.38)
        IMG[p] = im
    bstart, bidx, bend = [], [], []
    for i, s_ in enumerate(segs):
        if not bidx or PB[i] != bidx[-1]: bidx.append(PB[i]); bstart.append(0.0 if i == 0 else s_['s'] - 0.4)
    bstart.append(TOTAL + 2)
    GW, GH = 1188, 2112
    def view(i, t):
        # slow Ken-Burns zoom + pan inside the 10% headroom
        t0, t1 = bstart[i], bstart[i + 1] + 1.2; k = ss((t - t0) / max(1, t1 - t0))
        z = 1.0 + 0.09 * (k if i % 2 == 0 else 1 - k)
        cw, ch = GW * 0.92 / z, GH * 0.92 / z
        cx = GW / 2 + (GW - cw) / 2 * (0.6 * math.sin(i * 1.7) * (k - 0.5) * 2)
        cy = GH / 2 + (GH - ch) / 2 * (0.6 * math.cos(i * 1.3) * (k - 0.5) * 2)
        box = (cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2)
        return IMG[bidx[i]].resize((W, HH), Image.BILINEAR, box=box)
    def bgframe(t):
        q = max(i for i in range(len(bidx)) if bstart[i] <= t)
        cur = view(q, t)
        if q > 0 and t - bstart[q] < 1.0: cur = Image.blend(view(q - 1, t), cur, ss((t - bstart[q]) / 1.0))
        return cur
    D = f'{H}/subs/'
    SUB = {n: Image.open(D + n + '.png').convert('RGBA') for n in ('subA', 'subB', 'subC')}
    SPOS = {n: [int(x) for x in open(D + n + '_pos.txt').read().split(',')] for n in ('subA', 'subB', 'subC')}
    HAND = Image.open(D + 'hand.png').convert('RGBA'); HT = (45, 6); SY = 1660
    def lerp(a, b, k): return (a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k)
    def sub_overlay(img, t):
        if not (4.8 <= t <= 9.8): return
        n = 'subA' if t < 6.15 else ('subB' if t < 7.35 else 'subC'); c = SUB[n].copy(); bx, byy, lx, ly, cw, ch = SPOS[n]
        a = ss((t - 4.8) / 0.4) * (1 - ss((t - 9.3) / 0.5)); dy = int((1 - ss((t - 4.8) / 0.4)) * 40)
        if a < 1: c.putalpha(c.getchannel('A').point(lambda v: int(v * a)))
        img.paste(c, (540 - c.width // 2, SY + dy), c)
        if t >= 5.2:
            l0 = 540 - cw // 2; btn = (l0 + bx, SY + byy + 8); bell = (l0 + lx, SY + ly + 10); st0 = (900, 1950); en = (1000, 1980)
            p = lerp(st0, btn, ss((t - 5.2) / 0.8)) if t < 6 else btn if t < 6.6 else lerp(btn, bell, ss((t - 6.6) / 0.6)) if t < 7.2 else bell if t < 7.8 else lerp(bell, en, ss((t - 7.8) / 0.8))
            img.paste(HAND, (int(p[0] - HT[0]), int(p[1] - HT[1])), HAND)
    SUBT = [2.5] + ([TOTAL - 12] if TOTAL > 30 else [])
    def frame(t):
        img = bgframe(t).convert('RGBA')
        img.alpha_composite(HEAD)
        for k, s in enumerate(segs):
            st = s['s']; en = segs[k + 1]['s'] if k + 1 < len(segs) else TOTAL - 0.6
            if st - 0.1 <= t < en:
                a = ss((t - st + 0.1) / 0.35) * (1 - ss((t - (en - 0.3)) / 0.3)); tx = TX[k]
                if a < 1: tx = tx.copy(); tx.putalpha(tx.getchannel('A').point(lambda v: int(v * a)))
                for ws, we, wi in s['words']:
                    if ws <= t < we:
                        x0, y0, bw, bh = BX[k][wi]; ov = Image.new('RGBA', (W, HH), (0, 0, 0, 0))
                        ImageDraw.Draw(ov).rounded_rectangle([x0 - 8, y0 + bh * 0.15, x0 + bw + 8, y0 + bh * 0.9], radius=22, fill=(255, 215, 130, int(45 * a)))
                        img.alpha_composite(ov.filter(ImageFilter.GaussianBlur(4)))
                img.alpha_composite(tx)
        for T0 in SUBT:
            if T0 <= t <= T0 + 5.0: sub_overlay(img, t - T0 + 4.8)
        return img.convert('RGB')
    return frame

def render_part(args):
    f0, f1, out = args; frame = make_frame_fn()
    ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{HH}', '-r', str(FPS), '-i', '-',
                           '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-pix_fmt', 'yuv420p', out + '.tmp.mp4'], stdin=subprocess.PIPE)
    for f in range(f0, f1): ff.stdin.write(frame(f / FPS).tobytes())
    ff.stdin.close(); assert ff.wait() == 0; os.rename(out + '.tmp.mp4', out)

if __name__ == '__main__':
    if os.environ.get('PREVIEW'):
        fr = make_frame_fn()
        for t in map(float, os.environ['PREVIEW'].split(',')): fr(t).resize((360, 640)).save(f'{WORK}/prev_{t}.png')
        sys.exit()
    from multiprocessing import Pool
    NF = int(TOTAL * FPS); P = max(1, min(4, os.cpu_count() or 1)); step = math.ceil(NF / P)
    parts = [(i * step, min(NF, (i + 1) * step), f'{WORK}/c{i}.mp4') for i in range(P) if i * step < NF]
    with Pool(len(parts)) as pool: pool.map(render_part, parts)
    for name, d in (('th0', 0.5), ('th1', 1.0)):
        run('ffmpeg', '-v', 'error', '-y', '-framerate', '30', '-i', f'{WORK}/thumb.png', '-vf', f'format=yuv420p,loop=-1:1,trim=duration={d}',
            '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-pix_fmt', 'yuv420p', '-r', '30', f'{WORK}/{name}.mp4')
    open(f'{WORK}/cl.txt', 'w').write("file 'th0.mp4'\n" + ''.join(f"file 'c{i}.mp4'\n" for i in range(len(parts))) + "file 'th1.mp4'\n")
    run('ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', f'{WORK}/cl.txt', '-c', 'copy', f'{WORK}/vid.mp4')
    D = float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', f'{WORK}/vid.mp4']))
    run('ffmpeg', '-v', 'error', '-y', '-i', f'{WORK}/raw.wav', '-af', f'adelay=500|500,apad,atrim=0:{D}', '-ar', '44100', f'{WORK}/final.wav')
    slug = f'surah_{EN.lower().replace("-", "_")}_{rng.lower().replace("-", "_")}_mishary'
    out = f'{WORK}/{slug}.mp4'
    run('ffmpeg', '-v', 'error', '-y', '-i', f'{WORK}/vid.mp4', '-i', f'{WORK}/final.wav', '-map', '0:v', '-map', '1:a', '-c:v', 'copy',
        '-c:a', 'aac', '-b:a', '160k', '-shortest', '-movflags', '+faststart', out)
    rng_t = 'Full' if whole else f'{A}-{B}'
    title = f'Surah {EN} {rng_t} | سورہ {ARN} | Mishary Alafasy 🤍 Urdu Translation #shorts #quran'
    if len(title) > 100: title = f'Surah {EN} {rng_t} | سورہ {ARN} | Mishary Alafasy 🤍 #shorts #quran'
    tag = EN.lower().replace('-', '').replace(' ', '')
    meta = {'file': out, 'name': os.path.basename(out), 'duration': round(D, 1), 'S': S, 'A': A, 'B': B,
            'youtube_title': title,
            'youtube_text': f'Surah {EN} ({rng_t}) with Urdu translation | Sheikh Mishary Rashid Alafasy 🤍\n\n{" ".join(first)}\n\nSubscribe to Peaceful Tilawat for daily Quran recitation.\n#shorts #quran #surah{tag} #tilawat #mishary #urdutranslation',
            'youtube_tags': ['quran', f'surah {EN.lower()}', 'tilawat', 'mishary alafasy', 'urdu translation', 'quran shorts'],
            'tiktok_title': f'سورہ {ARN} {"" if whole else "آیت " + rng_t} | Surah {EN} 🤍'.replace('  ', ' '),
            'tiktok_text': f'سورہ {ARN} {"مکمل" if whole else "آیت " + rng_t} | Surah {EN} | Mishary Alafasy 🤍 اردو ترجمہ کے ساتھ\n#quran #surah{tag} #tilawat #islam #fyp',
            'pin_comment': f'{" ".join(first)} 🤍 کون کون سن رہا ہے؟ کمنٹ میں "سبحان اللہ" لکھیں اور Peaceful Tilawat کو سبسکرائب کریں'}
    json.dump(meta, open(f'{WORK}/meta.json', 'w'), ensure_ascii=False, indent=1)
    print(json.dumps(meta, ensure_ascii=False, indent=1))
