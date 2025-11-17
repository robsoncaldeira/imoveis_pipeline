import json
import sys
sys.path.insert(0, '.')

# Copiando a lógica para test direto
def extract_json_from_truncated_array(txt):
    """Extract multiple objects from truncated JSON array."""
    if not txt or not txt.startswith('['):
        return None
    
    items = []
    start_idx = 0
    depth = 0
    obj_start = -1
    
    for i in range(len(txt)):
        if txt[i] == '{':
            if depth == 0:
                obj_start = i
            depth += 1
        elif txt[i] == '}':
            depth -= 1
            if depth == 0 and obj_start >= 0:
                try:
                    obj_text = txt[obj_start:i+1]
                    obj = json.loads(obj_text)
                    items.append(obj)
                    print(f"Extracted object at {obj_start}:{i+1}")
                except Exception as e:
                    print(f"Failed to parse object at {obj_start}: {e}")
                obj_start = -1
    
    return items if items else None

with open('./output/network_www.olx.com.br_20251114_120445.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

e = data[0]
txt = e['text']

result = extract_json_from_truncated_array(txt)
print(f"\nResult type: {type(result)}")
if result:
    print(f"Extracted {len(result)} items")
    if len(result) > 0:
        print(f"First item type: {type(result[0])}")
        if isinstance(result[0], dict):
            print(f"First item keys: {list(result[0].keys())}")
