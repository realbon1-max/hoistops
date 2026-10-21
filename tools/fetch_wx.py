# Fetch the latest METAR and TAF for Japanese aerodromes from the NOAA Aviation Weather Center Data API
# (it relays the reports issued by JMA) and write a compact wx.json for the HOIST OPS app.
import json, time, urllib.request, urllib.parse, sys
IDS = """RJCC RJCJ RJCH RJCB RJCK RJCM RJCN RJCW RJEC RJCO RJER RJEB RJEO RJCR RJCA RJCT RJCY
RJSA RJSM RJSH RJSI RJSK RJSR RJSY RJSC RJSS RJST RJSU RJSF RJSN RJSD
RJTT RJAA RJTJ RJTY RJTA RJAH RJTU RJTL RJTK RJTE RJTF RJAK RJTO RJTH RJAN RJAZ RJTQ RJTC RJTR
RJAF RJNT RJNK RJNW RJNS RJGG RJNA RJNG RJNH RJNY RJNO RJAW
RJBB RJOO RJBE RJBD RJBT RJOY RJOE RJOF RJOZ
RJOB RJOA RJOI RJOW RJOC RJOH RJOR RJDC RJOT RJOK RJOM RJOS RJOP
RJFF RJFR RJFS RJFU RJFT RJFO RJFM RJFK RJFN RJFZ RJFA RJFY RJFE RJDB RJDT RJFG RJKA RJKN RJKB RJFC RJDA RJFW
ROAH RODN ROMD ROKJ ROMY RORS ROIG ROYN ROTM RORK RORY RORE RORA RJAM""".split()
UA = {'User-Agent': 'hoistops-wx/1.0 (github.com/realbon1-max/hoistops)'}
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
m = get('metar'); time.sleep(2); t = get('taf')
if m is None and t is None: sys.exit('no data')
out = {'t': int(time.time()), 'src': 'NOAA Aviation Weather Center（気象庁発表の METAR/TAF を中継）', 'metar': [], 'taf': []}
for x in m or []:
    out['metar'].append({'id': x.get('icaoId'), 'name': x.get('name'), 'lat': x.get('lat'), 'lon': x.get('lon'), 'elev': x.get('elev'),
                         'obs': x.get('obsTime'), 'raw': x.get('rawOb')})
for x in t or []:
    out['taf'].append({'id': x.get('icaoId'), 'name': x.get('name'), 'lat': x.get('lat'), 'lon': x.get('lon'),
                       'issue': x.get('issueTime'), 'raw': x.get('rawTAF')})
json.dump(out, open(sys.argv[1] if len(sys.argv) > 1 else 'wx.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print('metar', len(out['metar']), 'taf', len(out['taf']))
