import socket
import requests

print("Testando conectividade...\n")

# Teste 1: Socket (Google DNS)
try:
    socket.create_connection(("8.8.8.8", 53), timeout=3)
    print("✓ Socket: OK")
except:
    print("✗ Socket: FALHOU")

# Teste 2: Requests HTTP
try:
    r = requests.get("https://www.google.com", timeout=5)
    print(f"✓ HTTP: OK (Status {r.status_code})")
except Exception as e:
    print(f"✗ HTTP: FALHOU ({str(e)[:50]})")

# Teste 3: Playwright
try:
    from playwright.sync_api import sync_playwright
    print("Testando Playwright...")
    p = sync_playwright().start()
    b = p.chromium.launch()
    page = b.new_page()
    page.goto("https://www.google.com", timeout=10000)
    print("✓ Playwright: OK")
    b.close()
    p.stop()
except Exception as e:
    print(f"✗ Playwright: FALHOU ({str(e)[:80]})")
