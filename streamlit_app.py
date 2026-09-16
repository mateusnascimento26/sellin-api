"""
Front-end (Streamlit) do Sellin-API -- painel simples pra fazer login e usar os
3 recursos principais da API sem precisar mexer em código, scripts ou Postman:

- Gerar a apresentação (.pptx) a partir da planilha de sell-in
- Baixar só os gráficos (.zip), sem montar a apresentação inteira
- Importar a planilha pro banco de dados

Como rodar (depois de "pip install streamlit requests" no mesmo ambiente
Python da API):

    streamlit run streamlit_app.py --server.address 0.0.0.0

O "--server.address 0.0.0.0" deixa o painel acessível por qualquer pessoa na
mesma rede, em http://<ip-desta-máquina>:8501 -- a API (FastAPI/uvicorn)
continua rodando só nesta máquina; o painel conversa com ela em segundo plano
(por padrão em http://127.0.0.1:8000, ajustável no campo "Endereço da API" na
barra lateral, se um dia a API rodar em outra máquina).
"""
import os
from datetime import date, timedelta

import requests
import streamlit as st

API_BASE_URL_PADRAO = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")

st.set_page_config(page_title="Sellin-API", page_icon="📊", layout="centered")

# ------------------------------------------------------------------ sessão

if "token" not in st.session_state:
    st.session_state.token = None
if "username" not in st.session_state:
    st.session_state.username = None
if "api_base_url" not in st.session_state:
    st.session_state.api_base_url = API_BASE_URL_PADRAO


def cabecalho_autenticado() -> dict:
    return {"Authorization": f"Bearer {st.session_state.token}"}


def deslogar():
    st.session_state.token = None
    st.session_state.username = None


# ------------------------------------------------------------------ sidebar

with st.sidebar:
    st.text_input(
        "Endereço da API", key="api_base_url",
        help="Onde o back-end (FastAPI) está rodando. Só precisa mudar se a "
             "API não estiver rodando nesta mesma máquina.",
    )
    if st.session_state.token:
        st.success(f"Logado como **{st.session_state.username}**")
        if st.button("Sair"):
            deslogar()
            st.rerun()


# ------------------------------------------------------------------ login

def tela_login():
    st.title("📊 Sellin-API")
    st.caption("Entre com seu usuário e senha para continuar.")
    with st.form("form_login"):
        usuario = st.text_input("Usuário")
        senha = st.text_input("Senha", type="password")
        entrar = st.form_submit_button("Entrar", type="primary")

    if not entrar:
        return
    if not usuario or not senha:
        st.error("Preencha usuário e senha.")
        return

    try:
        resposta = requests.post(
            f"{st.session_state.api_base_url}/login",
            json={"username": usuario, "password": senha}, timeout=15,
        )
    except requests.RequestException as exc:
        st.error(f"Não consegui falar com a API em {st.session_state.api_base_url}. Detalhe: {exc}")
        return

    if resposta.status_code == 200:
        st.session_state.token = resposta.json()["access_token"]
        st.session_state.username = usuario
        st.rerun()
    else:
        try:
            detalhe = resposta.json().get("detail")
        except ValueError:
            detalhe = None
        st.error(detalhe or "Usuário ou senha inválidos.")


if not st.session_state.token:
    tela_login()
    st.stop()


# ------------------------------------------------------------------ util comum

def chamar_api(metodo: str, caminho: str, **kwargs):
    """Faz a chamada autenticada à API e trata token expirado/inválido (401)
    deslogando automaticamente e voltando pra tela de login."""
    try:
        resposta = requests.request(
            metodo, f"{st.session_state.api_base_url}{caminho}",
            headers=cabecalho_autenticado(), timeout=180, **kwargs,
        )
    except requests.RequestException as exc:
        st.error(f"Não consegui falar com a API em {st.session_state.api_base_url}. Detalhe: {exc}")
        return None

    if resposta.status_code == 401:
        st.warning("Sua sessão expirou. Faça login novamente.")
        deslogar()
        st.rerun()
        return None

    return resposta


