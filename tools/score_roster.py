# -*- coding: utf-8 -*-
import glob, json, os, sys, itertools, statistics
sys.path.insert(0, 'tools')
import numpy as np
from PIL import Image
from scipy import ndimage
from patch_general import core_size

ATT = ['slash', 'thrust', 'heavy']
WALKS = ['walk1', 'walk2', 'walk3', 'walk4']

def sil(p):
    a = np.array(Image.open(p).convert('RGBA').getchannel('A')) > 16
    l, n = ndimage.label(a)
    return l == int(np.argmax(ndimage.sum(a, l, range(1, n + 1)))) + 1

def legs_of(m):
    ys, _ = np.nonzero(m); top = ys.min(); h = ys.max() - top
    o = np.zeros((300, m.shape[1]), bool); s = m[top + int(h * .55):, :][:300]
    o[:s.shape[0]] = s; return o

def height_of(m):
    ys, _ = np.nonzero(m); return 880 - int(ys.min())

def span_of(m):
    ys, _ = np.nonzero(m)
    b = m[ys.max() - 40:ys.max() + 1, :]; bx = np.nonzero(b)[1]
    return int(bx.max() - bx.min()) if len(bx) else 0

def tipx(p, fwd):
    a = np.array(Image.open(p).convert('RGBA').getchannel('A')) > 24
    ys, xs = np.nonzero(a)
    l, n = ndimage.label(a)
    body = l == int(np.argmax(ndimage.sum(a, l, range(1, n + 1)))) + 1
    by, bx = ndimage.center_of_mass(body)
    d = (xs - bx) ** 2 + (ys - by) ** 2
    if fwd:
        s = xs > bx
        if s.any(): d, xs, ys = d[s], xs[s], ys[s]
    return int(xs[int(np.argmax(d))])

def xor(a, b): return np.logical_xor(a, b).sum() / np.logical_or(a, b).sum() * 100
def iou(a, b): return np.logical_and(a, b).sum() / np.logical_or(a, b).sum()

def grade(v, best, worst, higher=True):
    if higher:
        if v >= best: return 100.0
        return max(0.0, 60 + (v - worst) / (best - worst) * 40)
    if v <= best: return 100.0
    return max(0.0, 60 + (v - worst) / (best - worst) * 40)

