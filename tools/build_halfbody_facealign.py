# 반신(halfbody_v6) 얼굴정렬 정규화 빌더
# - 소스: new_characters/upper_body_200_redraw_v9_new_halfbody (원본 보존, 읽기만)
# - 결과: assets/generals/halfbody_v6/{id}.webp (얼굴 크기/위치 균일, 머리 보호)
# - 개별 보정: tools/halfbody_align_overrides.json
import cv2, numpy as np, re, os, json, sys
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC  = os.path.join(ROOT, 'assets/generals/new_characters/upper_body_200_redraw_v9_new_halfbody')
DST  = os.path.join(ROOT, 'assets/generals/halfbody_v6')
OVR  = os.path.join(ROOT, 'tools/halfbody_align_overrides.json')

CW, CH = 720, 960
TARGET_FACE_W = int(CW * 0.30)   # 얼굴 목표 폭(균일 크기 기준)
FACE_TOP      = int(CH * 0.24)   # 얼굴 상단 '고정' 위치 — 세로 정렬 통일(카드가 다 가슴팍까지 균일하게)
MARGIN_TOP    = int(CH * 0.025)  # (미사용 가능) 머리 최소 상단 여백

cas    = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
casalt = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_alt2.xml')
eyec   = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
eyec2  = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye_tree_eyeglasses.xml')

EXP_RATIO  = 0.169        # 얼굴폭/이미지폭 중앙값 — 과검출/실패 클램프 기준
TARGET_EYE = 94.0         # 목표 눈 간격(px) — 얼굴 '크기' 통일의 주 기준(조조 기준)
EYE_Y      = int(CH*0.335)  # 눈 중심 고정 세로 위치
FACE_FALLBACK_W = 250     # (위치 폴백용) 눈검출 실패 시 얼굴박스 목표폭
TARGET_FIG = int(CW*1.26) # 어깨(알파)폭 목표 — 모든 카드 크기 통일 기준(결정론적, 검출무관)

def detect_faces(pil):
    # 후보 얼굴박스 '전부' 반환(두 캐스케이드). 가장 큰 것=얼굴 보장 안 됨(투구/손 오검출) → 후보 중 눈으로 검증
    w0 = pil.width
    scale = min(1.0, 700.0 / w0)
    small = pil if scale == 1.0 else pil.resize((int(w0*scale), int(pil.height*scale)))
    arr = np.array(small.convert('RGB'))[:, :, ::-1].copy()
    gray = cv2.cvtColor(arr, cv2.COLOR_BGR2GRAY)
    out = []
    for c in (cas, casalt):
        for b in c.detectMultiScale(gray, 1.1, 4, minSize=(int(small.width*0.09), int(small.height*0.06))):
            out.append([float(v/scale) for v in b])
    return out

def detect_eye_pair(pil, face):
    # 얼굴 상단 영역에서 눈 검출 → 유효한 좌/우 눈쌍의 (중심x, 중심y, 간격) 반환
    fx, fy, fw, fh = [int(v) for v in face]
    roi = pil.convert('RGB').crop((fx, fy, fx+fw, fy+int(fh*0.70)))
    arr = np.array(roi)[:, :, ::-1].copy()
    gray = cv2.cvtColor(arr, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)   # 대비 평활화로 검출률↑
    cs = []
    for cc in (eyec, eyec2):
        for sf, mn in ((1.05, 3), (1.1, 4)):
            es = cc.detectMultiScale(gray, sf, mn, minSize=(int(fw*0.10), int(fw*0.10)))
            cs = [(fx+ex+ew/2.0, fy+ey+eh/2.0) for ex, ey, ew, eh in es]
            if len(cs) >= 2:
                break
        if len(cs) >= 2:
            break
    if len(cs) < 2:
        return None
    cs.sort(key=lambda p: p[0])
    lx, ly = cs[0]; rx, ry = cs[-1]
    inter = rx - lx
    if inter < 0.28*fw or abs(ly-ry) > 0.22*fw:   # 간격/수평 정렬 검증
        return None
    return ((lx+rx)/2.0, (ly+ry)/2.0, inter)

