import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output", "caixa")
os.makedirs(OUTPUT_DIR, exist_ok=True)

URL_FORM = "https://venda-imoveis.caixa.gov.br/sistema/busca-imovel.asp?sltTipoBusca=imoveis"
URL_POST = "https://venda-imoveis.caixa.gov.br/sistema/resultadoBuscaImovel.asp"

def coletar_imoveis(estado="PR"):
    session = requests.Session()

    # 1. Abrir página inicial e gerar cookies
    resposta_inicial = session.get(URL_FORM, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(resposta_inicial.text, "html.parser")

    # 2. Capturar todos os campos hidden gerados dinamicamente
    hidden_fields = {}
    for hidden in soup.find_all("input", type="hidden"):
        hidden_fields[hidden.get("name")] = hidden.get("value", "")

    # 3. Montar payload completo do formulário
    payload = {
        **hidden_fields,
        "sltTipoBusca": "imoveis",
        "sltEstado": estado,
        "sltCidade": "TODAS",
        "sltFaixaValor": "0",
        "sltTipoImovel": "0",
        "nCdCliente": "",
        "nCdImovel": "",
        "nCdSegmento": "",
        "nCdAssunto": ""
    }

    # 4. Submeter POST autenticado na sessão
    resposta = session.post(
        URL_POST,
        data=payload,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    soup = BeautifulSoup(resposta.text, "html.parser")

    cards = soup.select(".card-imovel")

    registros = []

    for card in cards:
        try:
            titulo = card.select_one(".titulo-imovel").get_text(strip=True)
            endereco = card.select_one(".end-imovel").get_text(strip=True)
            cidade = card.select_one(".cidade-imovel").get_text(strip=True)
            valor = card.select_one(".valor-imovel").get_text(strip=True)
            link = card.select_one("a").get("href")

            registros.append({
                "titulo": titulo,
                "endereco": endereco,
                "cidade": cidade,
                "valor": valor,
                "link": f"https://venda-imoveis.caixa.gov.br/sistema/{link}",
                "fonte": "Caixa",
                "data_coleta": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
        except:
            pass

    nome_json = f"caixa_{estado}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    caminho_json = os.path.join(OUTPUT_DIR, nome_json)

    with open(caminho_json, "w", encoding="utf-8") as f:
        json.dump(registros, f, indent=4, ensure_ascii=False)

    print(f"Total coletado: {len(registros)}")
    print(f"Arquivo salvo: {caminho_json}")

    return caminho_json


if __name__ == "__main__":
    coletar_imoveis("PR")
