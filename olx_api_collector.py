#!/usr/bin/env python3
"""
OLX API Collector: Extract ad URLs from captured network JSON or live API calls.
Priority: parse captured JSON payloads first (even if truncated), then try live fetches with pagination.
"""

import json
import argparse
import time
import requests
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent))
from scraper_escalavel import ImovelDB


def load_capture(capture_path):
    """Load capture JSON file (array of {status, text, type, url})."""
    try:
        with open(capture_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f'Error loading capture: {e}')
        return []


def extract_json_from_text(txt):
    """
    Extract valid JSON from text that may be truncated.
    Falls back to regex pattern matching to find ad URLs directly.
    """
    if not txt or not isinstance(txt, str):
        return None
    
    import re
    
    txt = txt.strip()
    if not txt:
        return None
    
    # Priority 1: Try full parse (if complete)
    if txt.startswith('['):
        start_idx = txt.find('[')
        if start_idx >= 0:
            depth = 0
            for i in range(start_idx, len(txt)):
                if txt[i] == '[':
                    depth += 1
                elif txt[i] == ']':
                    depth -= 1
                    if depth == 0:
                        try:
                            return json.loads(txt[start_idx:i+1])
                        except Exception:
                            pass
    
    # Priority 2: Regex-based fallback for truncated JSON
    # Look for ad_url patterns and list_id patterns
    urls = []
    
    # Pattern 1: "ad_url":"https://www.olx.com.br/vi/...?..."
    for match in re.finditer(r'"ad_url":"(https://[^"]+)"', txt):
        url = match.group(1)
        if url not in urls:
            urls.append(url)
    
    # Pattern 2: "list_id":12345 (use to construct URL if no ad_url)
    for match in re.finditer(r'"list_id":(\d+)', txt):
        list_id = match.group(1)
        url = f'https://www.olx.com.br/vi/{list_id}'
        if url not in urls:
            urls.append(url)
    
    if urls:
        return {'extracted_urls': urls}  # Return dict with extracted URLs
    
    # Priority 3: Try objects
    if '{' in txt:
        start_idx = txt.find('{')
        if start_idx >= 0:
            depth = 0
            for i in range(start_idx, len(txt)):
                if txt[i] == '{':
                    depth += 1
                elif txt[i] == '}':
                    depth -= 1
                    if depth == 0:
                        try:
                            return json.loads(txt[start_idx:i+1])
                        except Exception:
                            pass
    
    return None


def find_candidate_api_urls(capture_entries):
    """Find API endpoint URLs in capture (e.g., apigw.olx.com.br)."""
    candidates = set()
    for e in capture_entries:
        if isinstance(e, dict) and 'url' in e:
            url = e.get('url', '').strip()
            if url and 'api' in url.lower() and 'olx' in url.lower():
                candidates.add(url)
    return list(candidates)


def extract_ad_urls_from_obj(obj, depth=0, max_depth=10):
    """
    Recursively extract ad URLs (ad_url field) and list_id from JSON object.
    Can handle objects, arrays, or lists of mixed items.
    Also handles the special 'extracted_urls' key for regex-extracted results.
    """
    if depth > max_depth:
        return []
    
    urls = []
    
    if isinstance(obj, dict):
        # Special case: already extracted URLs from regex
        if 'extracted_urls' in obj and isinstance(obj['extracted_urls'], list):
            return obj['extracted_urls']
        
        # Direct ad_url field
        if 'ad_url' in obj and isinstance(obj['ad_url'], str):
            urls.append(obj['ad_url'])
        # Fallback: use list_id to construct URL
        if 'list_id' in obj and 'ad_url' not in obj:
            list_id = obj['list_id']
            if isinstance(list_id, int):
                urls.append(f'https://www.olx.com.br/vi/{list_id}')
        # Recurse into dict values
        for v in obj.values():
            urls.extend(extract_ad_urls_from_obj(v, depth + 1, max_depth))
    elif isinstance(obj, list):
        for item in obj:
            urls.extend(extract_ad_urls_from_obj(item, depth + 1, max_depth))
    
    return list(set(urls))  # Remove duplicates


