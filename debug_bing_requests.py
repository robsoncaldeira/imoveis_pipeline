import requests
import re
from urllib.parse import quote, unquote

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

def find_links_bing(domain, query, limit=10):
    q = f"site:{domain} {query}"
    url = f"https://www.bing.com/search?q={quote(q)}"
    print('GET', url)
    r = requests.get(url, headers=HEADERS, timeout=15)
    r.raise_for_status()
    html = r.text
    links = []
    # try to find <a href="http...domain..."
    for m in re.finditer(r'href=["\']([^"\']*%s[^"\']*)["\']' % re.escape(domain), html):
        href = m.group(1)
        href = unquote(href)
        if href.startswith('//'):
            href = 'https:' + href
        if href.startswith('/'): 
            href = 'https://www.bing.com' + href
        if href not in links:
            links.append(href)
        if len(links) >= limit:
            break
    return links

if __name__ == '__main__':
    domain = 'vivareal.com.br'
    query = 'apartamento curitiba'
    try:
        links = find_links_bing(domain, query, limit=10)
        print('Found', len(links), 'links:')
        for l in links:
            print(l)
    except Exception as e:
        print('Error:', e)
