"""
scanner.py (versão celular)
---------------------------
Acessa o link da nota fiscal (NFC-e) e tenta extrair mercado e produtos/preços.
Se não reconhecer o formato da página, devolve lista vazia (o app deixa você
preencher na mão). Nunca trava o app.
"""

import re
import requests
from bs4 import BeautifulSoup

CABECALHOS = {"User-Agent": "Mozilla/5.0 (Linux; Android 12) AppleWebKit/537.36 Chrome/120 Mobile Safari/537.36"}


def extrair_dados_da_nota(url_nota):
    resultado = {"mercado": None, "itens": []}

    try:
        resposta = requests.get(url_nota, headers=CABECALHOS, timeout=15)
        resposta.raise_for_status()
    except Exception:
        return resultado

    soup = BeautifulSoup(resposta.text, "html.parser")

    candidato_nome = soup.find(["h1", "h2"])
    if candidato_nome:
        resultado["mercado"] = candidato_nome.get_text(strip=True)

    padrao_preco = re.compile(r"(\d{1,3}(?:\.\d{3})*,\d{2})")

    for linha in soup.find_all("tr"):
        texto_linha = linha.get_text(" ", strip=True)
        precos = padrao_preco.findall(texto_linha)
        if not precos:
            continue

        primeiro_preco = precos[0]
        nome_produto = texto_linha.split(primeiro_preco)[0].strip(" -:")
        if not nome_produto or len(nome_produto) < 2:
            continue

        try:
            preco_float = float(primeiro_preco.replace(".", "").replace(",", "."))
        except ValueError:
            continue

        resultado["itens"].append(
            {"produto": nome_produto, "preco": preco_float, "quantidade": 1}
        )

    return resultado
