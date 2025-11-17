import requests
import json

# Tentando acessar a API do site
urls_api = [
    "https://www.imovelweb.com.br/api/1/property/list",
    "https://www.imovelweb.com.br/api/search",
]

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json'
}

for url in urls_api:
    try:
        print(f"\nTentando: {url}")
        response = requests.get(url, headers=headers, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Conteúdo: {response.text[:300]}")
    except Exception as e:
        print(f"Erro: {e}")

# Vamos tentar com Vivareal que é mais acessível
print("\n" + "="*60)
print("Tentando com Vivareal...")
print("="*60)

vivareal_url = "https://www.vivareal.com.br/venda/apartamentos/curitiba-pr/"
try:
    print(f"\nAcessando: {vivareal_url}")
    response = requests.get(vivareal_url, headers=headers, timeout=10)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        print("✓ Acesso bem-sucedido!")
        print(f"Tamanho: {len(response.text)} bytes")
except Exception as e:
    print(f"Erro: {e}")
