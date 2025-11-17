import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from pathlib import Path

# Iniciar navegador
options = Options()
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option('useAutomationExtension', False)

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

print("Acessando ImóvelWeb...")
driver.get("https://www.imovelweb.com.br/venda/apartamentos/curitiba-pr")

print("Aguardando carregamento...")
time.sleep(8)

# Scroll
for i in range(3):
    driver.execute_script("window.scrollBy(0, window.innerHeight);")
    time.sleep(2)

# Salvar HTML para análise
html = driver.page_source

# Salvar em arquivo
with open("imovelweb_debug.html", "w", encoding="utf-8") as f:
    f.write(html)

print("✓ HTML salvo em: imovelweb_debug.html")

# Análise básica
if "Não encontramos imóveis" in html:
    print("⚠️ Página retorna: Não encontramos imóveis")
elif len(html) > 5000:
    print(f"✓ HTML com {len(html)} caracteres carregado")
    
    # Procurar por padrões
    if "listing" in html.lower():
        print("  ✓ Encontrou 'listing' no HTML")
    if "propriedad" in html.lower():
        print("  ✓ Encontrou 'propriedad' no HTML")
    if "preco" in html.lower():
        print("  ✓ Encontrou 'preco' no HTML")
else:
    print("✗ HTML vazio ou muito pequeno")

driver.quit()
print("\n✓ Navegador fechado - verifique o arquivo imovelweb_debug.html")
