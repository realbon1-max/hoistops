# 国交省「公共用・非公共用ヘリポート一覧」（2026-09-01現在）の所在地を国土地理院の住所検索で緯度経度にする（一度だけ手動実行）
import json, sys, time, urllib.request, urllib.parse
out = []
for line in open('tools/heliports_mlit.tsv', encoding='utf-8'):
    k, n, m, a = line.rstrip('\n').split('\t')
    q = a; r = None
    for t in range(3):
        try:
            with urllib.request.urlopen('https://msearch.gsi.go.jp/address-search/AddressSearch?q=' + urllib.parse.quote(q), timeout=30) as f:
                j = json.loads(f.read()); r = j[0] if j else None; break
        except Exception as e:
            print('retry', n, e, file=sys.stderr); time.sleep(3)
    c = r['geometry']['coordinates'] if r else [None, None]
    out.append({'k': k, 'n': n, 'm': m, 'a': a, 'lat': c[1], 'lon': c[0], 'hit': r['properties']['title'] if r else None})
    time.sleep(0.4)
json.dump(out, open(sys.argv[1], 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
print(sum(1 for o in out if o['lat'] is None), 'not found')
