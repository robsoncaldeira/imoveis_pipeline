#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de teste rápido da URL extraction corrigida
"""

import re
from urllib.parse import urlparse, parse_qs, unquote

# Testa a função de extração de URL real do Bing
def extract_real_url_from_bing_redirect(href):
    """
    Tenta extrair a URL real de um redirecionamento do Bing.
    """
    try:
        if 'bing.com' not in href:
            return href
        
        parsed = urlparse(href)
        params = parse_qs(parsed.query)
        
        # Tentar parâmetro 'u' (ck/a) - pode estar codificado
        if 'u' in params:
            real_url = params['u'][0]
            # Remover prefixo 'a1' ou 'a2' (encoding indicator)
            if real_url.startswith('a'):
                real_url = real_url[2:]
            # Decodificar URL-encoded
            real_url = unquote(real_url)
            if real_url.startswith('http'):
                return real_url
        
        # Tentar parâmetro 'ref' (rdr.asp) - geralmente já decodificado
        if 'ref' in params:
            real_url = params['ref'][0]
            # Decodificar se necessário
            real_url = unquote(real_url)
            if real_url.startswith('http'):
                return real_url
        
        return None
    except:
        return None


# Testes
test_urls = [
    # Bing ck/a redirect
    "https://www.bing.com/ck/a?!&&p=0e8fbcbd7d09d4c0JmRtPQoxMzMyJmU9dGFibCZudGI9MQ&u=a1https3A%2F%2Fwww.vivareal.com.br%2Fvenda%2Fapartamento%2Fparana%2Fcuritiba%2F&ntb=1",
    # Bing rdr.asp redirect
    "https://www.bing.com/rdr.asp?ref=https%3A%2F%2Fwww.imovelweb.com.br%2Fvenda-apartamento-curitiba%2F",
    # URL direto do domínio alvo
    "https://www.vivareal.com.br/venda/apartamento/parana/curitiba/123456789",
    # URL que não é do domínio alvo
    "https://www.google.com/search?q=imovel",
    # URL anormalmente formatada
    "https://www.bing.com/search?q=site%3Avivareal.com.br%20apartamento&qs=n",
]

print("=" * 80)
print("TESTE DE EXTRAÇÃO DE URL DO BING")
print("=" * 80)

for i, test_url in enumerate(test_urls, 1):
    result = extract_real_url_from_bing_redirect(test_url)
    print(f"\n[Teste {i}]")
    print(f"Input:  {test_url[:80]}...")
    print(f"Output: {result[:80] if result else 'None'}...")
    
    # Verificação
    if 'bing.com' in test_url and 'u=' in test_url:
        expected = 'vivareal.com.br' in (result or '')
        status = '✓ CORRETO' if expected else '✗ FALHOU'
        print(f"Status: {status}")
    elif 'bing.com' in test_url and 'ref=' in test_url:
        expected = 'imovelweb.com.br' in (result or '')
        status = '✓ CORRETO' if expected else '✗ FALHOU'
        print(f"Status: {status}")

print("\n" + "=" * 80)
print("Teste de extração finalizado!")
print("=" * 80)
