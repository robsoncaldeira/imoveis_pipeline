# -*- coding: utf-8 -*-
"""
Network utilities: load proxy list and user-agent list, and helper to configure Chrome options.
"""
import random
from pathlib import Path


def load_proxies(file_path):
    if not file_path:
        return []
    p = Path(file_path)
    if not p.exists():
        return []
    lines = [l.strip() for l in p.read_text(encoding='utf-8').splitlines() if l.strip()]
    # Expect proxies in format host:port or http://user:pass@host:port
    return lines


def load_user_agents(file_path=None):
    # If file provided, load; else return a small built-in list
    if file_path:
        p = Path(file_path)
        if p.exists():
            return [l.strip() for l in p.read_text(encoding='utf-8').splitlines() if l.strip()]
    return [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15',
    ]


def pick_random(seq):
    if not seq:
        return None
    return random.choice(seq)


def configure_chrome_options(options, proxy=None, user_agent=None, headless=False):
    # options is undetected_chromedriver.ChromeOptions
    if headless:
        try:
            options.add_argument('--headless=new')
        except Exception:
            pass
    # Common flags
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    if user_agent:
        options.add_argument(f'--user-agent={user_agent}')
    if proxy:
        options.add_argument(f'--proxy-server={proxy}')
    return options
