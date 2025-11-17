#!/usr/bin/env python3
import undetected_chromedriver as uc
import sys

try:
    print("Iniciando Chrome...")
    driver = uc.Chrome()
    print("✅ Chrome iniciado com sucesso")
    driver.quit()
    sys.exit(0)
except Exception as e:
    print(f"❌ Erro: {e}")
    sys.exit(1)
