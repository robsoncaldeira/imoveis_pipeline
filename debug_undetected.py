import time
import undetected_chromedriver as uc

print("Acessando ImóvelWeb com undetected-chromedriver...")
options = uc.ChromeOptions()
driver = uc.Chrome(options=options, version_main=None)

driver.get("https://www.imovelweb.com.br/venda/apartamentos/curitiba-pr")

print("Aguardando carregamento...")
time.sleep(8)

# Scroll
for i in range(2):
    driver.execute_script("window.scrollBy(0, window.innerHeight);")
    time.sleep(2)

html = driver.page_source

# Salvar HTML
with open("imovelweb_undetected.html", "w", encoding="utf-8") as f:
    f.write(html)

print(f"✓ HTML salvo ({len(html)} bytes)")

# Análise
if "Não encontramos" in html:
    print("⚠️ Não encontramos imóveis")
elif "preco" in html.lower() or "price" in html.lower():
    print("✓ Página tem preços")
    
    # Procurar por padrões
    import re
    precos = re.findall(r"R\$\s*[\d.,]+", html)
    print(f"✓ Encontrou {len(precos)} preços")
    
    if precos:
        print(f"  Exemplos: {precos[:3]}")

driver.quit()
