import time
from urllib.parse import quote
from selenium.webdriver.common.by import By
import undetected_chromedriver as uc

query = 'site:vivareal.com.br apartamento curitiba'
url = f"https://www.bing.com/search?q={quote(query)}"
print('Opening', url)
options = uc.ChromeOptions()
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
# Run visible for debugging
# options.add_argument('--headless=new')
try:
    driver = uc.Chrome(options=options, version_main=None)
    driver.get(url)
    time.sleep(3)
    elems = driver.find_elements(By.CSS_SELECTOR, 'li.b_algo')
    print('Found li.b_algo count:', len(elems))
    if elems:
        print('First li.b_algo outerHTML snippet:')
        print(elems[0].get_attribute('outerHTML')[:1000])
    else:
        # try other selectors
        anchors = driver.find_elements(By.CSS_SELECTOR, 'a')
        print('Total anchors:', len(anchors))
        count_domain = sum(1 for a in anchors if a.get_attribute('href') and 'vivareal.com.br' in a.get_attribute('href'))
        print('Anchors with domain vivareal:', count_domain)
    driver.quit()
except Exception as e:
    print('Error launching browser:', e)
