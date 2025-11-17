import time
from urllib.parse import quote
from selenium.webdriver.common.by import By
import undetected_chromedriver as uc

DOMAINS = [
    'imovelweb.com.br',
    'vivareal.com.br',
    'olx.com.br',
    'zapimoveis.com.br',
    'mercadolivre.com.br',
]

query_template = 'site:{domain} apartamento curitiba'

options = uc.ChromeOptions()
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')

for domain in DOMAINS:
    try:
        q = query_template.format(domain=domain)
        url = f"https://www.bing.com/search?q={quote(q)}"
        print('\n---')
        print('Domain:', domain)
        print('Opening', url)
        driver = uc.Chrome(options=options, version_main=None)
        driver.get(url)
        time.sleep(3)
        anchors = driver.find_elements(By.CSS_SELECTOR, 'a')
        total = len(anchors)
        count_domain = 0
        samples = []
        for a in anchors:
            href = a.get_attribute('href')
            if href and domain in href:
                count_domain += 1
                if len(samples) < 8:
                    samples.append(href)
        print('Total anchors:', total)
        print(f'Anchors with domain {domain}:', count_domain)
        for s in samples:
            print('  -', s[:200])
        driver.quit()
    except Exception as e:
        print('Error for domain', domain, e)
