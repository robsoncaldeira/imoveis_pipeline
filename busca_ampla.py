import re
import time
import json
import requests
import hashlib
from urllib.parse import quote, urlparse, parse_qs, unquote
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
    "mercadolivre.com.br",
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


def extract_real_url_from_bing_redirect(href):
    """
    Tenta extrair a URL real de um redirecionamento do Bing.
    Exemplos:
    - https://www.bing.com/ck/a?!&&p=...&u=a1...&ntb=1 -> extrai parâmetro 'u'
    - https://www.bing.com/rdr.asp?ref=... -> extrai parâmetro 'ref'
    """
    try:
        if 'bing.com' not in href:
            return href
        
        parsed = urlparse(href)
        params = parse_qs(parsed.query)
        
        # Tentar parâmetro 'u' (ck/a) - pode estar codificado
        if 'u' in params:
            real_url = params['u'][0]
            # Remover prefixo 'a1' ou 'a2' (encoding indicator)
            if real_url.startswith('a'):
                real_url = real_url[2:]
            # Decodificar URL-encoded
            real_url = unquote(real_url)
            # Corrigir artefatos de decodificação (https3A -> https:)
            real_url = real_url.replace('https3A', 'https:').replace('http3A', 'http:')
            real_url = real_url.replace('2F', '/')
            if real_url.startswith('http'):
                return real_url
        
        # Tentar parâmetro 'ref' (rdr.asp) - geralmente já decodificado
        if 'ref' in params:
            real_url = params['ref'][0]
            # Decodificar se necessário
            real_url = unquote(real_url)
            if real_url.startswith('http'):
                return real_url
        
        return None
    except:
        return None


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
            # Skip Bing internal links
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
        """
        Use the browser to perform a Bing site:domain search and extract result links.
        
        FIXED: Agora extrai URLs reais dos domínios alvo, não URLs de redirecionamento do Bing.
        """
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

            # Method 1: Bing results via CSS selector 'li.b_algo h2 a'
            try:
                # Detect if Bing is showing a challenge page and pause for manual solve
                pg = self.driver.page_source
                if 'One last step' in pg or 'Please solve the challenge' in pg or 'Verifying' in pg:
                    print('\n⚠️ Bing is presenting a challenge (CAPTCHA/verification).')
                    print('   Please solve it in the opened browser window.')
                    input('   Press Enter here after you complete the challenge to continue...')

                elems = self.driver.find_elements(By.CSS_SELECTOR, 'li.b_algo h2 a')
                # We'll click anchors instead of trusting hrefs to follow the redirect chain
                for a in elems:
                    try:
                        # If element is not interactable, try to extract href fallback
                        href = a.get_attribute('href')
                        # Try clicking to land on the real page (handles redirects)
                        try:
                            a.click()
                            time.sleep(self.slow_wait)
                        except Exception:
                            # clicking may fail in headless or stale elements; fallback to href
                            pass

                        # If a new tab was opened, switch to it
                        try:
                            handles = self.driver.window_handles
                            if len(handles) > 1:
                                self.driver.switch_to.window(handles[-1])
                                real_url = self.driver.current_url
                            else:
                                real_url = self.driver.current_url
                        except Exception:
                            real_url = href

                        # If the URL is a Bing redirect URL, attempt to extract the real url
                        if real_url and ('bing.com' in real_url or 'microsoft' in real_url):
                            decoded = extract_real_url_from_bing_redirect(real_url)
                            if decoded:
                                real_url = decoded

                        if real_url and domain in real_url and real_url not in links:
                            links.append(real_url)

                        # If we opened a new tab, close it and switch back
                        try:
                            handles = self.driver.window_handles
                            if len(handles) > 1:
                                self.driver.close()
                                self.driver.switch_to.window(handles[0])
                        except Exception:
                            pass

                        if len(links) >= limit:
                            break
                    except Exception:
                        continue
            except Exception as e:
                print(f"  ⚠ CSS selector/click flow falhou: {e}")

            # Method 2: Robust anchor scan - sempre tentar coletar anchors com o domínio alvo
            try:
                anchors = self.driver.find_elements(By.CSS_SELECTOR, 'a')
                for a in anchors:
                    try:
                        href = a.get_attribute('href')
                        if not href:
                            continue
                        # normalize
                        href = href.strip()
                        # If href is a Bing redirect, try to extract real URL
                        if 'bing.com' in href or 'microsoft' in href:
                            real = extract_real_url_from_bing_redirect(href)
                            if real and domain in real and real not in links:
                                links.append(real)
                        else:
                            # Direct link - check domain
                            if domain in href and href.startswith('http'):
                                # remove tracking params
                                if '?' in href:
                                    href_clean = href.split('?')[0]
                                else:
                                    href_clean = href
                                if href_clean not in links:
                                    links.append(href_clean)
                        if len(links) >= limit:
                            break
                    except:
                        continue
            except Exception as e:
                print(f"  ⚠ Anchor scan falhou: {e}")

            return links[:limit]
        except Exception as e:
            print(f"  ✗ Erro no Bing (browser) para {domain}: {e}")
            return []

    def search(self, query, domains=None, links_per_domain=LINKS_PER_DOMAIN):
        if domains is None:
            domains = TARGET_DOMAINS
        
        # Remove duplicatas de domínios
        domains = list(dict.fromkeys(domains))
        
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
