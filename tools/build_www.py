# assets -> app/www/assets 를 만들면서 앱 번들 크기를 줄인다.
#
# 원본(assets/)은 절대 건드리지 않는다. 발주·검수는 계속 원본으로 한다.
# 여기서 줄인 결과만 APK/AAB 에 들어간다.
#
#   1) 안 쓰는 폴더·파일 제외        (참조 0건 확인분 + *_source.*)
#   2) 일기토 컷 1280x1024 -> 640x512
#        화면에선 403px 로 그려진다(spriteScale = 200/635 = 0.315).
#        1280 은 3.2배 과했다. 640 이면 1.6배로 여유는 남고 용량은 1/3 이다.
#        duel_v2 의 drawImage 목적지가 STATE_CW 같은 상수로만 계산되므로
#        그림만 줄이면 코드도 poses.json 좌표도 그대로 맞는다.
#   3) PNG/JPG -> WEBP 변환 + index.html 안의 경로 확장자 치환
#
# 사용: python tools/build_www.py
import os, re, io, shutil, sys
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

SRC = 'assets'
DST = 'app/www/assets'
WEBP_Q = 86

# 참조 0건으로 확인된 것들. 화이트리스트가 아니라 제외 목록이라, 빠뜨려도 게임이 안 깨진다.
EX_DIRS = {
    'generals/new_characters',
    'generals/face_icons/war_v6_halfbody_style_transparent_backup_20260603',
    'generals/face_icons/war_v1',
    'generals/face_icons/war_v2_anime',
    'generals/face_icons/war_v3_portrait',
    'generals/face_icons/war_v4_fullbody_style',
    'generals/face_icons/war_v5_halfbody_crop_style',
    'generals/face_icons/war_v6_halfbody_style',
    'generals/busts/_orig',
    'generals/busts_original_20260508',
    'generals/faces_original_20260509',
    'generals/busts_real_samples',
    'generals/mobile_fullbody_backup_20260516_093605',
    'duel_rework',
    'arcade_duel_640',            # 비교용 사본 — 빌드엔 안 넣는다
}

DUEL_SCALE = 0.5                  # 일기토 컷 축소율
CONVERT_EXT = {'.png', '.jpg', '.jpeg'}


def norm(p):
    return p.replace(os.sep, '/')


def excluded(rel):
    rel = norm(rel)
    return any(rel == e or rel.startswith(e + '/') for e in EX_DIRS)


def duel_root_refs():
    """arcade_duel 루트에서 duel_v2 가 실제로 부르는 파일만."""
    try:
        s = io.open('duel_v2.html', encoding='utf-8', errors='replace').read()
    except OSError:
        return None
    return set(os.path.basename(p.split('?')[0])
               for p in re.findall(r'assets/arcade_duel/([^\'"`\s\)]+)', s))


def main():
    keep_root = duel_root_refs()
    if os.path.isdir(DST):
        # app/www 를 무엇이 붙들고 있으면(로컬 서버·브라우저) 중간에 실패하고
        # **반쯤 만들어진 www 로 빌드가 그대로 진행된다**(APK 13MB 로 나왔다).
        # 지우기부터 실패시켜 그 자리에서 멈추게 한다.
        try:
            shutil.rmtree(DST)
        except OSError as e:
            raise SystemExit('www 를 지울 수 없습니다 - 로컬 서버나 브라우저가 app/www 를 붙들고 있는지 확인하세요: %s' % e)

    n_copy = n_conv = n_shrink = n_skip = 0
    b_src = b_dst = 0

    for root, dirs, files in os.walk(SRC):
        rel = norm(os.path.relpath(root, SRC))
        if rel == '.':
            rel = ''
        dirs[:] = [d for d in dirs if not excluded((rel + '/' + d).lstrip('/'))]
        out = os.path.join(DST, rel) if rel else DST
        os.makedirs(out, exist_ok=True)

        in_duel_states = rel.startswith('arcade_duel/') and rel.endswith('_states')
        in_duel_root = (rel == 'arcade_duel')

        for f in files:
            s = os.path.join(root, f)
            try:
                sz = os.path.getsize(s)
            except OSError:
                continue
            # 발주 원본 — 코드는 _cute50.png 만 부른다
            if '_source.' in f:
                n_skip += 1
                continue
            # 일기토 루트: 참조되는 것만 (나머지는 도구용 시트)
            if in_duel_root and keep_root is not None and f not in keep_root:
                n_skip += 1
                continue

            b_src += sz
            ext = os.path.splitext(f)[1].lower()

            if in_duel_states and ext == '.webp':
                im = Image.open(s)
                im = im.resize((int(im.width * DUEL_SCALE), int(im.height * DUEL_SCALE)), Image.LANCZOS)
                d = os.path.join(out, f)
                im.save(d, 'WEBP', quality=WEBP_Q, method=5)
                n_shrink += 1
            elif ext in CONVERT_EXT:
                im = Image.open(s)
                if im.mode not in ('RGB', 'RGBA'):
                    im = im.convert('RGBA' if 'A' in im.getbands() else 'RGB')
                d = os.path.join(out, os.path.splitext(f)[0] + '.webp')
                im.save(d, 'WEBP', quality=WEBP_Q, method=5)
                n_conv += 1
            else:
                d = os.path.join(out, f)
                shutil.copy2(s, d)
                n_copy += 1
            b_dst += os.path.getsize(d)

    for root, dirs, files in os.walk(DST, topdown=False):
        try:
            if not os.listdir(root):
                os.rmdir(root)
        except OSError:
            pass

    print('축소 %d · 변환 %d · 복사 %d · 제외 %d' % (n_shrink, n_conv, n_copy, n_skip))
    print('assets %.0f MB -> www %.0f MB' % (b_src / 1048576, b_dst / 1048576))
    return b_dst


