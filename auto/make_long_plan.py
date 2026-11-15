"""Builds auto/plan_long.json: daily long (landscape) YouTube videos, 2.5–8.5 min each, Mishary Alafasy."""
import json, os, math
H = os.path.dirname(os.path.abspath(__file__))
TEMPO, MAXD, MIND = 1.06, 510.0, 150.0
QA = {(e['surah'], e['ayah']): e['segments'] for e in json.load(open(f'{H}/data/Alafasy_128kbps.json'))}
NAY = {}
for s, a in QA: NAY[s] = max(NAY.get(s, 0), a)
def dur(s, a):
    sg = QA[(s, a)]; return (sg[-1][3] - sg[0][2]) / 1000 / TEMPO + 0.2
ORDER = [67, 36, 55, 56, 18, 32, 76, 78, 73, 59, 75, 44, 48, 49, 50, 53, 54, 57, 62, 64, 65, 66, 71, 72, 74, 79, 80, 81, 83, 84, 85,
         89, 90, 91, 92, 68, 69, 70, 77, 61, 63, 60, 58, 47, 46, 45, 31, 51, 52, 19, 12, 1, 25, 23, 24, 14, 13, 30, 29, 28, 27, 26,
         35, 34, 33, 37, 38, 39, 40, 41, 42, 43, 20, 21, 22, 17, 16, 15, 10, 11, 3, 2, 4, 5, 6, 7, 8, 9, 87, 88, 86, 82, 98, 96, 100]
plan = []
for s in ORDER:
    n = NAY[s]; ds = [dur(s, a) for a in range(1, n + 1)]; tot = sum(ds)
    if tot < MIND: continue
    parts = math.ceil(tot / MAXD); tgt = tot / parts; acc = 0; start = 1; made = 0
    for a in range(1, n + 1):
        acc += ds[a - 1]
        if a == n or (acc >= tgt * (made + 1) - ds[a - 1] / 2 and made < parts - 1):
            plan.append({'s': s, 'a': start, 'b': a}); start = a + 1; made += 1
json.dump(plan, open(f'{H}/plan_long.json', 'w'), indent=0)
print(len(plan), 'long videos'); print(plan[:8])
print('max min', max(sum(dur(p['s'], a) for a in range(p['a'], p['b'] + 1)) for p in plan) / 60)
