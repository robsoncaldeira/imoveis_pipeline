import json
import sys
sys.path.insert(0, '.')
from olx_api_collector import extract_json_from_text, extract_ad_urls_from_obj

with open('./output/network_www.olx.com.br_20251114_120445.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print('Capture entries:', len(data))
parsed_count = 0
urls_total = 0

for i, e in enumerate(data):
    if not isinstance(e, dict) or not e.get('text'):
        continue
    txt = e.get('text')
    if not isinstance(txt, str):
        continue
    
    obj = extract_json_from_text(txt)
    
    if obj is not None:
        parsed_count += 1
        urls = extract_ad_urls_from_obj(obj)
        urls_total += len(urls)
        print(f'\nEntry {i}: Parsed JSON block')
        print(f'  Root type: {type(obj).__name__}')
        if isinstance(obj, dict):
            print(f'  Keys: {list(obj.keys())[:5]}')
            # Show first level structure
            for k in list(obj.keys())[:3]:
                v = obj[k]
                if isinstance(v, list):
                    print(f'    {k}: list of {len(v)} items')
                elif isinstance(v, dict):
                    print(f'    {k}: dict with keys {list(v.keys())[:3]}')
        print(f'  Found {len(urls)} ad URLs')
        if urls:
            for u in urls[:3]:
                print(f'    - {u}')

print(f'\nTotal: parsed {parsed_count} blocks, found {urls_total} URLs')
