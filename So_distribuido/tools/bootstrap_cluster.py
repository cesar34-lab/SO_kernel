# -*- coding: utf-8 -*-
"""
Script de conveniencia para verificar servicios en local.
"""
import requests, time

def ping(url):
    try:
        r = requests.get(url + "/estado", timeout=2)
        return r.status_code, r.json()
    except Exception as e:
        return None, str(e)

def main():
    urls = ["http://localhost:8000","http://localhost:8101","http://localhost:8102"]
    for _ in range(10):
        ok = True
        for u in urls:
            s, j = ping(u)
            print(u, "->", s, j)
            ok = ok and (s == 200)
        if ok:
            print("Cluster OK")
            return
        time.sleep(2)
    print("Cluster no disponible")

if __name__ == "__main__":
    main()