def fetch_json_from_url(url, headers=None, timeout=10):
    """Fetch and parse JSON from URL. Returns (json_obj, response_obj) or (None, None)."""
    try:
        r = requests.get(url, headers=headers, timeout=timeout)
        if r.status_code == 200:
            try:
                obj = r.json()
                return obj, r
            except Exception:
                return None, r
    except Exception:
        pass
    return None, None


def find_pagination_token(obj, resp):
    """Find pagination token (next, cursor, etc.) in JSON or response headers."""
    if isinstance(obj, dict):
        for key in ('next', 'cursor', 'after', 'nextCursor', 'endCursor', 'page_next', 'next_token'):
            if key in obj:
                val = obj[key]
                if val:
                    return str(val)
    
    if resp:
        link_header = resp.headers.get('Link', '')
        if 'rel="next"' in link_header:
            import re
            m = re.search(r'<([^>]+)>;\s*rel="next"', link_header)
            if m:
                return m.group(1)
    
    return None


def main():
    parser = argparse.ArgumentParser(description='OLX API Collector: Parse captured JSON or fetch live API')
    parser.add_argument('--capture', type=str, help='Path to capture JSON file')
    parser.add_argument('--api', type=str, help='Direct API URL to fetch')
    parser.add_argument('--insert-db', action='store_true', help='Insert discovered links into imoveis.db')
    parser.add_argument('--max-pages', type=int, default=5, help='Max pages for pagination')
    parser.add_argument('--preview', type=int, default=10, help='Preview first N URLs')
    parser.add_argument('--delay', type=float, default=1.0, help='Delay between requests (seconds)')
    args = parser.parse_args()

    if not args.capture and not args.api:
        print('Error: provide --capture or --api')
        return

    db = ImovelDB()
    discovered = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

    # STEP 1: Parse capture file for JSON payloads (highest priority)
    if args.capture:
        print(f'📂 Parsing capture file: {args.capture}')
        entries = load_capture(Path(args.capture))
        count_parsed = 0
        for e in entries:
            if not isinstance(e, dict) or not e.get('text'):
                continue
            txt = e.get('text')
            if not isinstance(txt, str):
                continue
            
            obj = extract_json_from_text(txt)
            
            if obj is not None:
                count_parsed += 1
                urls = extract_ad_urls_from_obj(obj)
                for ad in urls:
                    if ad not in discovered:
                        discovered.append(ad)
                        if args.insert_db:
                            try:
                                db.add_link(ad, 'olx.com.br', 'olx_api')
                            except Exception:
                                pass
        
        print(f'  ✓ Parsed {count_parsed} JSON blocks → found {len(discovered)} unique ad URLs')

    # STEP 2: Try live API URLs if enabled (optional)
    candidates = []
    if args.capture:
        candidates.extend(find_candidate_api_urls(load_capture(Path(args.capture))))
    if args.api:
        candidates.append(args.api)

    for url in candidates:
        if not url:
            continue
        
        print(f'\n→ Trying live fetch: {url[:80]}...')
        current_url = url
        pages = 0
        
        while pages < args.max_pages:
            pages += 1
            obj, resp = fetch_json_from_url(current_url, headers=headers)
            if obj is None:
                break
            
            urls = extract_ad_urls_from_obj(obj)
            new_count = sum(1 for ad in urls if ad not in discovered)
            
            for ad in urls:
                if ad not in discovered:
                    discovered.append(ad)
                    if args.insert_db:
                        try:
                            db.add_link(ad, 'olx.com.br', 'olx_api')
                        except Exception:
                            pass
            
            if new_count == 0:
                break
            
            token = find_pagination_token(obj, resp)
            if not token:
                break
            
            if isinstance(token, str) and token.startswith('http'):
                current_url = token
            else:
                sep = '&' if '?' in url else '?'
                current_url = f"{url}{sep}cursor={token}"
            
            time.sleep(args.delay)

    print(f'\n✅ Total discovered: {len(discovered)} unique ad URLs')
    
    if args.preview and discovered:
        preview_count = min(args.preview, len(discovered))
        print(f'\n📋 Preview (first {preview_count}):')
        for url in discovered[:preview_count]:
            print(f'  - {url}')
    
    if args.insert_db:
        print(f'\n✓ Inserted {len(discovered)} links into DB (imoveis.db)')
        print('Next: run ScraperEscalavel to extract full property details and export CSV')


if __name__ == '__main__':
    main()