def resolve_place(im, bbox, override):
    # 반환: (scale, ax, ay, ty, mode)  — 앵커점(ax,ay)을 캔버스 (CW/2, ty)에 배치, scale 적용
    exp = EXP_RATIO * im.width
    bx0, by0, bx1, by1 = bbox
    bw = bx1 - bx0; bh = by1 - by0
    if override and override.get('face'):
        cands = [[float(v) for v in override['face']]]
    else:
        cands = detect_faces(im)
        # 인물 상단부(머리 영역)에 중심이 있는 박스만 — 손/몸통 오검출 제거
        up = [c for c in cands if (c[1] + c[3]/2.0) <= by0 + 0.55*bh]
        if up:
            cands = up
        # 기대 얼굴폭에 가까운 순(투구처럼 과대박스 후순위)
        cands.sort(key=lambda c: abs(c[2] - exp))
    # 1순위: 눈이 검출되는 후보 = 진짜 얼굴(가장 균일·신뢰)
    for c in cands:
        pair = detect_eye_pair(im, c)
        if pair:
            ecx, ecy, inter = pair
            return (TARGET_EYE/inter, ecx, ecy, EYE_Y, 'eye')
    # 2순위: 눈 실패 → 기대크기에 맞는 상단부 후보를 얼굴로(눈높이≈박스 42% 지점)
    sane = [c for c in cands if 0.45*exp <= c[2] <= 1.9*exp]
    if sane:
        fx, fy, fw, fh = sane[0]
        return (FACE_FALLBACK_W/fw, fx+fw/2.0, fy+fh*0.42, EYE_Y, 'face')
    # 3순위(완전 실패): 알파 상단 중앙=머리 추정, 눈높이≈알파top+18%
    cx = (bx0 + bx1)/2.0
    eye_y = by0 + 0.18*bh
    return (FACE_FALLBACK_W/exp, cx, eye_y, EYE_Y, 'clamp')

def roster_ids():
    txt = open(os.path.join(ROOT, 'assets/generals/roster_200.js'), encoding='utf-8').read()
    return [m[0] for m in re.findall(r"\['([a-z0-9_]+)'\s*,\s*'([^']+)'\]", txt)]

def half_versions():
    html = open(os.path.join(ROOT, 'general_v6_halfbody_rework_final.html'), encoding='utf-8').read()
    return dict(re.findall(r'^\s*([a-z0-9_]+):\s*"(v\d+)"', html, re.M))

def build():
    ov_all = json.load(open(OVR, encoding='utf-8')).get('overrides', {})
    vers = half_versions()
    requested = set(sys.argv[1:])
    ids = [i for i in roster_ids() if not requested or i in requested]
    misses = []
    done = 0
    for i in ids:
        ver = vers.get(i, 'v9')
        p = os.path.join(SRC, f'{i}_halfbody_game_cutout_{ver}.png')
        if not os.path.exists(p):
            misses.append((i, 'NO_SRC')); continue
        try:
            o = ov_all.get(i, {})
            im = Image.open(p).convert('RGBA')
            bbox = im.split()[3].getbbox()
            scale, ax, ay, ty, mode = resolve_place(im, bbox, o)
            if mode != 'eye':
                misses.append((i, mode.upper()))   # 위치(앵커)는 눈 검증, 크기는 아래에서 어깨폭 기준
            # 크기: '어깨(알파)폭' 기준으로 전부 통일 → 검출 노이즈로 인한 대두/소두 원천 차단(결정론적)
            #   위치(ax,ay)는 눈 검증 얼굴 그대로 사용 → 얼굴이 항상 EYE_Y에 옴
            bbox_w = bbox[2] - bbox[0]
            scale = TARGET_FIG / bbox_w
            s = scale * float(o.get('scale', 1.0))
            # 앵커점(ax,ay)을 캔버스 (CW/2, ty)에 고정 배치 → 얼굴 크기/위치 통일
            dx = CW/2 - ax*s + float(o.get('dx', 0))
            dy = ty - ay*s + float(o.get('dy', 0))
            nim = im.resize((max(1, int(im.width*s)), max(1, int(im.height*s))), Image.LANCZOS)
            canvas = Image.new('RGBA', (CW, CH), (0, 0, 0, 0))
            canvas.alpha_composite(nim, (int(round(dx)), int(round(dy))))
            canvas.save(os.path.join(DST, f'{i}.webp'), 'WEBP', quality=86, method=4)
            done += 1
        except Exception as e:
            misses.append((i, f'ERROR:{e}'))
    n_face  = sum(1 for m in misses if m[1] == 'FACE')
    n_clamp = sum(1 for m in misses if m[1] == 'CLAMP')
    n_nosrc = sum(1 for m in misses if m[1] == 'NO_SRC')
    n_err   = sum(1 for m in misses if str(m[1]).startswith('ERROR'))
    n_eye   = done - n_face - n_clamp
    print(f'완료 {done} / 눈정렬 {n_eye} / 얼굴박스폴백 {n_face} / 클램프 {n_clamp} / 소스없음 {n_nosrc} / 에러 {n_err}')
    print('  -- 눈검출 실패(보정 후보) --')
    for m in misses:
        if m[1] in ('FACE', 'CLAMP'):
            print('  ', m[0], m[1])

if __name__ == '__main__':
    build()