def mostrar_erro_api(resposta) -> None:
    try:
        detalhe = resposta.json().get("detail")
    except ValueError:
        detalhe = None
    st.error(detalhe or f"A API retornou um erro (status {resposta.status_code}).")


def mostrar_aviso_dimensoes(resposta) -> None:
    aviso = resposta.headers.get("X-Dimensoes-Sem-Tipologia")
    if aviso:
        st.warning(f"Algumas linhas não entraram na análise (dimensão ainda sem tipologia cadastrada): {aviso}")


def arquivo_multipart(arquivo):
    return {"file": (arquivo.name, arquivo.getvalue(),
                      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}


st.title("📊 Sellin-API")
aba_apresentacao, aba_graficos, aba_importar = st.tabs(
    ["🖥️ Gerar apresentação", "📈 Baixar gráficos", "⬆️ Importar pro banco"]
)

# ------------------------------------------------------------------ aba: apresentação

with aba_apresentacao:
    st.subheader("Gerar apresentação (.pptx)")
    st.caption("Monta a apresentação completa (Bloco 1, Bloco 2 e, se preencher o período 2, "
                "também o Bloco 3) a partir da planilha de sell-in.")

    arquivo = st.file_uploader("Planilha (.xlsx)", type=["xlsx"], key="arquivo_apresentacao")

    usar_periodo1 = st.checkbox(
        "Escolher um período específico (em vez de usar todos os dados da planilha)",
        key="usar_periodo1",
    )
    data_inicial = data_final = None
    if usar_periodo1:
        col1, col2 = st.columns(2)
        data_inicial = col1.date_input("Início do período", value=date.today().replace(day=1),
                                        key="data_inicial_1")
        data_final = col2.date_input("Fim do período", value=date.today(), key="data_final_1")

    usar_periodo2 = st.checkbox(
        "Comparar também com um segundo período livre (adiciona o Bloco 3)",
        key="usar_periodo2", disabled=not usar_periodo1,
        help="Só é possível escolher o 2º período depois de escolher o 1º período específico acima.",
    )
    data_inicial_2 = data_final_2 = None
    if usar_periodo2 and usar_periodo1:
        col1, col2 = st.columns(2)
        data_inicial_2 = col1.date_input(
            "Início do período 2", value=date.today().replace(day=1) - timedelta(days=365),
            key="data_inicial_2")
        data_final_2 = col2.date_input(
            "Fim do período 2", value=date.today() - timedelta(days=365), key="data_final_2")

    if st.button("Gerar apresentação", type="primary", disabled=arquivo is None,
                  key="botao_apresentacao"):
        params = {}
        if usar_periodo1:
            params["data_inicial"] = data_inicial.isoformat()
            params["data_final"] = data_final.isoformat()
            if usar_periodo2:
                params["data_inicial_2"] = data_inicial_2.isoformat()
                params["data_final_2"] = data_final_2.isoformat()

        with st.spinner("Gerando apresentação... pode levar alguns segundos."):
            resposta = chamar_api("GET", "/apresentacao", params=params, files=arquivo_multipart(arquivo))

        # Guarda o resultado no session_state (em vez de só numa variável local):
        # clicar no botão de download logo abaixo dispara um novo rerun do script,
        # e sem isso o resultado "sumiria" da tela nesse rerun (o clique no botão
        # "Gerar apresentação" só é True no proprio run em que foi clicado).
        if resposta is not None and resposta.status_code == 200:
            st.session_state["resultado_apresentacao"] = resposta.content
            st.session_state["aviso_apresentacao"] = resposta.headers.get("X-Dimensoes-Sem-Tipologia")
            st.session_state["erro_apresentacao"] = None
        elif resposta is not None:
            st.session_state["resultado_apresentacao"] = None
            st.session_state["erro_apresentacao"] = resposta

    if st.session_state.get("erro_apresentacao") is not None:
        mostrar_erro_api(st.session_state["erro_apresentacao"])
    if st.session_state.get("resultado_apresentacao") is not None:
        if st.session_state.get("aviso_apresentacao"):
            st.warning("Algumas linhas não entraram na análise (dimensão ainda sem tipologia cadastrada): "
                       f"{st.session_state['aviso_apresentacao']}")
        st.success("Apresentação gerada com sucesso!")
        st.download_button(
            "⬇️ Baixar apresentação (.pptx)", data=st.session_state["resultado_apresentacao"],
            file_name="apresentacao_sellin.pptx",
            mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            key="download_apresentacao",
        )

# ------------------------------------------------------------------ aba: gráficos

with aba_graficos:
    st.subheader("Baixar gráficos avulsos (.zip)")
    st.caption("Gera só as imagens dos gráficos (sem montar a apresentação inteira), "
                "considerando todos os dados da planilha.")

    arquivo_g = st.file_uploader("Planilha (.xlsx)", type=["xlsx"], key="arquivo_graficos")

    if st.button("Gerar gráficos", type="primary", disabled=arquivo_g is None, key="botao_graficos"):
        with st.spinner("Gerando gráficos..."):
            resposta = chamar_api("POST", "/graficos", files=arquivo_multipart(arquivo_g))

        if resposta is not None and resposta.status_code == 200:
            st.session_state["resultado_graficos"] = resposta.content
            st.session_state["aviso_graficos"] = resposta.headers.get("X-Dimensoes-Sem-Tipologia")
            st.session_state["erro_graficos"] = None
        elif resposta is not None:
            st.session_state["resultado_graficos"] = None
            st.session_state["erro_graficos"] = resposta

    if st.session_state.get("erro_graficos") is not None:
        mostrar_erro_api(st.session_state["erro_graficos"])
    if st.session_state.get("resultado_graficos") is not None:
        if st.session_state.get("aviso_graficos"):
            st.warning("Algumas linhas não entraram na análise (dimensão ainda sem tipologia cadastrada): "
                       f"{st.session_state['aviso_graficos']}")
        st.success("Gráficos gerados com sucesso!")
        st.download_button("⬇️ Baixar gráficos (.zip)", data=st.session_state["resultado_graficos"],
                            file_name="graficos_sellin.zip", mime="application/zip", key="download_graficos")

# ------------------------------------------------------------------ aba: importar

with aba_importar:
    st.subheader("Importar planilha para o banco de dados")
    st.caption("Salva os dados da planilha no banco -- use com cuidado, isso persiste os registros.")

    arquivo_i = st.file_uploader("Planilha (.xlsx)", type=["xlsx"], key="arquivo_importar")

    if st.button("Importar", type="primary", disabled=arquivo_i is None, key="botao_importar"):
        with st.spinner("Importando..."):
            resposta = chamar_api("POST", "/upload", files=arquivo_multipart(arquivo_i))

        if resposta is not None and resposta.status_code == 200:
            st.session_state["resultado_importar"] = resposta.json()
            st.session_state["erro_importar"] = None
        elif resposta is not None:
            st.session_state["resultado_importar"] = None
            st.session_state["erro_importar"] = resposta

    if st.session_state.get("erro_importar") is not None:
        mostrar_erro_api(st.session_state["erro_importar"])
    dados = st.session_state.get("resultado_importar")
    if dados is not None:
        if dados["ok"]:
            st.success(dados["message"])
        else:
            st.warning(dados["message"])

        col1, col2, col3 = st.columns(3)
        col1.metric("Linhas na planilha", dados.get("total_rows", 0))
        col2.metric("Linhas importadas", dados.get("persisted_rows", 0))
        col3.metric("Linhas com erro", dados.get("total_errors", 0))

        if dados.get("errors"):
            with st.expander(f"Ver erros ({len(dados['errors'])})"):
                st.write(dados["errors"])
        if dados.get("skipped_rows"):
            with st.expander(f"Ver linhas ignoradas ({len(dados['skipped_rows'])})"):
                st.write(dados["skipped_rows"])
