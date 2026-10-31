# Fetch the latest METAR and TAF for Japanese aerodromes from the NOAA Aviation Weather Center Data API
# (it relays the reports issued by JMA) and write a compact wx.json for the IFR briefing app.
import json, time, urllib.request, urllib.parse, sys
IDS = """RJAA RJAF RJAH RJAK RJAM RJAN RJAW RJAZ RJBB RJBD RJBE RJBK RJBT RJCA RJCB RJCC
RJCH RJCJ RJCK RJCM RJCN RJCO RJCR RJCT RJCW RJDA RJDB RJDC RJDK RJDM RJDO RJDT
RJDU RJEB RJEC RJEO RJER RJFA RJFC RJFE RJFF RJFG RJFK RJFM RJFN RJFO RJFR RJFS
RJFT RJFU RJFY RJFZ RJGG RJKA RJKB RJKI RJKN RJNA RJNF RJNG RJNH RJNK RJNO RJNS
RJNT RJNW RJNY RJOA RJOB RJOC RJOE RJOF RJOH RJOI RJOK RJOM RJOO RJOR RJOS RJOT
RJOW RJOY RJOZ RJSA RJSC RJSD RJSF RJSH RJSI RJSK RJSM RJSN RJSO RJSR RJSS RJST
RJSU RJSY RJTA RJTC RJTE RJTF RJTH RJTJ RJTK RJTL RJTO RJTQ RJTT RJTU RJTY ROAH
RODN ROIG ROKJ ROKR ROMD ROMY RORA RORE RORH RORK RORS RORT RORY ROTM ROYN""".split()
UA = {'User-Agent': 'ifr-briefing-wx/1.0 (github.com/realbon1-max/IFR)'}
def get(kind, extra=''):
    q = urllib.parse.urlencode({'ids': ','.join(IDS), 'format': 'json'}) + extra
    req = urllib.request.Request(f'https://aviationweather.gov/api/data/{kind}?{q}', headers=UA)
    for k in range(3):
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                b = r.read()
                return json.loads(b) if b.strip() else []
        except Exception as e:
            print(kind, 'retry', e, file=sys.stderr); time.sleep(5 * (k + 1))
    return None
import re, html as H
def imoc_metars():
    # 国際気象海洋（IMOC）のスマホ向けMETAR一覧（地域0〜11）。霞目 RJSU など自衛隊・防衛省の飛行場も載っている
    out = {}
    pat = re.compile(r'(?:\b(METAR|SPECI)\s+)?\b(R[JO][A-Z]{2})\s+(\d{6}Z)\s+([^=\u3000-\uffff]{0,400}?)=')
    for area in range(12):
        url = f'https://imoc.co.jp/SmartPhone/d/metar.php?Lang=Jpn&Area={area}&List=1'
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
                txt = r.read().decode('utf-8', 'replace')
        except Exception as e:
            print('imoc', area, e, file=sys.stderr); continue
        txt = H.unescape(re.sub(r'<[^>]+>', ' ', txt)); txt = re.sub(r'\s+', ' ', txt)
        for typ, icao, ts, body in pat.findall(txt):
            body = body.strip()
            if body.startswith('NIL') or not body: continue
            dd = int(ts[:2]); now = time.gmtime(); prev = time.gmtime(time.time() - 86400)
            if dd not in (now.tm_mday, prev.tm_mday): continue  # 古い報（前月など）は捨てる
            raw = f'{typ or "METAR"} {icao} {ts} {body}='
            if icao not in out or out[icao]['ts'] < ts: out[icao] = {'ts': ts, 'raw': raw}
        time.sleep(1)
    return out
def imoc_tafs():
    # IMOC TAF一覧（地域0〜3）
    out = {}
    pat = re.compile(r'(?:\bTAF\s+(?:(?:AMD|COR)\s+)?)?\b(R[JO][A-Z]{2})\s+(\d{6}Z)\s+(\d{4}/\d{4})\s+([^=　-￿]{0,1500}?)=')
    for area in range(4):
        url = f'https://imoc.co.jp/SmartPhone/d/taf.php?Lang=Jpn&Area={area}'
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
                txt = r.read().decode('utf-8', 'replace')
        except Exception as e:
            print('imoc taf', area, e, file=sys.stderr); continue
        txt = H.unescape(re.sub(r'<[^>]+>', ' ', txt)); txt = re.sub(r'\s+', ' ', txt)
        for icao, ts, valid, body in pat.findall(txt):
            body = body.strip()
            if not body or body.startswith('NIL'): continue
            dd = int(ts[:2]); now = time.gmtime(); prev = time.gmtime(time.time() - 86400)
            if dd not in (now.tm_mday, prev.tm_mday): continue
            raw = f'TAF {icao} {ts} {valid} {body}='
            if icao not in out or out[icao]['ts'] < ts: out[icao] = {'ts': ts, 'raw': raw}
        time.sleep(1)
    return out
# 第一優先は国際気象海洋（IMOC）。IMOCに報が無い飛行場だけ NOAA Aviation Weather Center の中継で補う
im = imoc_metars(); it = imoc_tafs()
m = get('metar'); time.sleep(2); t = get('taf')
if m is None and t is None and not im and not it: sys.exit('no data')
out = {'t': int(time.time()), 'src': '国際気象海洋 IMOC（第一優先）／NOAA Aviation Weather Center（IMOCに無い飛行場を補完）', 'metar': [], 'taf': []}
for icao, v in im.items(): out['metar'].append({'id': icao, 'raw': v['raw'], 'via': 'imoc'})
for icao, v in it.items(): out['taf'].append({'id': icao, 'raw': v['raw'], 'via': 'imoc'})
hm = set(im); ht = set(it); n_nm = n_nt = 0
for x in m or []:
    if x.get('icaoId') in hm or not x.get('rawOb'): continue
    out['metar'].append({'id': x.get('icaoId'), 'raw': x.get('rawOb'), 'via': 'noaa'}); n_nm += 1
for x in t or []:
    if x.get('icaoId') in ht or not x.get('rawTAF'): continue
    out['taf'].append({'id': x.get('icaoId'), 'raw': x.get('rawTAF'), 'via': 'noaa'}); n_nt += 1
json.dump(out, open(sys.argv[1] if len(sys.argv) > 1 else 'wx.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print('metar imoc', len(im), 'noaa', n_nm, '/ taf imoc', len(it), 'noaa', n_nt)
