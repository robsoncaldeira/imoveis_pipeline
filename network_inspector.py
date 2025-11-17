#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Network inspector: injects JS to capture fetch/XHR calls on page load and saves captured requests.
Usage:
    python network_inspector.py --url "https://..." --scrolls 6 --wait 3

Saves output to output/network_<hostname>_YYYYMMDD_HHMMSS.json
"""

import argparse
import time
import json
from pathlib import Path
from urllib.parse import urlparse
import undetected_chromedriver as uc

OUTPUT = Path(__file__).parent / 'output'
OUTPUT.mkdir(exist_ok=True)

INJECT_JS = r"""
window.__capturedRequests = [];
(function(){
  // wrap fetch
  const _fetch = window.fetch;
  window.fetch = function(...args){
    return _fetch.apply(this,args).then(async (res)=>{
      try{
        const clone = res.clone();
        const text = await clone.text();
        window.__capturedRequests.push({type:'fetch', url: clone.url, status: clone.status, text: (text && text.length>0? text.substring(0,20000): null)});
      }catch(e){}
      return res;
    });
  };
  // wrap XHR
  const _XHR = window.XMLHttpRequest;
  function ProxyXHR(){
    const xhr = new _XHR();
    const open = xhr.open;
    const send = xhr.send;
    xhr.open = function(method, url){
      this._req_method = method; this._req_url = url; return open.apply(this, arguments);
    };
    xhr.addEventListener('readystatechange', function(){
      try{
        if(this.readyState === 4){
          let txt = null;
          try{ txt = this.responseText && this.responseText.substring(0,20000); }catch(e){}
          window.__capturedRequests.push({type:'xhr', url: this._req_url, method: this._req_method, status: this.status, text: txt});
        }
      }catch(e){}
    });
    return xhr;
  }
  window.XMLHttpRequest = ProxyXHR;
})();
"""


def scroll_and_wait(driver, scrolls=6, pause=1.0):
    for i in range(scrolls):
        try:
            driver.execute_script('window.scrollTo(0, document.body.scrollHeight);')
        except Exception:
            pass
        time.sleep(pause)


def run_inspector(url, scrolls=6, wait=3, headful=True):
    options = uc.ChromeOptions()
    if not headful:
        options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    driver = uc.Chrome(options=options)

    # Add script to run on new document
    try:
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {'source': INJECT_JS})
    except Exception:
        # fallback: inject after load
        pass

    driver.get(url)
    time.sleep(1)
    # If injection failed earlier, inject now
    try:
        driver.execute_script(INJECT_JS)
    except Exception:
        pass

    scroll_and_wait(driver, scrolls=scrolls, pause=1.0)
    time.sleep(wait)

    # Retrieve captured requests
    try:
        captured = driver.execute_script('return window.__capturedRequests || []')
    except Exception:
        captured = []

    driver.quit()

    # Save
    parsed = urlparse(url)
    host = parsed.netloc.replace(':','_')
    ts = time.strftime('%Y%m%d_%H%M%S')
    out_file = OUTPUT / f'network_{host}_{ts}.json'
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(captured, f, ensure_ascii=False, indent=2)
    print(f'Saved {len(captured)} captured requests to: {out_file}')
    return out_file, captured


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Inspect network requests on a page')
    parser.add_argument('--url', '-u', required=True, help='Listing URL to inspect')
    parser.add_argument('--scrolls', type=int, default=6, help='Number of scrolls to trigger XHRs')
    parser.add_argument('--wait', type=int, default=3, help='Seconds to wait after scrolls')
    parser.add_argument('--headful', action='store_true', help='Run with visible browser')
    args = parser.parse_args()

    run_inspector(args.url, scrolls=args.scrolls, wait=args.wait, headful=args.headful)
