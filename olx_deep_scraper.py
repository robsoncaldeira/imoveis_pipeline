#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deep scraper for OLX listing pages.
- Crawls listing pagination (simple page param strategy)
- Extracts ad links from listing pages
- Visits each ad and extracts structured data (JSON-LD + fallbacks)
- Inserts property records into existing SQLite `imoveis.db` using ImovelDB

Usage:
    python olx_deep_scraper.py --url "https://www.olx.com.br/imoveis/..." --pages 3 --headless

Note: OLX pages can be JS-heavy. This script uses undetected-chromedriver for best results.
"""

import argparse
import time
import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
import undetected_chromedriver as uc
import json as _json
import re as _re

# Import ImovelDB from existing module
from scraper_escalavel import ImovelDB
from net_utils import load_proxies, load_user_agents, pick_random, configure_chrome_options


def scroll_page(driver, pause=1.0, scrolls=6):
    """Scroll page to load lazy content."""
    for _ in range(scrolls):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(pause)


def extract_links_from_listing(html, base_url):
    """Extract candidate ad links from a listing page HTML.
    We look for anchors with href containing olx domain or typical ad paths.
    """
    soup = BeautifulSoup(html, "html.parser")
    anchors = soup.find_all('a', href=True)
    links = set()
    for a in anchors:
        href = a['href']
        # Normalize
        if href.startswith('/'):
            href = urljoin(base_url, href)
        if 'olx.com.br' not in href:
            continue
        # Heuristics: ad pages often include specific keywords OR are long OLX URLs
        if re.search(r'/anunci(o|os)|/anuncio/|/imoveis/|/anuncios/|/venda/|/aluguel/|/anuncios-|/anuncio-', href):
            links.add(href.split('?')[0])
            continue
        # Also accept anchors that contain image descendants (typical ad cards)
        if a.find('img'):
            # avoid category/filter links (short)
            if len(href) > 40:
                links.add(href.split('?')[0])
                continue
        # Accept long olx links as likely ad/resource links
        if len(href) > 60:
            links.add(href.split('?')[0])
    return list(links)


def extract_embedded_json_links(html):
    """Try to find embedded JSON objects in page that contain listing URLs.
    Look for common inline variables like window.__PRELOADED_STATE__ or similar.
    """
    candidates = set()
    # Search for simple patterns
    patterns = [r'window\.__PRELOADED_STATE__\s*=\s*(\{.*?\});',
                r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\});',
                r'window\.__SSR_STATE__\s*=\s*(\{.*?\});']
    for pat in patterns:
        for m in _re.finditer(pat, html, _re.S):
            try:
                txt = m.group(1)
                data = _json.loads(txt)
                # find urls in nested dicts
                def walk(obj):
                    if isinstance(obj, dict):
                        for k, v in obj.items():
                            walk(v)
                    elif isinstance(obj, list):
                        for it in obj:
                            walk(it)
                    elif isinstance(obj, str):
                        if 'olx.' in obj or 'olx.com.br' in obj:
                            if obj.startswith('http'):
                                candidates.add(obj.split('?')[0])
                walk(data)
            except Exception:
                continue
    return list(candidates)


def parse_ad_page(html, url):
    """Extract structured data from an ad page using JSON-LD then fallbacks."""
    soup = BeautifulSoup(html, "html.parser")
    # Try JSON-LD
    title = None
    price = None
    endereco = None
    cidade = None
    estado = None
    cep = None
    contato = None
    descricao = None

    # JSON-LD
    scripts = soup.find_all('script', type='application/ld+json')
    for s in scripts:
        try:
            data = json.loads(s.string or '{}')
        except Exception:
            continue
        # If it's an Offer or Product
        if isinstance(data, dict):
            if data.get('@type') in ('Offer', 'Product', 'Apartment', 'SingleFamilyResidence'):
                title = title or data.get('name')
                offers = data.get('offers')
                if isinstance(offers, dict):
                    price = price or offers.get('price')
                addr = data.get('address')
                if isinstance(addr, dict):
                    endereco = endereco or addr.get('streetAddress')
                    cidade = cidade or addr.get('addressLocality')
                    estado = estado or addr.get('addressRegion')
                    cep = cep or addr.get('postalCode')
            # some pages include description/name
            title = title or data.get('name')
            descricao = descricao or data.get('description')

    # Fallbacks: meta tags
    if not descricao:
        md = soup.find('meta', {'name': 'description'})
        if md and md.get('content'):
            descricao = md['content']
    if not title:
        t = soup.find('title')
        if t:
            title = t.get_text(strip=True)
    # Regex fallbacks
    text = soup.get_text(' ', strip=True)
    if not price:
        m = re.search(r'R\$\s*[0-9\.,]+', text)
        if m:
            price = m.group(0)
    # CEP (xxxxx-xxx)
    if not cep:
        m = re.search(r'\b\d{5}-\d{3}\b', text)
        if m:
            cep = m.group(0)
    # Phone
    if not contato:
        m = re.search(r'\(?\d{2}\)?\s*\d{4,5}-\d{4}', text)
        if m:
            contato = m.group(0)
    # Address heuristics
    if not endereco:
        # look for address labels
        addr_tags = soup.find_all(lambda tag: tag.name in ['p', 'span', 'div'] and 'bairro' in (tag.get_text(' ').lower()))
        if addr_tags:
            endereco = addr_tags[0].get_text(' ', strip=True)

    # City/State fallback from breadcrumb or text
    if not cidade or not estado:
        # Try meta og:site_name or breadcrumb
        crumbs = soup.select('a[rel="breadcrumb"]') or soup.select('.breadcrumb a')
        if crumbs:
            parts = [c.get_text(strip=True) for c in crumbs]
            if parts:
                if not cidade and len(parts) >= 1:
                    cidade = parts[-1]

    return {
        'titulo': title,
        'preco': price,
        'descricao': descricao,
        'endereco': endereco,
        'cidade': cidade,
        'estado': estado,
        'cep': cep,
        'contato': contato,
        'link': url,
    }


def run_scraper(start_url, max_pages=5, headless=True, delay=1.0, max_ads=None, proxy_file=None, ua_file=None):
    db = ImovelDB()
    options = uc.ChromeOptions()
    proxies = load_proxies(proxy_file)
    uas = load_user_agents(ua_file)
    proxy = pick_random(proxies)
    ua = pick_random(uas)
    configure_chrome_options(options, proxy=proxy, user_agent=ua, headless=headless)
    try:
        driver = uc.Chrome(options=options)
    except TypeError:
        driver = uc.Chrome(options=options)

    all_ad_links = []
    seen_links = set()

    parsed = urlparse(start_url)
    base = f"{parsed.scheme}://{parsed.netloc}"

    for page in range(1, max_pages + 1):
        # Try common OLX pagination patterns: page parameter 'page' or '?o='
        if '?' in start_url:
            page_url = start_url + f'&page={page}'
        else:
            # append ?page=N
            page_url = start_url + (f'?page={page}')

        print(f"[listing] Loading page {page}: {page_url}")
        try:
            driver.get(page_url)
            time.sleep(delay)
            scroll_page(driver, pause=0.8, scrolls=4)
            html = driver.page_source
        except Exception as e:
            print(f"Error loading listing page {page_url}: {e}")
            continue

        links = extract_links_from_listing(html, base)
        # If no links found, try to extract from embedded JSON
        if not links:
            embedded = extract_embedded_json_links(html)
            if embedded:
                print(f"  extracted {len(embedded)} links from embedded JSON")
                links = embedded
        new_links = 0
        for l in links:
            if l not in seen_links:
                seen_links.add(l)
                all_ad_links.append(l)
                new_links += 1
        print(f"  found {len(links)} candidate links, {new_links} new")

        if max_ads and len(all_ad_links) >= max_ads:
            break

        # Basic stop: if no new links found on this page, break
        if new_links == 0:
            print("  no new links on this page — stopping pagination")
            break

    print(f"Total ad links collected: {len(all_ad_links)}")

    # Insert collected links into links table (do not process immediately unless asked)
    inserted = 0
    for link in all_ad_links:
        try:
            db.add_link(link, 'olx.com.br', None)
            inserted += 1
        except Exception:
            continue

    # Optionally process immediately: we'll leave processing to the ScraperEscalavel (external orchestration)
    driver.quit()
    print(f"Done. Inserted {inserted} links into DB (imoveis.links). Use ScraperEscalavel to process them.")
    return len(all_ad_links), inserted


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='OLX deep scraper')
    parser.add_argument('--url', '-u', required=True, help='Starting OLX listing URL')
    parser.add_argument('--pages', type=int, default=3, help='Max listing pages to crawl')
    parser.add_argument('--headless', action='store_true', help='Run browser headless')
    parser.add_argument('--max-ads', type=int, default=0, help='Max ads to process (0 = all)')
    parser.add_argument('--proxy-file', type=str, default=None, help='File with proxies, one per line')
    parser.add_argument('--ua-file', type=str, default=None, help='File with user-agents, one per line')
    args = parser.parse_args()

    run_scraper(args.url, max_pages=args.pages, headless=args.headless, max_ads=(args.max_ads or None), proxy_file=args.proxy_file, ua_file=args.ua_file)
