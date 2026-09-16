"""
Script pra testar o endpoint GET /apresentacao. A apresentacao gerada sempre traz
2 blocos fixos:
- Bloco 1: so o periodo 1 (principal), sem nenhuma comparacao.
- Bloco 2: o periodo 1 comparado com o mesmo periodo do ano anterior (calculado
  automaticamente pela API -- voce so informa o periodo 1).

Se voce tambem informar um PERIODO 2 (livre, pode ter duracao diferente do
periodo 1), um 3o bloco e adicionado comparando periodo 1 x periodo 2 em cima
de totais (nao mes a mes).

Como usar:
1. Suba a API (uvicorn main:app --reload)
2. Preencha USERNAME, SENHA e CAMINHO_ARQUIVO abaixo
3. Rode:
   python testar_apresentacao.py
   python testar_apresentacao.py 2026-01-01 2026-03-01
   python testar_apresentacao.py 2026-01-01 2026-03-01 2025-03-01 2025-07-01
   (o 3o e 4o argumento sao opcionais -- so entram se voce quiser o 3o bloco)

Atencao ao formato da data: tem que ser AAAA-MM-DD (padrao ISO), nao DD/MM/AAAA.
O periodo 1 pode cruzar a virada do ano (ex: Out/2025 a Fev/2026), mas nao pode
ultrapassar 12 meses no total. O periodo 2 nao tem essa restricao de tamanho
(pode ter qualquer duracao e tambem pode cruzar anos).

Por que via script e nao pelo /docs? Porque o navegador bloqueia envio de
corpo (o arquivo) em requisicoes GET -- e uma regra do proprio navegador,
nao da nossa API. A biblioteca "requests" nao tem essa restricao, entao
funciona normalmente.
"""
import sys

import requests

BASE_URL = "http://127.0.0.1:8000"
USERNAME = "felipe"
SENHA = "123456789"
CAMINHO_ARQUIVO = r"C:\Users\mateu\Desktop\Teste.xlsx"

if len(sys.argv) > 2:
    data_inicial, data_final = sys.argv[1], sys.argv[2]
else:
    data_inicial, data_final = "2026-01-01", "2026-06-01"

data_inicial_2, data_final_2 = None, None
if len(sys.argv) > 4:
    data_inicial_2, data_final_2 = sys.argv[3], sys.argv[4]

# 1) login para pegar o token
resposta_login = requests.post(f"{BASE_URL}/login", json={"username": USERNAME, "password": SENHA})
resposta_login.raise_for_status()
token = resposta_login.json()["access_token"]
print("Login ok, token obtido.")

# 2) chama o /apresentacao em GET, passando o(s) periodo(s) como query params
params = {"data_inicial": data_inicial, "data_final": data_final}
if data_inicial_2 and data_final_2:
    params["data_inicial_2"] = data_inicial_2
    params["data_final_2"] = data_final_2

with open(CAMINHO_ARQUIVO, "rb") as arquivo:
    resposta = requests.get(
        f"{BASE_URL}/apresentacao",
        params=params,
        headers={"Authorization": f"Bearer {token}"},
        files={"file": (CAMINHO_ARQUIVO.split("\\")[-1], arquivo,
                         "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )

print("Status:", resposta.status_code)

if resposta.status_code != 200:
    print("Erro:", resposta.text)
else:
    sufixo_periodo2 = f"_vs_{data_inicial_2}_a_{data_final_2}" if data_inicial_2 else ""
    nome_saida = f"apresentacao_{data_inicial}_a_{data_final}{sufixo_periodo2}.pptx"
    with open(nome_saida, "wb") as saida:
        saida.write(resposta.content)
    print(f"Apresentacao salva em: {nome_saida}")
    if "X-Dimensoes-Sem-Tipologia" in resposta.headers:
        print("Aviso:", resposta.headers["X-Dimensoes-Sem-Tipologia"])
