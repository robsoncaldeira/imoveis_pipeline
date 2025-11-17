from olx_api_collector import load_capture, extract_first_json, extract_ad_urls_from_obj

entries = load_capture('output/network_www.olx.com.br_20251114_120445.json')
print('entries:', len(entries))
for i,e in enumerate(entries[:6]):
    txt = e.get('text') if isinstance(e, dict) else None
    print('\n--- entry', i, 'len text', len(txt) if txt else 0)
    sub = extract_first_json(txt) if txt else None
    print('sub found:', bool(sub))
    if sub:
        try:
            import json
            obj = json.loads(sub)
            print('obj type', type(obj))
            urls = extract_ad_urls_from_obj(obj)
            print('found urls:', len(urls))
            if urls:
                for u in urls[:10]:
                    print(' -', u)
        except Exception as ex:
            print('parse error', ex)
