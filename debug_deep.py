import json
import sys
sys.path.insert(0, '.')
from olx_api_collector import extract_json_from_text

with open('./output/network_www.olx.com.br_20251114_120445.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

e = data[0]
txt = e['text']
obj = extract_json_from_text(txt)

print("Parsed object type:", type(obj))

if obj and isinstance(obj, list) and len(obj) > 0:
    print('First array element type:', type(obj[0]))
    print('First element keys:', list(obj[0].keys())[:5] if isinstance(obj[0], dict) else 'not a dict')
    
    # Dig deeper into GalleryGroup structure
    if 'content' in obj[0]:
        content = obj[0]['content']
        print(f'content has {len(content)} items')
        if len(content) > 0:
            print('First content item type:', type(content[0]))
            print('First content item keys:', list(content[0].keys())[:5] if isinstance(content[0], dict) else 'not a dict')
            if 'content' in content[0]:
                inner_content = content[0]['content']
                print(f'Inner content has {len(inner_content)} items')
                if len(inner_content) > 0:
                    print('First inner item:', type(inner_content[0]))
                    if isinstance(inner_content[0], dict):
                        print('First inner item keys:', list(inner_content[0].keys()))
                        if 'ad_url' in inner_content[0]:
                            print('ad_url found:', inner_content[0]['ad_url'])
                        if 'list_id' in inner_content[0]:
                            print('list_id found:', inner_content[0]['list_id'])
