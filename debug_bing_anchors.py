#!/usr/bin/env python3
import re
import requests
from urllib.parse import quote

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

TARGET_DOMAINS = [
    "imovelweb.com.br",
    "vivareal.com.br",
    "olx.com.br",
    "zapimoveis.com.br",
    "mercadolivre.com.br",
]

QUERY = "apartamento curitiba"
LIMIT = 10

for domain in TARGET_DOMAINS:
    q = f"site:{domain} {QUERY}"
    url = f"https://www.bing.com/search?q={quote(q)}"
    print(f"\n---\nDomain: {domain}\nURL: {url}\n")
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        html = r.text
        # find hrefs with the domain
        pattern = rf'href=["\']([^\'" >]*{re.escape(domain)}[^\'" >]*)["\']'
        matches = re.findall(pattern, html)
        unique = []
        for m in matches:
            if m not in unique and m.startswith('http'):
                unique.append(m)
            if len(unique) >= LIMIT:
                break
        print(f"Found {len(unique)} anchors for {domain}:")
        for u in unique:
            print("  ", u)
    except Exception as e:
        print("Error:", e)
print('\nDone')
