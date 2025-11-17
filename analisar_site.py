import requests
from bs4 import BeautifulSoup

url = 'https://www.imovelweb.com.br/imoveis-venda-curitiba-pr.html'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

try:
    print("Conectando ao site...")
    response = requests.get(url, headers=headers, timeout=15)
    print(f'✓ Status: {response.status_code}')
    print(f'✓ Tamanho: {len(response.text)} bytes')
    
    soup = BeautifulSoup(response.text, 'html.parser')
    print(f'✓ Title: {soup.title.string if soup.title else "Não encontrado"}')
    
    # Procurar por seletores comuns
    print("\nProcurando por classes/IDs comuns...")
    
    # Tentar encontrar cards/listagens
    for selector in ['article', 'li[data-listing]', 'div[data-id]', '.card', '.listing', '.item']:
        found = soup.select(selector)
        if found:
            print(f"  ✓ {selector}: {len(found)} elementos")
    
    # Salvar HTML para análise
    with open('debug_imovelweb.html', 'w', encoding='utf-8') as f:
        f.write(response.text[:5000])
    
    print("\n✓ HTML salvo em debug_imovelweb.html (primeiros 5000 chars)")
    
except Exception as e:
    print(f'✗ Erro: {type(e).__name__} - {e}')
