"""Builds auto/plan.json: an ordered list of short (<55 s) Mishary Alafasy segments."""
import json, re, os
H = os.path.dirname(os.path.abspath(__file__))
TEMPO, GAP, MAXD = 1.06, 0.3, 50.0
QA = {(e['surah'], e['ayah']): e for e in json.load(open(f'{H}/data/Alafasy_128kbps.json'))}
def norm(s):
    s = s.replace('‏', '').strip(); s = re.sub(r'([ࣰࣱࣲ]) (ا)', r'\1\2', s)
    return re.sub(r'\s+', ' ', s.replace('ࣰ', 'ً').replace('ࣱ', 'ٌ').replace('ࣲ', 'ٍ'))
AR = {}
for line in open(f'{H}/data/ara-quranuthmanihaf.txt', encoding='utf-8'):
    q = line.rstrip('\n').split('|')
    if len(q) == 3: AR[(int(q[0]), int(q[1]))] = norm(q[2]).split(' ')
NAY = {}
for s, a in AR: NAY[s] = max(NAY.get(s, 0), a)
def ok(k):
    e = QA.get(k)
    if not e or len(e['segments']) != len(AR[k]) or e['stats']['deletions'] or e['stats']['transpositions']: return False
    sg = e['segments']
    if any(g[0] != i or g[1] != i + 1 for i, g in enumerate(sg)): return False
    if not e['stats']['insertions']: return True
    if any(sg[i + 1][2] - sg[i][3] > 1200 for i in range(len(sg) - 1)): return False
    return all(g[3] - g[2] < 3500 for g in sg)
def dur(k):
    sg = QA[k]['segments']; return (sg[-1][3] / 1000 + 0.35 - max(0, sg[0][2] / 1000 - 0.15)) / TEMPO + GAP
BISM = dur((1, 1))
# order: short surahs first, then well-loved passages, then longer surahs in chunks
ORDER = [(93,), (97,), (108,), (113,), (114,), (1,), (102,), (105,), (106,), (110,), (109,), (95,), (99,), (100,),
         (101,), (104,), (107,), (111,), (112,), (103,), (96,), (91,), (92,), (90,), (89,), (88,), (87,), (86,), (85,),
         (84,), (82,), (81,), (80,), (79,), (83,), (78,), (98,), (55,), (67,), (36,), (56,), (59, 18, 24), (25, 63, 77),
         (23, 1, 11), (31, 12, 19), (2, 284, 286), (3, 190, 200), (18, 1, 16), (76,), (75,), (77,), (74,), (73,), (72,),
         (71,), (70,), (69,), (68,), (50,), (54,), (53,), (52,), (51,), (32,), (19,), (12,)]
import math
plan = []
for r in ORDER:
    s = r[0]; a0, a1 = (r[1], r[2]) if len(r) == 3 else (1, NAY[s])
    runs, cur = [], []
    for a in range(a0, a1 + 1):
        if ok((s, a)) and dur((s, a)) < MAXD: cur.append(a)
        else:
            if cur: runs.append(cur)
            cur = []
    if cur: runs.append(cur)
    for run in runs:
        ds = [dur((s, a)) + (BISM if (a == 1 and s not in (1, 9)) else 0) for a in run]
        tot = sum(ds); n = 1 if tot <= 57 else math.ceil(tot / MAXD)
        tgt = tot / n; acc = 0; start = 0
        for i, d in enumerate(ds):
            acc += d
            last = i == len(ds) - 1
            if last or (acc + ds[i + 1] / 2 > tgt * (len([p for p in plan if p.get('_r') is run]) + 1) and acc - sum(ds[:start]) > 8):
                plan.append({'s': s, 'a': run[start], 'b': run[i], '_r': run}); start = i + 1
for p in plan: p.pop('_r')
def pd(p): return sum(dur((p['s'], a)) for a in range(p['a'], p['b'] + 1)) + (BISM if p['a'] == 1 and p['s'] not in (1, 9) else 0)
out = []
for p in plan:
    q = [p]
    while any(pd(x) > 55 and x['b'] > x['a'] for x in q):
        x = next(x for x in q if pd(x) > 55 and x['b'] > x['a']); i = q.index(x); m = (x['a'] + x['b']) // 2
        q[i:i + 1] = [{'s': x['s'], 'a': x['a'], 'b': m}, {'s': x['s'], 'a': m + 1, 'b': x['b']}]
    out += [x for x in q if pd(x) <= 55]
plan = out
# drop very short leftovers (< 2 ayahs of a long surah)
plan = [p for p in plan if p['b'] - p['a'] >= 1 or NAY[p['s']] <= 6]
json.dump(plan, open(f'{H}/plan.json', 'w'), indent=0)
print(len(plan), 'videos planned'); print(plan[:12])