# 시험 빌드 표식 — APK 는 주소에 ?test=1 을 붙일 수가 없다. 그래서 문서 맨 앞에
# 한 줄을 심어 주소를 바꿔 둔다. 이게 먼저 돌고 본 스크립트가 파싱되므로
# location.search 를 읽는 쪽에서 정상적으로 잡힌다.
#   전 스테이지 해금 · 튜토리얼 완료 · 일기토 49명 ★5~◆다이아 +5 로 시작.
#   한 번만 붙인다 — 셋업이 끝나면 location.replace 로 주소를 지우는데,
#   표식이 없으면 그때 또 ?test=1 을 붙여 무한 새로고침이 된다(검은 화면).
TEST_BOOT = ("<script>/* TEST BUILD */try{"
             "if(!localStorage.getItem('__testBuildDone')"
             "&&location.search.indexOf('test=')<0)"
             "history.replaceState(null,'',location.pathname+'?test=1')"
             "}catch(e){}</script>")


# assets 밖에 있는데 게임이 부르는 것들. 예전엔 assets/ 만 복사해서
# duel/sfx.js 가 앱에 없었고, import('./duel/sfx.js') 가 조용히 실패해
# **소리가 통째로 안 났다**(리그 애니메이션도 같이 죽는다).
EXTRA_DIRS = ['duel']


def copy_extras():
    for d in EXTRA_DIRS:
        if not os.path.isdir(d):
            print('  (없음) %s' % d)
            continue
        dst = os.path.join('app/www', d)
        if os.path.isdir(dst):
            shutil.rmtree(dst)
        # 게임이 쓰는 것만 — 테스트 페이지는 뺀다
        os.makedirs(dst, exist_ok=True)
        n = 0
        for f in sorted(os.listdir(d)):
            src = os.path.join(d, f)
            if not os.path.isfile(src) or not f.endswith('.js'):
                continue
            shutil.copy2(src, os.path.join(dst, f))
            n += 1
        print('  %s : %d개 복사' % (d, n))


def rewrite_html(test=False):
    """index.html(=prototype 사본) 안의 .png/.jpg 경로를 .webp 로 바꾼다.
       원본 prototype.html 은 손대지 않는다."""
    total = 0
    for name, src in [('app/www/index.html', 'prototype.html'),
                      ('app/www/duel_v2.html', 'duel_v2.html')]:
        if not os.path.exists(src):
            continue
        s = io.open(src, encoding='utf-8', errors='surrogateescape').read()
        # assets/ 로 시작하는 경로의 확장자만 바꾼다 — 다른 문자열은 안 건드린다
        def sub(m):
            return m.group(1) + '.webp'
        s2, n = re.subn(r'(assets/[A-Za-z0-9_\-./$${}]*?)\.(?:png|jpg|jpeg)\b', sub, s)
        if test and name.endswith('index.html'):
            j = s2.find('<body')
            j = s2.find('>', j) + 1 if j >= 0 else 0
            s2 = s2[:j] + chr(10) + TEST_BOOT + s2[j:]
        io.open(name, 'w', encoding='utf-8', errors='surrogateescape').write(s2)
        print('%s : 경로 %d곳 .webp 로' % (name, n))
        total += n
    return total


if __name__ == '__main__':
    _test = '--test' in sys.argv
    main()
    copy_extras()
    rewrite_html(_test)
    tot = sum(os.path.getsize(os.path.join(r, f))
              for r, _, fs in os.walk('app/www') for f in fs)
    print('app/www 전체 %.0f MB' % (tot / 1048576))
    if _test:
        print('*** TEST BUILD: all stages unlocked / 49 duel generals at 5-star~diamond +5 ***')
