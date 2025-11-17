import json

with open('./output/network_www.olx.com.br_20251114_120445.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

e = data[0]
txt = e['text']

print(f"Text length: {len(txt)}")
print(f"First 100 chars: {txt[:100]}")
print(f"Starts with '[': {txt.strip().startswith('[')}")

# Try to manually find and extract
start_idx = txt.find('[')
print(f"Position of '[': {start_idx}")

if start_idx >= 0:
    depth = 0
    end_idx = -1
    for i in range(start_idx, min(start_idx + 1000, len(txt))):  # Check first 1000 chars
        if txt[i] == '[':
            depth += 1
        elif txt[i] == ']':
            depth -= 1
            if depth == 0:
                end_idx = i + 1
                print(f"Found closing bracket at position {i}")
                break
    
    if end_idx > 0:
        print(f"Trying to parse from {start_idx} to {end_idx} ({end_idx - start_idx} chars)")
        try:
            obj = json.loads(txt[start_idx:end_idx])
            print(f"Success! Type: {type(obj)}, len: {len(obj) if isinstance(obj, (list, dict)) else 'N/A'}")
        except Exception as e:
            print(f"Failed to parse: {e}")
    else:
        print("Could not find balanced closing bracket")
