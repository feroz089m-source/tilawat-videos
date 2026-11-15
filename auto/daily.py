"""Daily job: build the next planned short, publish it on the orphan 'media' branch,
advance state.json on main, and print the public media URL + upload metadata as JSON.
usage: python3 auto/daily.py [--long] [--dry]   (--long: landscape long YouTube video; --dry: build only, no git changes)"""
import json, os, sys, subprocess, shutil, datetime
H = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(H)
DRY = '--dry' in sys.argv
LONG = '--long' in sys.argv
WK = f'{H}/work_long' if LONG else f'{H}/work'
BR = 'media_long' if LONG else 'media'
env = dict(os.environ, LONG='1' if LONG else '0')
GIT = ['git', '-C', REPO, '-c', 'user.name=feroz089m-source', '-c', 'user.email=feroz089m-source@users.noreply.github.com']
def run(*a, **k): return subprocess.run(list(a), check=True, **k)

shutil.rmtree(WK, ignore_errors=True)
run(sys.executable, f'{H}/build.py', stdout=subprocess.DEVNULL, env=env)
meta = json.load(open(f'{WK}/meta.json'))
assert os.path.getsize(meta['file']) < 95e6, 'video too large for GitHub'
OWNER_REPO = 'feroz089m-source/tilawat-videos'
meta['media_url'] = f'https://raw.githubusercontent.com/{OWNER_REPO}/{BR}/{meta["name"]}'

if not DRY:
    # 1) video on a fresh orphan branch 'media' (keeps the repo small: only the latest video lives there)
    tmp = f'/tmp/{BR}_wt'; shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp); run('git', '-C', tmp, 'init', '-q', '-b', BR)
    shutil.copy(meta['file'], f'{tmp}/{meta["name"]}')
    url = subprocess.check_output(['git', '-C', REPO, 'remote', 'get-url', 'origin'], text=True).strip()
    g = ['git', '-C', tmp, '-c', 'user.name=feroz089m-source', '-c', 'user.email=feroz089m-source@users.noreply.github.com']
    run(*g, 'add', '.'); run(*g, 'commit', '-qm', f'media {meta["name"]}')
    run(*g, 'push', '-f', url, f'{BR}:{BR}')
    # 2) advance state on main
    sp = f'{H}/state_long.json' if LONG else f'{H}/state.json'
    st = json.load(open(sp)) if os.path.exists(sp) else {'next': 0, 'done': []}
    st['done'].append({'date': datetime.date.today().isoformat(), 'S': meta['S'], 'A': meta['A'], 'B': meta['B']})
    st['done'] = st['done'][-60:]; st['next'] += 1
    json.dump(st, open(sp, 'w'), indent=1)
    run(*GIT, 'add', sp); run(*GIT, 'commit', '-qm', f'daily: {meta["name"]}')
    run(*GIT, '-c', 'push.negotiate=true', 'push', 'origin', 'HEAD:main')
print('META_JSON=' + json.dumps(meta, ensure_ascii=False))
