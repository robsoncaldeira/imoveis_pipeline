import re
import json
import hashlib
import requests
from pathlib import Path
from datetime import datetime
from urllib.parse import urljoin
from bs4 import BeautifulSoup

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


class WebScraperImoveis:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        })

    def extrair_info(self, html, url):
        """Extrai informações de imóveis do HTML"""
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(" ", strip=True).lower()

        # Verificar se é página de imóvel
        palavras_chave = ["aluga", "vende", "apartamento", "casa", "imóvel", 
                         "kitnet", "sobrado", "propriedade", "residencial"]
        
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
            
            # Gerar ID único
            raw = f"{titulo}{precos[0]}{url}"
            uid = hashlib.md5(raw.encode()).hexdigest()

            registro = {
                "id": uid,
                "titulo": titulo.strip() if titulo else "Imóvel",
                "preco": precos[0] if precos else None,
                "metragem": f"{areas[0][0]} m²" if areas else None,
                "descricao": descricao,
                "link": url,
                "data_coleta": datetime.now().isoformat()
            }
            registros.append(registro)

        return registros

    def coletar(self, url):
        """Coleta imóveis de uma URL"""
        try:
            print(f"  → Acessando: {url}")
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            imoveis = self.extrair_info(response.text, url)
            if imoveis:
                print(f"  ✓ {len(imoveis)} imóvel(is) encontrado(s)")
            return imoveis
            
        except requests.exceptions.Timeout:
            print(f"  ✗ Timeout ao acessar {url}")
            return []
        except requests.exceptions.ConnectionError:
            print(f"  ✗ Erro de conexão: {url}")
            return []
        except Exception as e:
            print(f"  ✗ Erro: {str(e)[:80]}")
            return []

    def coletar_varios(self, urls):
        """Coleta de múltiplas URLs"""
        todos_imoveis = []
        
        for idx, url in enumerate(urls, 1):
            print(f"\n[{idx}/{len(urls)}] Processando: {url}")
            imoveis = self.coletar(url)
            todos_imoveis.extend(imoveis)
        
        return todos_imoveis

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

    def close(self):
        """Fecha a sessão"""
        if self.session:
            self.session.close()


def teste_com_dados_reais():
    """Testa com URLs reais de imóveis"""
    
    # Lista de URLs reais que vendem imóveis
    urls = [
        # Você pode adicionar URLs reais aqui
        # Por enquanto, vamos testar com um site que tem conteúdo de imóveis
        "https://www.imovirtual.com.br/",
    ]
    
    print("="*60)
    print("WEB SCRAPER DE IMÓVEIS - TESTE COM DADOS REAIS")
    print("="*60)
    print(f"Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
    
    scraper = WebScraperImoveis()
    
    try:
        imoveis = scraper.coletar_varios(urls)
        
        if imoveis:
            print("\n" + "="*60)
            print(f"ENCONTRADOS {len(imoveis)} IMÓVEL(IS)")
            print("="*60)
            
            for i, im in enumerate(imoveis, 1):
                print(f"\n{i}. {im['titulo']}")
                print(f"   ID: {im['id']}")
                print(f"   Preço: {im['preco']}")
                print(f"   Metragem: {im['metragem']}")
                print(f"   Link: {im['link']}")
            
            scraper.salvar(imoveis)
        else:
            print("\n❌ Nenhum imóvel encontrado")
            print("\n💡 Dicas:")
            print("   • Adicione URLs reais de sites de imóveis")
            print("   • Ajuste os padrões de busca se necessário")
            print("   • Verifique se as URLs têm conteúdo de imóveis")
    
    except KeyboardInterrupt:
        print("\n\n⏹️ Execução cancelada")
    except Exception as e:
        print(f"\n❌ Erro: {type(e).__name__} - {str(e)[:100]}")
    
    finally:
        scraper.close()
        print("\n✓ Encerrando...")


if __name__ == "__main__":
    teste_com_dados_reais()
