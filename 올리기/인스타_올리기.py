# 인스타그램 카드뉴스 올리기 (알뜰폰노트, 2026.11.11)
# - 토큰은 깃허브 금고(Secrets) IG_TOKEN에서만 꺼내 씀. 화면·기록에 토큰을 찍지 않음.
# - 하는 일은 "게시물 올리기"뿐. 메시지(DM)·댓글·광고 기능은 쓰지 않음.
# 쓰는 법 (깃허브 Actions가 실행):
#   python 올리기/인스타_올리기.py 확인            → 토큰이 맞는지, 계정 이름만 확인 (게시 안 함)
#   python 올리기/인스타_올리기.py 올리기 001_daiso → cards/001_daiso/1~10.jpg + caption.txt 를 한 게시물로 올림
import json, os, sys, time, urllib.parse, urllib.request, urllib.error
from pathlib import Path

API = 'https://graph.facebook.com/v27.0/'
IG_ID = os.environ.get('IG_USER_ID', '17841432087397506')   # @kkdkgd1
TOKEN = os.environ.get('IG_TOKEN', '')
REPO = os.environ.get('GITHUB_REPOSITORY', 'sujung67966-png/gnt-cards')
BRANCH = os.environ.get('GITHUB_REF_NAME', 'main')
ROOT = Path(__file__).resolve().parent.parent


def call(path, params=None, post=False):
    params = dict(params or {}, access_token=TOKEN)
    data = urllib.parse.urlencode(params).encode()
    url = API + path
    req = urllib.request.Request(url, data=data) if post else urllib.request.Request(url + '?' + data.decode())
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', 'replace').replace(TOKEN, '***')
        sys.exit(f'메타 오류 ({e.code}): {body}')


def check():
    me = call(IG_ID, {'fields': 'username,media_count'})
    print(f"토큰 정상. 인스타 계정: @{me.get('username')} (게시물 {me.get('media_count')}개)")
    lim = call(IG_ID + '/content_publishing_limit', {'fields': 'quota_usage,config'})
    d = (lim.get('data') or [{}])[0]
    print(f"최근 24시간 올린 수: {d.get('quota_usage')} / 한도 {d.get('config', {}).get('quota_total')}")


def wait_ready(cid):
    for _ in range(30):
        s = call(cid, {'fields': 'status_code'}).get('status_code')
        if s == 'FINISHED':
            return
        if s in ('ERROR', 'EXPIRED'):
            sys.exit(f'그림 준비 실패: {s}')
        time.sleep(5)
    sys.exit('그림 준비가 너무 오래 걸려 멈춤')


def post(folder):
    d = ROOT / 'cards' / folder
    imgs = sorted(d.glob('*.jpg'), key=lambda p: int(p.stem) if p.stem.isdigit() else 99)
    cap_file = d / 'caption.txt'
    if not 2 <= len(imgs) <= 10:
        sys.exit(f'{folder}: jpg 그림이 2~10장이어야 함 (지금 {len(imgs)}장)')
    if not cap_file.exists():
        sys.exit(f'{folder}: caption.txt 가 없음')
    caption = cap_file.read_text(encoding='utf-8').strip()
    tags = caption.count('#')
    if tags > 5:
        sys.exit(f'해시태그가 {tags}개 → 5개 이하로 줄여야 함')
    check()
    kids = []
    for p in imgs:
        url = f'https://raw.githubusercontent.com/{REPO}/{BRANCH}/cards/{folder}/{p.name}'
        cid = call(IG_ID + '/media', {'image_url': url, 'is_carousel_item': 'true'}, post=True)['id']
        wait_ready(cid); kids.append(cid); print('그림 준비:', p.name)
    car = call(IG_ID + '/media', {'media_type': 'CAROUSEL', 'children': ','.join(kids), 'caption': caption}, post=True)['id']
    wait_ready(car)
    mid = call(IG_ID + '/media_publish', {'creation_id': car}, post=True)['id']
    link = call(mid, {'fields': 'permalink'}).get('permalink')
    print('올림 완료:', link)
    (d / '올림.txt').write_text(f'{time.strftime("%Y-%m-%d %H:%M")} {link}\n', encoding='utf-8')


if __name__ == '__main__':
    if not TOKEN:
        sys.exit('IG_TOKEN 이 없음 (깃허브 금고 확인)')
    mode = sys.argv[1] if len(sys.argv) > 1 else '확인'
    if mode == '확인':
        check()
    elif mode == '올리기' and len(sys.argv) > 2:
        post(sys.argv[2])
    else:
        sys.exit('쓰는 법: 확인 | 올리기 폴더이름')
