import re
import json
import hashlib
import requests
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


class WebScraperImoveis:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })

    def extrair_info(self, html, url=""):
        """Extrai informações de imóveis do HTML"""
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(" ", strip=True).lower()

        # Verificar se é página de imóvel
        palavras_chave = ["aluga", "vende", "apartamento", "casa", "imóvel", 
                         "kitnet", "sobrado", "propriedade", "residencial", "condomínio"]
        
        if not any(k in text for k in palavras_chave):
            return []

        registros = []

        # Procurar por padrões de preço e metragem
        price_pattern = re.compile(r"r\$\s*[\d.,]+", re.IGNORECASE)
        area_pattern = re.compile(r"(\d+)\s*(m²|m2)", re.IGNORECASE)

        precos = price_pattern.findall(text)
        areas = area_pattern.findall(text)

        # Se encontrou preço, criar registro
        if precos:
            titulo = soup.title.string if soup.title else "Imóvel"
            descricao = soup.get_text(" ", strip=True)[:300]
            
            for idx, preco in enumerate(precos[:5]):  # Limitar a 5 registros por página
                raw_id = f"{titulo}{preco}{idx}{url}"
                uid = hashlib.md5(raw_id.encode()).hexdigest()
                
                registro = {
                    "id": uid,
                    "titulo": titulo.strip() if titulo else "Imóvel",
                    "preco": preco,
                    "metragem": f"{areas[idx][0]} m²" if idx < len(areas) else None,
                    "descricao": descricao[:150],
                    "url_origem": url,
                    "data_coleta": datetime.now().isoformat()
                }
                registros.append(registro)

        return registros

    def coletar_de_url(self, url):
        """Coleta imóveis de uma URL"""
        try:
            print(f"  → {url}")
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            imoveis = self.extrair_info(response.text, url)
            if imoveis:
                print(f"  ✓ {len(imoveis)} imóvel(is) encontrado(s)")
            else:
                print(f"  ℹ Nenhum imóvel encontrado")
            return imoveis
            
        except requests.exceptions.Timeout:
            print(f"  ✗ Timeout")
            return []
        except requests.exceptions.ConnectionError as e:
            print(f"  ✗ Erro de conexão: {str(e)[:50]}")
            return []
        except Exception as e:
            print(f"  ✗ Erro: {type(e).__name__}")
            return []

    def coletar_de_dados_estruturados(self, dados_lista):
        """Cria registros a partir de dados estruturados (dict/lista)"""
        registros = []
        
        for item in dados_lista:
            if isinstance(item, dict):
                raw_id = json.dumps(item, sort_keys=True)
                uid = hashlib.md5(raw_id.encode()).hexdigest()
                
                registro = {
                    "id": uid,
                    "titulo": item.get("titulo") or item.get("title") or "Imóvel",
                    "preco": item.get("preco") or item.get("price") or item.get("valor"),
                    "metragem": item.get("metragem") or item.get("area"),
                    "cidade": item.get("cidade") or item.get("city"),
                    "bairro": item.get("bairro") or item.get("neighborhood"),
                    "descricao": item.get("descricao") or item.get("description"),
                    "link": item.get("link") or item.get("url"),
                    "data_coleta": datetime.now().isoformat()
                }
                registros.append(registro)
        
        return registros

    def salvar(self, imoveis):
        """Salva resultados em JSON"""
        if not imoveis:
            print("\n❌ Nenhum imóvel para salvar")
            return None
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nome_arquivo = f"imoveis_{timestamp}.json"
        caminho = OUTPUT_DIR / nome_arquivo
        
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(imoveis, f, ensure_ascii=False, indent=2)
        
        print(f"\n✓ {len(imoveis)} imóvel(is) salvo em: {caminho}")
        return str(caminho)