roster = json.load(open('assets/arcade_duel/generals.json', encoding='utf-8'))
rows = []
for g in roster:
    d = f"assets/arcade_duel/{g['id']}_states"
    names = sorted(os.path.basename(f)[:-5] for f in glob.glob(f'{d}/*.webp'))
    M = {n: sil(f'{d}/{n}.webp') for n in names}
    Sm = {n: M[n][::4, ::4] for n in names}
    cs = {n: core_size(Image.open(f'{d}/{n}.webp').convert('RGBA')) for n in names}

    L = {w: legs_of(M[w]) for w in WALKS}
    SP = {w: span_of(M[w]) for w in WALKS}
    o = sorted(WALKS, key=lambda w: SP[w]); mids, cons = o[:2], o[2:]
    A = xor(L[cons[0]], L[cons[1]])
    B = xor(L[mids[0]], L[mids[1]])
    hs = [height_of(M[w]) for w in cons]
    C = abs(hs[0] - hs[1]) / max(hs) * 100
    D = statistics.mean(SP[w] for w in mids) / max(SP[w] for w in cons) * 100
    hi = height_of(M['idle'])
    hw = statistics.mean(height_of(M[w]) for w in WALKS)
    E = abs(hi - hw) / hw * 100

    # 걷기 컷은 다리를 벌려 erode 코어가 구조적으로 6% 작다(로스터 평균 0.94배).
    # 넣으면 걸음이 클수록 '몸통이 흔들린다'고 잘못 잡힌다(유비 0.84 → 19%).
    core = [v for k, v in cs.items()
            if not k.startswith('walk') and k not in ('ko_down', 'ko_fall')]
    F = (max(core) - min(core)) / statistics.median(core) * 100

    Gbad = []
    for a in ATT:
        t = [tipx(f'{d}/{a}_{s}.webp', s != 'windup') for s in ('windup', 'impact', 'recovery')]
        if not (t[1] > t[0]): Gbad.append(a)

    atk = [f'{a}_{s}' for a in ATT for s in ('windup', 'impact', 'recovery')]
    # stunned 는 설계상 웅크린 자세라 heavy_impact 같은 웅크린 타격과 실루엣이
    # 겹친다(11명이 이 조합으로 감점됐다). 이 항목의 목적은 '공격 슬롯에 피격
    # 그림이 들어갔는가' 이므로 stunned 는 비교 대상에서 뺀다.
    hurt = ['hurt_light', 'hurt_heavy', 'ko_fall']
    H = max(iou(Sm[x], Sm[y]) for x in atk for y in hurt)

    dup = [f'{a}={b}' for a, b in itertools.combinations(names, 2) if iou(Sm[a], Sm[b]) >= 0.95]
    # 무기를 쥔 손이 실루엣을 끊으면 두 덩어리로 잡힌다. 크기만 보면 정상 컷이
    # 무더기로 걸린다(악진 걷기 5컷 전부). 본체와의 실제 간격으로 판정한다.
    frag = []
    for n in names:
        if n in ('ko_fall', 'ko_down'): continue
        a = np.array(Image.open(f'{d}/{n}.webp').convert('RGBA').getchannel('A')) > 16
        l, k = ndimage.label(a); s = ndimage.sum(a, l, range(1, k + 1))
        main = int(np.argmax(s)) + 1; mm = np.nonzero(l == main)
        for i in range(1, k + 1):
            if i == main or s[i - 1] < 3000: continue
            py, px = np.nonzero(l == i)
            gap = min(((mm[0] - py[j]) ** 2 + (mm[1] - px[j]) ** 2).min()
                      for j in range(0, len(py), 13)) ** 0.5
            if gap >= 60: frag.append(n); break
    I = (height_of(M['stunned']) - hi) / hi * 100

    sc = {'접지교대': grade(A, 25, 14), '통과교대': grade(B, 20, 8),
          '접지키차': grade(C, 1, 4, False), '통과발폭': grade(D, 35, 70, False),
          'idle걷기': grade(E, 2, 6, False), '몸통일관': grade(F, 6, 14, False),
          '공격순서': 100.0 - 25 * len(Gbad), '피격구분': grade(H, .60, .72, False),
          '자세중복': 100.0 - 20 * len(dup), '조각정리': 100.0 - 20 * len(frag)}
    W = {'접지교대': 3, '통과교대': 1, '접지키차': 2, '통과발폭': 1, 'idle걷기': 2,
         '몸통일관': 2, '공격순서': 3, '피격구분': 2, '자세중복': 2, '조각정리': 2}
    total = sum(max(0, sc[k]) * W[k] for k in W) / sum(W.values())
    rows.append(dict(name=g['name'], gid=g['id'], sc=sc, A=A, B=B, C=C, D=D, E=E, F=F, G=Gbad,
                     H=H, dup=dup, frag=frag, I=I, total=total))

rows.sort(key=lambda r: -r['total'])
print(f"{'장수':<7}{'총점':>6} │{'접지':>6}{'통과':>6}{'키차':>6}{'발폭':>6}{'대기':>7}{'몸통':>6}{'피격':>6} │ 결함")
for r in rows:
    fl = []
    if r['G']: fl.append('공격순서:' + ','.join(r['G']))
    if r['dup']: fl.append('중복:' + ','.join(r['dup']))
    if r['frag']: fl.append('조각:' + ','.join(r['frag']))
    if r['I'] > 5: fl.append(f"경직+{r['I']:.0f}%")
    print(f"{r['name']:<7}{r['total']:6.1f} │{r['A']:5.0f}%{r['B']:5.0f}%{r['C']:5.1f}%{r['D']:5.0f}%{r['E']:+6.1f}%{r['F']:5.0f}%{r['H']:6.2f} │ {' / '.join(fl)}")
print()
print(f"평균 {statistics.mean(r['total'] for r in rows):.1f} · 90+ {sum(1 for r in rows if r['total']>=90)}명 · "
      f"80s {sum(1 for r in rows if 80<=r['total']<90)}명 · <80 {sum(1 for r in rows if r['total']<80)}명")
