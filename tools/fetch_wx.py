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
m = get('metar'); time.sleep(2); t = get('taf')
im = imoc_metars()
if m is None and t is None and not im: sys.exit('no data')
out = {'t': int(time.time()), 'src': 'NOAA Aviation Weather Center（気象庁発表の METAR/TAF を中継）', 'metar': [], 'taf': []}
for x in m or []:
    out['metar'].append({'id': x.get('icaoId'), 'name': x.get('name'), 'lat': x.get('lat'), 'lon': x.get('lon'), 'elev': x.get('elev'),
                         'obs': x.get('obsTime'), 'raw': x.get('rawOb')})
have = {x['id']: (x.get('raw') or '') for x in out['metar']}
def ts_of(raw):
    g = re.search(r'\s(\d{6})Z', raw or ''); return g.group(1) if g else ''
n_im = 0
for icao, v in im.items():
    # NOAAに無い空港、またはIMOCの方が新しい報だけ追加（アプリ側は新しい方を採用）
    if icao not in have or ts_of(v['raw']) > ts_of(have[icao]):
        out['metar'].append({'id': icao, 'raw': v['raw'], 'via': 'imoc'}); n_im += 1
out['src'] += '／国際気象海洋 IMOC（自衛隊飛行場などNOAAに無いMETAR）'
for x in t or []:
    out['taf'].append({'id': x.get('icaoId'), 'name': x.get('name'), 'lat': x.get('lat'), 'lon': x.get('lon'),
                       'issue': x.get('issueTime'), 'raw': x.get('rawTAF')})
json.dump(out, open(sys.argv[1] if len(sys.argv) > 1 else 'wx.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print('metar', len(out['metar']), 'taf', len(out['taf']), 'imoc added', n_im)