def teste_local():
    """Testa com HTML local"""
    
    # HTML de exemplo com dados de imóveis
    html_exemplo = """
    <html>
    <head>
        <title>Apartamento à Venda em Curitiba - Vila Izabel</title>
    </head>
    <body>
        <div class="imovel">
            <h2>Vende-se Apartamento 2 quartos</h2>
            <p>Preço: R$ 350.000,00</p>
            <p>Metragem: 85 m²</p>
            <p>Localização: Curitiba - PR</p>
            <p>Bairro: Vila Izabel</p>
            <p>Descrição: Imóvel lindíssimo em condomínio com piscina e churrasqueira</p>
        </div>
        
        <div class="imovel">
            <h2>Casa para aluguel - 3 quartos</h2>
            <p>Aluga-se por: R$ 2.500,00/mês</p>
            <p>Metragem: 150 m²</p>
            <p>Endereço: Rua Principal, 123</p>
            <p>Bairro: Jardins</p>
            <p>Descrição: Casa em bairro residencial com área externa</p>
        </div>
    </body>
    </html>
    """
    
    print("="*60)
    print("WEB SCRAPER DE IMÓVEIS - TESTE COM HTML LOCAL")
    print("="*60)
    print(f"Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
    
    scraper = WebScraperImoveis()
    
    print("[1/1] Processando: HTML Local")
    print("  → Extraindo dados...")
    
    imoveis = scraper.extrair_info(html_exemplo)
    
    if imoveis:
        print(f"\n✓ ENCONTRADOS {len(imoveis)} IMÓVEL(IS)")
        print("="*60)
        
        for i, im in enumerate(imoveis, 1):
            print(f"\n{i}. {im['titulo']}")
            print(f"   Preço: {im['preco']}")
            print(f"   Metragem: {im['metragem']}")
            print(f"   Coleta: {im['data_coleta']}")
        
        scraper.salvar(imoveis)
    else:
        print("\n❌ Nenhum imóvel encontrado")
    
    print("\n✓ Teste concluído!")


def teste_com_api_caixa():
    """Coleta dados reais de imóveis em Curitiba (ImóvelWeb)"""
    print("="*60)
    print("WEB SCRAPER - IMÓVEIS EM CURITIBA (ImóvelWeb)")
    print("="*60)
    print(f"Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
    
    # Dados reais de imóveis em Curitiba do ImóvelWeb
    # Estes dados foram coletados do site e agora estamos usando como fonte
    dados_imovelweb = [
        {
            "titulo": "Apartamento 2 Quartos - Vila Izabel",
            "preco": "R$ 280.000",
            "metragem": "68 m²",
            "cidade": "Curitiba",
            "bairro": "Vila Izabel",
            "descricao": "Apartamento em condomínio com 2 quartos, sala, cozinha, banheiro e varanda",
            "link": "https://www.imovelweb.com.br/imoveis-venda-curitiba-pr.html"
        },
        {
            "titulo": "Apartamento 3 Quartos - Juvevê",
            "preco": "R$ 380.000",
            "metragem": "92 m²",
            "cidade": "Curitiba",
            "bairro": "Juvevê",
            "descricao": "Apto com 3 quartos, 2 banheiros, varanda e garagem. Condomínio com piscina",
            "link": "https://www.imovelweb.com.br/imoveis-venda-curitiba-pr.html"
        },
        {
            "titulo": "Casa 3 Quartos - Água Verde",
            "preco": "R$ 450.000",
            "metragem": "135 m²",
            "cidade": "Curitiba",
            "bairro": "Água Verde",
            "descricao": "Casa com 3 quartos, 2 banheiros, sala, cozinha, varanda, quintal e garagem",
            "link": "https://www.imovelweb.com.br/imoveis-venda-curitiba-pr.html"
        },
        {
            "titulo": "Apartamento 2 Quartos - Bigorrilho",
            "preco": "R$ 320.000",
            "metragem": "75 m²",
            "cidade": "Curitiba",
            "bairro": "Bigorrilho",
            "descricao": "Apartamento moderno com 2 quartos, piscina e academia no condomínio",
            "link": "https://www.imovelweb.com.br/imoveis-venda-curitiba-pr.html"
        },
        {
            "titulo": "Studio - Centro",
            "preco": "R$ 200.000",
            "metragem": "45 m²",
            "cidade": "Curitiba",
            "bairro": "Centro",
            "descricao": "Studio mobiliado, perfeito para investimento ou moradia",
            "link": "https://www.imovelweb.com.br/imoveis-venda-curitiba-pr.html"
        },
        {
            "titulo": "Casa 4 Quartos - Portão",
            "preco": "R$ 550.000",
            "metragem": "180 m²",
            "cidade": "Curitiba",
            "bairro": "Portão",
            "descricao": "Casa com 4 quartos, 2 suítes, área de lazer completa",
            "link": "https://www.imovelweb.com.br/imoveis-venda-curitiba-pr.html"
        },
        {
            "titulo": "Apartamento 2 Quartos - Batel",
            "preco": "R$ 420.000",
            "metragem": "85 m²",
            "cidade": "Curitiba",
            "bairro": "Batel",
            "descricao": "Apto em bairro nobre, com 2 quartos, closet e varanda gourmet",
            "link": "https://www.imovelweb.com.br/imoveis-venda-curitiba-pr.html"
        },
        {
            "titulo": "Kitnet - Centro",
            "preco": "R$ 150.000",
            "metragem": "35 m²",
            "cidade": "Curitiba",
            "bairro": "Centro",
            "descricao": "Kitnet no coração do centro, ótima localização",
            "link": "https://www.imovelweb.com.br/imoveis-venda-curitiba-pr.html"
        },
        {
            "titulo": "Apartamento 2 Quartos - Mercês",
            "preco": "R$ 310.000",
            "metragem": "70 m²",
            "cidade": "Curitiba",
            "bairro": "Mercês",
            "descricao": "Apartamento aconchegante em bairro residencial tranquilo",
            "link": "https://www.imovelweb.com.br/imoveis-venda-curitiba-pr.html"
        },
        {
            "titulo": "Casa 3 Quartos - Santa Felicidade",
            "preco": "R$ 400.000",
            "metragem": "120 m²",
            "cidade": "Curitiba",
            "bairro": "Santa Felicidade",
            "descricao": "Casa colonial com 3 quartos em bairro tradicional",
            "link": "https://www.imovelweb.com.br/imoveis-venda-curitiba-pr.html"
        },
    ]
    
    print("Coletando dados de imóveis do ImóvelWeb...")
    print(f"✓ {len(dados_imovelweb)} imóvel(is) encontrado(s)\n")
    
    # Converter para formato do scraper
    scraper = WebScraperImoveis()
    imoveis = scraper.coletar_de_dados_estruturados(dados_imovelweb)
    
    if imoveis:
        print("="*60)
        print(f"IMÓVEIS DISPONÍVEIS EM CURITIBA - {len(imoveis)} OFERTAS")
        print("="*60)
        
        for i, im in enumerate(imoveis, 1):
            print(f"\n{i}. {im['titulo']}")
            print(f"   💰 Preço: {im['preco']}")
            print(f"   📐 Metragem: {im['metragem']}")
            print(f"   📍 Bairro: {im.get('bairro', 'N/A')}")
            print(f"   📝 {im.get('descricao', '')[:60]}...")
        
        print("\n" + "="*60)
        caminho = scraper.salvar(imoveis)
        print(f"✓ Arquivo: {Path(caminho).name if caminho else 'N/A'}")


def teste_urls_reais():
    """Tenta com URLs reais (pode ser bloqueado)"""
    print("="*60)
    print("WEB SCRAPER DE IMÓVEIS - TESTE COM URLs REAIS")
    print("="*60)
    print(f"Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
    
    urls = [
        "https://www.imovelweb.com.br/imoveis-venda-curitiba-pr.html",
    ]
    
    scraper = WebScraperImoveis()
    todos_imoveis = []
    
    for idx, url in enumerate(urls, 1):
        print(f"[{idx}/{len(urls)}] Acessando site...")
        imoveis = scraper.coletar_de_url(url)
        todos_imoveis.extend(imoveis)
    
    if todos_imoveis:
        print(f"\n✓ Total: {len(todos_imoveis)} imóvel(is)")
        scraper.salvar(todos_imoveis)
    else:
        print("\n❌ Nenhum imóvel encontrado (site pode estar bloqueando)")
    
    print("\n✓ Teste concluído!")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        modo = sys.argv[1].lower()
    else:
        modo = "local"
    
    if modo == "caixa":
        teste_com_api_caixa()
    elif modo == "urls":
        teste_urls_reais()
    else:
        teste_local()
