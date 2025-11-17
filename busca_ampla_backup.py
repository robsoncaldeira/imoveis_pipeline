import re
import time
import json
import requests
import hashlib
from urllib.parse import quote
from selenium.webdriver.common.by import By
from pathlib import Path
from datetime import datetime
import undetected_chromedriver as uc

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# Sites to include in the broad search
TARGET_DOMAINS = [
    "imovelweb.com.br",
    "vivareal.com.br",
    "olx.com.br",
    "zapimoveis.com.br",
    "vivareal.com.br",
    "mercadolivre.com.br",
    "vivareal.com.br",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

# Limits
LINKS_PER_DOMAIN = 5
MAX_PAGES_TO_VISIT = 50

price_re = re.compile(r"R\$\s*[\d\.\,]+")
area_re = re.compile(r"(\d{2,4})\s*m[²2]", re.IGNORECASE)
rooms_re = re.compile(r"(\d+)\s*(?:quarto|quartos|q|qt)\b", re.IGNORECASE)


def bing_site_search(query, domain, limit=5):
    """(Fallback) Performs a Bing site:domain search using requests.

    NOTE: For JS-rendered SERP this may fail; BroadSearcher uses browser method instead.
    """
    q = f"site:{domain} {query}"
    url = f"https://www.bing.com/search?q={quote(q)}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        html = resp.text
        # Extract links from search results (basic fallback)
        links = []
        for m in re.finditer(r'<a href="(https?://[^\"]+)"', html):
            link = m.group(1)
            if "bing.com" in link or "microsoft" in link:
                continue
            if link not in links:
                links.append(link)
            if len(links) >= limit:
                break
        return links
    except Exception as e:
        print(f"  ✗ Erro na busca Bing para {domain}: {e}")
        return []


def extract_from_text(text, url=None):
    """Extract price, area and rooms from a page text using heuristics."""
    if not text:
        return None
    price = None
    area = None
    rooms = None

    mprice = price_re.search(text)
    if mprice:
        price = mprice.group(0)

    marea = area_re.search(text)
    if marea:
        area = f"{marea.group(1)} m²"

    mrooms = rooms_re.search(text)
    if mrooms:
        rooms = f"{mrooms.group(1)} Q"

    title = None
    # try to get first meaningful line as title
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    if lines:
        title = lines[0][:150]

    if not (price or area or title):
        return None

    uid = hashlib.md5(((title or "") + (price or "") + (url or "")).encode()).hexdigest()
    return {
        "id": uid,
        "titulo": title,
        "preco": price,
        "metragem": area,
        "quartos": rooms,
        "link": url,
        "data_coleta": datetime.now().isoformat()
    }


class BroadSearcher:
    def __init__(self, headless=True, slow_wait=2):
        self.headless = headless
        self.slow_wait = slow_wait
        self.driver = None

    def start_driver(self):
        try:
            options = uc.ChromeOptions()
            # explicit headless control
            if self.headless:
                options.add_argument('--headless=new')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument("--disable-blink-features=AutomationControlled")
            self.driver = uc.Chrome(options=options, version_main=None)
            time.sleep(1)
            return True
        except Exception as e:
            print(f"✗ Falha ao iniciar driver undetected: {e}")
            return False

    def visit_and_extract(self, url):
        try:
            self.driver.get(url)
            time.sleep(self.slow_wait)
            # scroll a bit
            for _ in range(2):
                try:
                    self.driver.execute_script("window.scrollBy(0, window.innerHeight);")
                except:
                    pass
                time.sleep(1)
            text = self.driver.page_source
            # Normalize text
            text_clean = re.sub(r"\s+", " ", text)
            data = extract_from_text(text_clean, url)
            return data
        except Exception as e:
            print(f"  ✗ Erro ao visitar {url}: {e}")
            return None

    def bing_site_search_browser(self, query, domain, limit=5):
        """Use the browser to perform a Bing site:domain search and extract result links.

        This avoids issues where SERP is rendered by JS or blocked for non-JS clients.
        FIXED: Extracts real domain URLs, not Bing redirects.
        """
        from urllib.parse import urlparse, parse_qs
        
        q = f"site:{domain} {query}"
        url = f"https://www.bing.com/search?q={quote(q)}"
        links = []
        try:
            self.driver.get(url)
            time.sleep(self.slow_wait + 1)
            # scroll a bit to ensure JS loads
            try:
                self.driver.execute_script("window.scrollBy(0, window.innerHeight);")
            except:
                pass
            time.sleep(1)

            # Bing results: 'li.b_algo h2 a' is a stable selector
            try:
                elems = self.driver.find_elements(By.CSS_SELECTOR, 'li.b_algo h2 a')
            except Exception:
                elems = []

            for a in elems:
                try:
                    href = a.get_attribute('href')
                    if not href or not href.startswith('http'):
                        continue
                    
                    # Handle Bing redirect URLs (rdr.asp?ref=...)
                    if 'bing.com' in href or 'microsoft' in href:
                        # Try to extract real URL from Bing redirect
                        try:
                            if 'rdr.asp' in href or 'ref=' in href:
                                parsed = urlparse(href)
                                params = parse_qs(parsed.query)
                                if 'ref' in params:
                                    real_url = params['ref'][0]
                                    if domain in real_url and real_url not in links:
                                        links.append(real_url)
                                        continue
                        except:
                            pass
                        continue
                    
                    # Direct link - check if matches target domain
                    if domain in href:
                        if href not in links:
                            links.append(href)
                        if len(links) >= limit:
                            break
                except Exception as e:
                    continue

            # Fallback: parse page source to find domain links
            if not links:
                try:
                    page_source = self.driver.page_source
                    # Look for href patterns pointing to target domain
                    pattern = rf'href=["\']([^\'"]*{re.escape(domain)}[^\'"]*)["\']'
                    for match in re.finditer(pattern, page_source):
                        href = match.group(1)
                        if href and domain in href and 'http' in href:
                            # Clean up URL parameters
                            if '?' in href:
                                href = href.split('?')[0]
                            if href not in links:
                                links.append(href)
                            if len(links) >= limit:
                                break
                except:
                    pass

            return links[:limit]
        except Exception as e:
            print(f"  ✗ Erro no Bing (browser) para {domain}: {e}")
            return []
from urllib.parse import urlparse, parse_qs

    def search(self, query, domains=None, links_per_domain=LINKS_PER_DOMAIN):
        if domains is None:
            domains = TARGET_DOMAINS
        results = []
        visited = set()

        if not self.start_driver():
            print("❌ Não foi possível iniciar o navegador. Abortando.")
            return []

        try:
            for domain in domains:
                print(f"\n🔎 Buscando em: {domain}")
                # Use browser-based SERP extraction to handle JS-rendered pages
                links = self.bing_site_search_browser(query, domain, limit=links_per_domain)
                # Fallback to requests-based search if browser returned none
                if not links:
                    links = bing_site_search(query, domain, limit=links_per_domain)
                print(f"  ✓ {len(links)} links encontrados em {domain}")
                for link in links:
                    if link in visited:
                        continue
                    visited.add(link)
                    print(f"  → Visitando: {link}")
                    item = self.visit_and_extract(link)
                    if item:
                        results.append(item)
                    if len(results) >= MAX_PAGES_TO_VISIT:
                        break
                if len(results) >= MAX_PAGES_TO_VISIT:
                    break
        finally:
            try:
                self.driver.quit()
            except:
                pass

        # deduplicate by id
        unique = {r['id']: r for r in results}
        return list(unique.values())


def save_results(imoveis, prefix="imoveis_busca_ampla"):
    if not imoveis:
        print("\n❌ Nenhum resultado para salvar")
        return None
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    nome = f"{prefix}_{timestamp}.json"
    caminho = OUTPUT_DIR / nome
    with open(caminho, 'w', encoding='utf-8') as f:
        json.dump(imoveis, f, ensure_ascii=False, indent=2)
    print(f"\n✅ {len(imoveis)} resultado(s) salvo(s) em: {caminho.name}")
    return caminho


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        query = ' '.join(sys.argv[1:])
    else:
        query = input('Digite a busca (ex: "apartamento curitiba"): ').strip() or 'apartamento curitiba'

    print(f"Iniciando busca ampla por: '{query}'")
    # Abrir navegador visível para debug (headless=False)
    buscador = BroadSearcher(headless=False, slow_wait=2)
    resultados = buscador.search(query)
    if resultados:
        save_results(resultados)
    else:
        print('\n⚠️ Nenhum resultado encontrado na busca ampla.')
