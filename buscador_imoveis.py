import re
import json
import hashlib
import requests
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


class BuscadorImoveis:
    """Busca imóveis na internet usando palavras-chave"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })

    def buscar_google(self, palavras_chave, limite=10):
        """Busca imóveis no Google usando palavras-chave"""
        print(f"\n🔍 Buscando: '{palavras_chave}' no Google...")
        
        # URL de busca do Google
        query = f"{palavras_chave} imóvel venda"
        url_search = f"https://www.google.com/search?q={quote(query)}"
        
        try:
            response = self.session.get(url_search, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Extrair links de busca
            links = []
            for link_elem in soup.find_all("a", href=True):
                href = link_elem.get("href", "")
                if "url?q=" in href and "webcache" not in href:
                    # Extrair URL real do link do Google
                    url_real = href.split("url?q=")[1].split("&")[0]
                    links.append(url_real)
            
            print(f"  ✓ {len(links)} links encontrados")
            return links[:limite]
            
        except Exception as e:
            print(f"  ✗ Erro: {str(e)[:50]}")
            return []

    def buscar_imovirtual(self, cidade, bairro="", preco_min=0, preco_max=999999):
        """Busca na ImóvelVirtual"""
        print(f"\n🏠 Buscando em ImóvelVirtual: {cidade}")
        
        url = f"https://www.imovirtual.com.br/venda/apartamentos/{cidade.lower().replace(' ', '-')}-pr/"
        
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            imoveis = self._extrair_imoveis_imovirtual(soup, url)
            
            print(f"  ✓ {len(imoveis)} imóvel(is) encontrado(s)")
            return imoveis
            
        except Exception as e:
            print(f"  ✗ Erro: {str(e)[:50]}")
            return []

    def _extrair_imoveis_imovirtual(self, soup, url_base):
        """Extrai imóveis da ImóvelVirtual"""
        imoveis = []
        
        # Procurar por cards de imóvel
        for article in soup.find_all("article", limit=10):
            try:
                # Título
                titulo_elem = article.find("a", {"class": "css-1jv9qum"})
                titulo = titulo_elem.get_text(strip=True) if titulo_elem else None
                
                if not titulo:
                    continue
                
                # Preço
                preco_elem = article.find("span", {"data-qa": "price"})
                preco = preco_elem.get_text(strip=True) if preco_elem else None
                
                # Link
                link_elem = article.find("a", href=True)
                link = urljoin(url_base, link_elem["href"]) if link_elem else None
                
                # Metragem e outros dados
                texto = article.get_text(" ", strip=True).lower()
                
                metragem = None
                match_area = re.search(r"(\d+)\s*m²", texto)
                if match_area:
                    metragem = f"{match_area.group(1)} m²"
                
                if titulo and preco:
                    uid = hashlib.md5(f"{titulo}{preco}".encode()).hexdigest()
                    imovel = {
                        "id": uid,
                        "titulo": titulo,
                        "preco": preco,
                        "metragem": metragem,
                        "link": link,
                        "fonte": "ImóvelVirtual",
                        "data_coleta": datetime.now().isoformat()
                    }
                    imoveis.append(imovel)
            except:
                continue
        
        return imoveis

    def buscar_vivareal(self, cidade):
        """Busca na VivaReal"""
        print(f"\n🏘️ Buscando em VivaReal: {cidade}")
        
        url = f"https://www.vivareal.com.br/venda/apartamentos/{cidade.lower().replace(' ', '-')}-pr/"
        
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            imoveis = self._extrair_imoveis_vivareal(soup, url)
            
            print(f"  ✓ {len(imoveis)} imóvel(is) encontrado(s)")
            return imoveis
            
        except Exception as e:
            print(f"  ✗ Erro: {str(e)[:50]}")
            return []

    def _extrair_imoveis_vivareal(self, soup, url_base):
        """Extrai imóveis da VivaReal"""
        imoveis = []
        
        for article in soup.find_all("a", {"data-testid": "card-property"}, limit=10):
            try:
                # Título
                titulo_elem = article.find("div", {"class": re.compile(".*title.*")})
                titulo = titulo_elem.get_text(strip=True) if titulo_elem else None
                
                # Preço
                preco_elem = article.find("span", {"class": re.compile(".*price.*")})
                preco = preco_elem.get_text(strip=True) if preco_elem else None
                
                # Link
                link = urljoin(url_base, article.get("href", ""))
                
                # Metragem
                texto = article.get_text(" ", strip=True).lower()
                metragem = None
                match_area = re.search(r"(\d+)\s*m²", texto)
                if match_area:
                    metragem = f"{match_area.group(1)} m²"
                
                if titulo and preco:
                    uid = hashlib.md5(f"{titulo}{preco}".encode()).hexdigest()
                    imovel = {
                        "id": uid,
                        "titulo": titulo,
                        "preco": preco,
                        "metragem": metragem,
                        "link": link,
                        "fonte": "VivaReal",
                        "data_coleta": datetime.now().isoformat()
                    }
                    imoveis.append(imovel)
            except:
                continue
        
        return imoveis

    def salvar(self, imoveis, nome_arquivo=""):
        """Salva resultados em JSON"""
        if not imoveis:
            print("\n❌ Nenhum imóvel para salvar")
            return None
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if not nome_arquivo:
            nome_arquivo = f"imoveis_buscados_{timestamp}.json"
        
        caminho = OUTPUT_DIR / nome_arquivo
        
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(imoveis, f, ensure_ascii=False, indent=2)
        
        print(f"\n✓ {len(imoveis)} imóvel(is) salvo em: {caminho}")
        return str(caminho)


def main():
    print("="*70)
    print("BUSCADOR DE IMÓVEIS NA INTERNET")
    print("="*70)
    print(f"Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
    
    buscador = BuscadorImoveis()
    todos_imoveis = []
    
    try:
        # Buscar por cidades e palavras-chave
        cidades = ["curitiba", "sao paulo", "belo horizonte"]
        
        for cidade in cidades:
            print(f"\n{'='*70}")
            print(f"Buscando em: {cidade.upper()}")
            print(f"{'='*70}")
            
            # Tentar múltiplas fontes
            imoveis_vivareal = buscador.buscar_vivareal(cidade)
            todos_imoveis.extend(imoveis_vivareal)
            
            imoveis_imovirtual = buscador.buscar_imovirtual(cidade)
            todos_imoveis.extend(imoveis_imovirtual)
        
        # Remover duplicatas
        vistos = set()
        imoveis_unicos = []
        for im in todos_imoveis:
            if im["id"] not in vistos:
                vistos.add(im["id"])
                imoveis_unicos.append(im)
        
        print(f"\n{'='*70}")
        print(f"RESUMO DA BUSCA")
        print(f"{'='*70}")
        
        if imoveis_unicos:
            print(f"\n✓ Total de imóveis encontrados: {len(imoveis_unicos)}")
            print(f"\nÚltimos 5 imóveis encontrados:")
            
            for i, im in enumerate(imoveis_unicos[-5:], 1):
                print(f"\n{i}. {im['titulo']}")
                print(f"   💰 {im['preco']}")
                print(f"   📐 {im.get('metragem', 'N/A')}")
                print(f"   🌐 {im['fonte']}")
            
            buscador.salvar(imoveis_unicos)
        else:
            print("\n❌ Nenhum imóvel encontrado")
            print("\n💡 Dicas:")
            print("   • Verifique sua conexão de internet")
            print("   • Os sites podem estar bloqueando scraping")
            print("   • Tente acessar manualmente os sites")
    
    except KeyboardInterrupt:
        print("\n\n⏹️ Busca cancelada")
    except Exception as e:
        print(f"\n❌ Erro: {type(e).__name__} - {str(e)[:100]}")


if __name__ == "__main__":
    main()
