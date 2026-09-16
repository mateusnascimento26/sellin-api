import io
from decimal import Decimal

import matplotlib
matplotlib.use("Agg")
import matplotlib.colors as mcolors
import matplotlib.patheffects as patheffects
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

from domain.value_objects.sell_in_aggregation import (
    FORMATOS_POR_TIPOLOGIA, MESES_NOMES, OutroPeriodoTotais, ResumoSellIn,
)

COR_TIPOLOGIA = {
    "Cerâmica": "#4E9F63",
    "Porcelanato": "#E0793E",
    "Super Prime": "#7B5EA7",
}
COR_ANO_ANTERIOR = "#B0B7C6"
COR_ANO_ATUAL = "#1F4E79"
COR_OUTRO_PERIODO = "#D9A441"

# Paleta de cores bem distintas entre si (nao tons de uma mesma cor), usada no
# estudo de formatos dentro de uma tipologia -- com ate 9 formatos numa unica
# tipologia (ex: Porcelanato), tons de uma so cor ficavam parecidos demais e
# confundiam a leitura do grafico. Uma cor por formato, na ordem em que aparecem
# em FORMATOS_POR_TIPOLOGIA.
PALETA_FORMATOS_DISTINTA = [
    "#1F4E79", "#E0793E", "#4E9F63", "#7B5EA7", "#C0392B",
    "#1F9E9E", "#D9A441", "#8C6E4A", "#5D6D7E",
]


class MatplotlibChartGenerator:
    def gerar_graficos(self, resumo: ResumoSellIn) -> dict[str, bytes]:
        plt.rcParams["font.family"] = "sans-serif"
        plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial"]

        return {
            "evolucao_mensal.png": self._evolucao_mensal(resumo),
            "representatividade.png": self._representatividade(resumo),
            "tipologia_mensal.png": self._tipologia_mensal(resumo),
        }

    def _salvar(self, fig, transparente: bool = False) -> bytes:
        buffer = io.BytesIO()
        # bbox_inches="tight" corta o espaco em branco sobrando ao redor do conteudo
        # real do grafico (ex: a margem vazia acima da legenda) -- sem isso, o slide
        # acaba com um vao grande entre o titulo (que fica por conta do proprio slide)
        # e onde o grafico realmente comeca a aparecer.
        fig.savefig(buffer, format="png", dpi=300, transparent=transparente,
                    bbox_inches="tight", pad_inches=0.08)
        plt.close(fig)
        return buffer.getvalue()

    def _fmt_faturamento_dinamico(self, valor_mil: float) -> str:
        """Formata um valor de faturamento recebido em R$ mil, escolhendo a unidade
        mais legivel ponto a ponto: 'mi' (milhoes) quando o valor bate R$ 1 milhao
        ou mais, senao usa 'K' (milhares). Isso evita rotulos como '8818' quando o
        numero ja e' grande o bastante pra virar '8,82 mi'."""
        if abs(valor_mil) >= 1000:
            texto = f"{valor_mil / 1000:,.0f}".replace(",", "§").replace(".", ",").replace("§", ".")
            return f"{texto} mi"
        texto = f"{valor_mil:,.0f}".replace(",", "§").replace(".", ",").replace("§", ".")
        return f"{texto}K"

    def _labels_mes(self, meses: list[int], chaves_reais: list[tuple[int, int]]) -> list[str]:
        """Rotulos do eixo X, mes a mes. Quando o periodo cruza a virada do ano, o mes
        sozinho ('Jan') fica ambiguo -- nesse caso acrescenta o ano abreviado ('Jan/26').
        Quando o periodo cabe num unico ano civil, mantem so o nome do mes, como sempre foi."""
        if len({ano for ano, _ in chaves_reais}) <= 1:
            return [MESES_NOMES[m - 1] for m in meses]
        return [f"{MESES_NOMES[mes - 1]}/{str(ano)[2:]}" for ano, mes in chaves_reais]

    def _cor_texto_sobre_fundo(self, cor) -> str:
        """Escolhe branco ou cinza bem escuro pro texto que vai ficar por cima da cor
        de fundo informada (hex ou tupla RGB 0-1), com base em quao clara/escura ela
        e' (luminancia relativa) -- garante contraste legivel dentro de qualquer barra,
        nao importa a cor."""
        r, g, b = mcolors.to_rgb(cor)
        luminancia = 0.299 * r + 0.587 * g + 0.114 * b
        return "#1F2A37" if luminancia > 0.6 else "white"

    def _blend_com_branco(self, cor_hex: str, alpha: float) -> tuple:
        """Simula visualmente uma cor com opacidade 'alpha' sobre fundo branco --
        usado pra escolher a cor do texto de barras que tem set_alpha() aplicado,
        ja que a cor "real" da barra (mais clara na tela) e' diferente da cor solida
        original passada pro matplotlib."""
        r, g, b = mcolors.to_rgb(cor_hex)
        return (r * alpha + (1 - alpha), g * alpha + (1 - alpha), b * alpha + (1 - alpha))

    def _desenhar_barras_agrupadas(self, ax, x, largura_total: float, series: list[tuple[str, list[float], str]],
                                    fmt=lambda v: f"{v:,.0f}", fontsize: int = 9):
        """Desenha N barras agrupadas lado a lado (N = len(series)), cada uma com seu
        proprio rotulo/valores/cor. Usado para 1, 2 ou 3 series (modo absoluto, ano
        anterior, ou ano anterior + outro periodo). Os valores ficam DENTRO de cada
        barra (centralizados), com a cor do texto escolhida automaticamente pra
        contrastar com a cor de fundo da barra."""
        n = len(series)
        largura = largura_total / max(n, 1)
        deslocamentos = [(-((n - 1) / 2) + i) * largura for i in range(n)]
        for (label, valores, cor), deslocamento in zip(series, deslocamentos):
            barras = ax.bar([xi + deslocamento for xi in x], valores, largura, label=label, color=cor)
            cor_texto = self._cor_texto_sobre_fundo(cor)
            ax.bar_label(barras, labels=[fmt(v) for v in barras.datavalues], label_type="center",
                          fontsize=fontsize, color=cor_texto, fontweight="bold")

    def _series_comparacao(self, resumo: ResumoSellIn) -> list[tuple[str, str]]:
        """Retorna a lista de (label, cor) das series ativas nesta comparacao, na ordem
        em que devem aparecer nos graficos de LINHA (que nao usam outro_periodo): ano
        anterior (se ativo) seguido do ano atual."""
        series = []
        if resumo.comparar_ano_anterior:
            series.append((resumo.rotulo_anterior, COR_ANO_ANTERIOR))
        series.append((resumo.rotulo_atual, COR_ANO_ATUAL))
        return series

    def _evolucao_mensal(self, resumo: ResumoSellIn) -> bytes:
        meses = resumo.meses_comparados
        labels_mes = self._labels_mes(meses, resumo.periodo_atual_chaves)
        largura = 0.38
        x = range(len(meses))
        ano_ant, ano_atu = resumo.ano_anterior, resumo.ano_atual

        fig, (ax_fat, ax_vol) = plt.subplots(2, 1, figsize=(10, 9), sharex=True)
        periodo = f"{labels_mes[0]} a {labels_mes[-1]}" if len(labels_mes) > 1 else labels_mes[0]
        fig.suptitle(f"Evolução mensal - {periodo}", fontsize=16, fontweight="bold", color="#1F2A37")

        fontes = (
            (ax_fat, resumo.faturamento_mensal, "Faturamento (R$ K)", 1_000),
            (ax_vol, resumo.volume_mensal, "Volume (m² K)", 1_000),
        )
        for eixo, dados, titulo, divisor in fontes:
            valores_ant = [float(dados.get((ano_ant, m), Decimal(0))) / divisor for m in meses]
            valores_atu = [float(dados.get((ano_atu, m), Decimal(0))) / divisor for m in meses]

            barras_ant = eixo.bar([i - largura / 2 for i in x], valores_ant, largura,
                                   label=resumo.rotulo_anterior, color=COR_ANO_ANTERIOR)
            barras_atu = eixo.bar([i + largura / 2 for i in x], valores_atu, largura,
                                   label=resumo.rotulo_atual, color=COR_ANO_ATUAL)

            for barras, cor in ((barras_ant, COR_ANO_ANTERIOR), (barras_atu, COR_ANO_ATUAL)):
                eixo.bar_label(barras, labels=[f"{v:,.0f}" for v in barras.datavalues],
                                label_type="center", fontsize=7, color=self._cor_texto_sobre_fundo(cor),
                                fontweight="bold")

            eixo.set_title(titulo, fontsize=12, loc="left", color="#374151")
            eixo.set_xticks(list(x))
            eixo.set_xticklabels(labels_mes)
            eixo.spines[["top", "right", "left"]].set_visible(False)
            eixo.yaxis.set_visible(False)
            eixo.tick_params(axis="x", length=0)

        ax_fat.legend(loc="upper left", frameon=False, ncols=2)

        total_ant = sum(resumo.faturamento_mensal.get((ano_ant, m), Decimal(0)) for m in meses)
        total_atu = sum(resumo.faturamento_mensal.get((ano_atu, m), Decimal(0)) for m in meses)
        variacao = (total_atu / total_ant - 1) * 100 if total_ant else Decimal(0)
        fig.text(0.5, 0.02,
                  f"Faturamento total: R\\$ {total_ant/1_000_000:.0f} mi ({resumo.rotulo_anterior}) "
                  f"→ R\\$ {total_atu/1_000_000:.0f} mi ({resumo.rotulo_atual})  |  variação: {float(variacao):+.0f}%",
                  ha="center", fontsize=10, color="#6B7280")

        fig.tight_layout(rect=(0, 0.05, 1, 0.95))
        return self._salvar(fig)

    def _representatividade(self, resumo: ResumoSellIn) -> bytes:
        tipologias = ["Cerâmica", "Porcelanato", "Super Prime"]
        anos = [resumo.ano_anterior, resumo.ano_atual]
        fig, ax = plt.subplots(figsize=(10, 3.2))

        for i, ano in enumerate(anos):
            totais_ano = resumo.faturamento_por_tipologia.get(ano, {})
            total_ano = sum(totais_ano.values()) or Decimal(1)
            esquerda = 0.0
            for tipologia in tipologias:
                participacao = float(totais_ano.get(tipologia, Decimal(0)) / total_ano) * 100
                ax.barh(i, participacao, left=esquerda, color=COR_TIPOLOGIA[tipologia], height=0.55,
                        label=tipologia if i == 0 else None)
                if participacao > 4:
                    ax.text(esquerda + participacao / 2, i, f"{participacao:.0f}%",
                            ha="center", va="center", color="white", fontsize=9, fontweight="bold")
                esquerda += participacao

        ax.set_yticks(list(range(len(anos))))
        ax.set_yticklabels([str(a) for a in anos], fontsize=11)
        ax.set_xlim(0, 100)
        ax.xaxis.set_visible(False)
        ax.spines[:].set_visible(False)
        ax.set_title("Representatividade por tipologia (% do faturamento)",
                      fontsize=13, loc="left", color="#1F2A37", fontweight="bold")
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.15), ncols=3, frameon=False)

        fig.tight_layout()
        return self._salvar(fig)

    def _tipologia_mensal(self, resumo: ResumoSellIn) -> bytes:
        tipologias = ["Cerâmica", "Porcelanato", "Super Prime"]
        chaves_ordenadas = [(ano, mes) for ano in (resumo.ano_anterior, resumo.ano_atual)
                             for mes in resumo.meses_comparados]
        if resumo.ano_anterior == resumo.ano_atual:
            chaves_ordenadas = [(resumo.ano_atual, mes) for mes in resumo.meses_comparados]

        x = range(len(chaves_ordenadas))
        labels_x = [f"{MESES_NOMES[mes - 1]}/{str(ano)[2:]}" for ano, mes in chaves_ordenadas]

        series = {tipologia: [] for tipologia in tipologias}
        for chave in chaves_ordenadas:
            totais_mes = resumo.faturamento_tipologia_mensal.get(chave, {})
            total_mes = sum(totais_mes.values()) or Decimal(1)
            for tipologia in tipologias:
                series[tipologia].append(float(totais_mes.get(tipologia, Decimal(0)) / total_mes) * 100)

        fig, ax = plt.subplots(figsize=(11, 5))
        ax.stackplot(list(x), *[series[t] for t in tipologias],
                     labels=tipologias, colors=[COR_TIPOLOGIA[t] for t in tipologias], alpha=0.9)

        ax.set_xticks(list(x))
        ax.set_xticklabels(labels_x, fontsize=9)
        ax.set_ylim(0, 100)
        ax.yaxis.set_major_formatter(mticker.PercentFormatter())
        ax.spines[["top", "right"]].set_visible(False)
        ax.set_title("Participação mensal de cada tipologia no faturamento",
                      fontsize=13, loc="left", color="#1F2A37", fontweight="bold")
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncols=3, frameon=False)
        if resumo.ano_anterior != resumo.ano_atual:
            ax.axvline(x=len(resumo.meses_comparados) - 0.5, color="white", linewidth=2,
                       linestyle="--", alpha=0.7)

        fig.tight_layout()
        return self._salvar(fig)

    def gerar_graficos_slide(self, resumo: ResumoSellIn) -> dict[str, bytes]:
        """Versoes compactas e sem titulo dos graficos, pensadas para serem inseridas
        como imagem dentro de um slide (o titulo fica a cargo do proprio slide)."""
        plt.rcParams["font.family"] = "sans-serif"
        plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial"]

        return {
            "evolucao_mensal.png": self._evolucao_mensal_slide(resumo),
            "representatividade.png": self._representatividade_slide(resumo),
            "tipologia_mensal.png": self._tipologia_mensal_slide(resumo),
        }

    def gerar_graficos_slide_linha(self, resumo: ResumoSellIn) -> dict[str, bytes]:
        """Mesmas 3 analises, em versao grafico de linha (para os slides 4-6)."""
        plt.rcParams["font.family"] = "sans-serif"
        plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial"]

        return {
            "evolucao_mensal_linha.png": self._evolucao_mensal_linha_slide(resumo),
            "representatividade_linha.png": self._representatividade_linha_slide(resumo),
            "tipologia_mensal_linha.png": self._tipologia_mensal_linha_slide(resumo),
        }

    def gerar_graficos_ticket_medio(self, resumo: ResumoSellIn) -> dict[str, bytes]:
        """Faturamento por m² (ticket medio = valor / qtde) mes a mes, um grafico por tipologia."""
        plt.rcParams["font.family"] = "sans-serif"
        plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial"]

        chaves_arquivo = {
            "Cerâmica": "ticket_medio_ceramica.png",
            "Porcelanato": "ticket_medio_porcelanato.png",
            "Super Prime": "ticket_medio_super_prime.png",
        }
        return {
            chave: self._ticket_medio_tipologia_slide(resumo, tipologia)
            for tipologia, chave in chaves_arquivo.items()
        }

    def gerar_graficos_faturamento_tipologia(self, resumo: ResumoSellIn) -> dict[str, bytes]:
        """Faturamento em R$ (sem dividir por volume) mes a mes, um grafico por tipologia."""
        plt.rcParams["font.family"] = "sans-serif"
        plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial"]

        chaves_arquivo = {
            "Cerâmica": "faturamento_tipologia_ceramica.png",
            "Porcelanato": "faturamento_tipologia_porcelanato.png",
            "Super Prime": "faturamento_tipologia_super_prime.png",
        }
        return {
            chave: self._faturamento_tipologia_slide(resumo, tipologia)
            for tipologia, chave in chaves_arquivo.items()
        }

    def gerar_graficos_participacao_tipologia(self, resumo: ResumoSellIn) -> dict[str, bytes]:
        """Participacao (%) no faturamento total, mes a mes, um grafico por tipologia."""
        plt.rcParams["font.family"] = "sans-serif"
        plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial"]

        chaves_arquivo = {
            "Cerâmica": "participacao_tipologia_ceramica.png",
            "Porcelanato": "participacao_tipologia_porcelanato.png",
            "Super Prime": "participacao_tipologia_super_prime.png",
        }
        return {
            chave: self._participacao_tipologia_slide(resumo, tipologia)
            for tipologia, chave in chaves_arquivo.items()
        }

    def gerar_grafico_volume_mensal(self, resumo: ResumoSellIn) -> bytes:
        """Volume vendido (m²) mes a mes, ano anterior x ano atual."""
        plt.rcParams["font.family"] = "sans-serif"
        plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial"]
        return self._volume_mensal_slide(resumo)

    def gerar_grafico_ticket_medio_geral(self, resumo: ResumoSellIn) -> bytes:
        """Valor medio por unidade (R$/m²) do negocio inteiro (nao por tipologia), mes a mes."""
        plt.rcParams["font.family"] = "sans-serif"
        plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial"]
        return self._ticket_medio_geral_slide(resumo)

    def gerar_grafico_crescimento_ticket_medio(self, resumo: ResumoSellIn) -> bytes:
        """Crescimento percentual (ano atual vs ano anterior) do valor medio por unidade, mes a mes."""
        plt.rcParams["font.family"] = "sans-serif"
        plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial"]
        return self._crescimento_ticket_medio_slide(resumo)

    def gerar_grafico_desempenho_tipologias(self, resumo: ResumoSellIn) -> bytes:
        """Faturamento total por tipologia, periodo selecionado x periodo do ano anterior."""
        plt.rcParams["font.family"] = "sans-serif"
        plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial"]
        return self._desempenho_tipologias_slide(resumo)

    def gerar_grafico_ticket_medio_tipologias(self, resumo: ResumoSellIn) -> bytes:
        """Apesar do nome (mantido por compatibilidade com a chave de arquivo ja usada
        em outros pontos do codigo), este grafico mostra o VOLUME vendido (mil m²) mes
        a mes, com as 3 tipologias juntas no mesmo grafico (cada uma com 2 linhas: ano
        anterior tracejado, ano atual solido) -- volume e' a metrica analisada aqui,
        nao o ticket medio."""
        plt.rcParams["font.family"] = "sans-serif"
        plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial"]
        return self._tipologias_juntas_slide(resumo, metrica="volume")

    def gerar_grafico_faturamento_tipologias(self, resumo: ResumoSellIn) -> bytes:
        """Faturamento total (R$ mil) mes a mes, com as 3 tipologias juntas no mesmo
        grafico (cada uma com 2 linhas: ano anterior tracejado, ano atual solido)."""
        plt.rcParams["font.family"] = "sans-serif"
        plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial"]
        return self._tipologias_juntas_slide(resumo, metrica="faturamento")

    def gerar_grafico_representatividade_volume(self, resumo: ResumoSellIn) -> bytes:
        """Participacao (%) de cada tipologia no volume total vendido (m²) -- mesma
        logica da representatividade por faturamento, so que a partir do volume."""
        plt.rcParams["font.family"] = "sans-serif"
        plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial"]
        return self._representatividade_volume_slide(resumo)

    def gerar_grafico_pizza_tipologia(self, totais: dict) -> bytes:
        """Pizza com a participacao (%) de cada tipologia dentro do dicionario informado
        (pode ser volume em m² ou faturamento em R$, tanto faz -- a pizza so olha a
        proporcao entre as 3 tipologias). Usada nos slides de 'Proporção por Tipologia'
        depois que trocaram de barra empilhada para pizza, a pedido do usuario."""
        plt.rcParams["font.family"] = "sans-serif"
        plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial"]
        return self._pizza_tipologia_slide(totais)

    def _pizza_tipologia_slide(self, totais: dict) -> bytes:
        tipologias = ["Cerâmica", "Porcelanato", "Super Prime"]
        valores = [float(totais.get(t, Decimal(0))) for t in tipologias]
        if sum(valores) <= 0:
            valores = [1.0, 1.0, 1.0]
        cores = [COR_TIPOLOGIA[t] for t in tipologias]

        fig, ax = plt.subplots(figsize=(4.3, 3.9))
        wedges, _textos, autotextos = ax.pie(
            valores, colors=cores, autopct=lambda p: f"{p:.0f}%" if p >= 4 else "",
            pctdistance=0.72, startangle=90,
            wedgeprops={"linewidth": 2, "edgecolor": "white"},
            textprops={"fontsize": 12, "fontweight": "bold"},
        )
        for wedge, autotexto in zip(wedges, autotextos):
            autotexto.set_color(self._cor_texto_sobre_fundo(wedge.get_facecolor()))
        ax.legend(tipologias, loc="upper center", bbox_to_anchor=(0.5, -0.02), ncols=3,
                  frameon=False, fontsize=8.5)
        ax.set_aspect("equal")
        fig.tight_layout()
        return self._salvar(fig, transparente=True)

    def gerar_grafico_crescimento_tipologia_mensal(self, resumo: ResumoSellIn) -> bytes:
        """Crescimento percentual mes a mes (dentro do proprio periodo analisado, nao
        comparado com o ano anterior) do faturamento de cada tipologia -- mostra se o
        ritmo de vendas de cada tipologia esta acelerando ou desacelerando ao longo do
        periodo, tipologia a tipologia."""
        plt.rcParams["font.family"] = "sans-serif"
        plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial"]
        return self._crescimento_tipologia_mensal_slide(resumo)

    def _crescimento_tipologia_mensal_slide(self, resumo: ResumoSellIn) -> bytes:
        tipologias = ["Cerâmica", "Porcelanato", "Super Prime"]
        chaves_atual = [(resumo.ano_atual, m) for m in resumo.meses_comparados]
        chaves_display = resumo.periodo_atual_chaves

        fig, ax = plt.subplots(figsize=(4.0, 2.7))
        for tipologia in tipologias:
            valores_mes = [float(resumo.faturamento_tipologia_mensal.get(c, {}).get(tipologia, Decimal(0)))
                            for c in chaves_atual]
            xs, ys = [], []
            for i in range(1, len(valores_mes)):
                anterior = valores_mes[i - 1]
                if anterior:
                    xs.append(i)
                    ys.append((valores_mes[i] / anterior - 1) * 100)
            if xs:
                ax.plot(xs, ys, marker="o", linewidth=2.2, markersize=5,
                        color=COR_TIPOLOGIA[tipologia], label=tipologia)

        ax.axhline(0, color="#B0B7C6", linewidth=1)
        ax.set_xticks(list(range(len(chaves_atual))))
        labels_reduzidos = self._reduzir_labels_por_ano(chaves_display)
        ax.set_xticklabels(labels_reduzidos, fontsize=8)
        ax.yaxis.set_major_formatter(mticker.PercentFormatter())
        ax.tick_params(axis="y", labelsize=9)
        ax.spines[["top", "right"]].set_visible(False)
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.16), ncols=3, frameon=False, fontsize=8)
        fig.tight_layout()
        return self._salvar(fig, transparente=True)

    def _formatos_tipologia_slide(self, resumo: ResumoSellIn, tipologia: str, por_ano_tipologia_formato: dict) -> bytes:
        """Estudo de formatos: barra empilhada com a participacao (%) de cada formato
        (ex: 33x46) DENTRO de uma unica tipologia -- mesma logica de
        _representatividade_generica_slide, so que uma tipologia por vez e com as
        categorias sendo os formatos (nao as 3 tipologias)."""
        linhas = []
        if resumo.comparar_ano_anterior:
            linhas.append((resumo.rotulo_anterior,
                            por_ano_tipologia_formato.get(resumo.ano_anterior, {}).get(tipologia, {})))
        linhas.append((resumo.rotulo_atual,
                        por_ano_tipologia_formato.get(resumo.ano_atual, {}).get(tipologia, {})))

        formatos = FORMATOS_POR_TIPOLOGIA[tipologia]
        cores = dict(zip(formatos, self._paleta_distinta_formatos(len(formatos))))
        # Esse grafico agora ocupa o slide inteiro (o slide so mostra volume, nao mais
        # volume + faturamento lado a lado), entao usa a largura toda disponivel.
        return self._barra_empilhada_proporcao(linhas, categorias=formatos, cores=cores,
                                                mostrar_legenda=True, largura_fig=8.6)

    def gerar_grafico_formatos_tipologia_volume(self, resumo: ResumoSellIn, tipologia: str) -> bytes:
        """Participacao (%) de cada formato no volume (m²) DENTRO da tipologia informada."""
        plt.rcParams["font.family"] = "sans-serif"
        plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial"]
        return self._formatos_tipologia_slide(resumo, tipologia, resumo.qtde_por_formato)

    def gerar_grafico_formatos_tipologia_faturamento(self, resumo: ResumoSellIn, tipologia: str) -> bytes:
        """Participacao (%) de cada formato no faturamento (R$) DENTRO da tipologia informada."""
        plt.rcParams["font.family"] = "sans-serif"
        plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial"]
        return self._formatos_tipologia_slide(resumo, tipologia, resumo.faturamento_por_formato)

    def _reduzir_labels_por_ano(self, chaves: list[tuple[int, int]]) -> list[str]:
        """Mantem sempre o primeiro mes de cada ano visivel e reduz de 2 em 2 dentro de
        cada ano -- evita que a troca de ano "engula" o rotulo de Janeiro (o que acontecia
        reduzindo por indice global, quando o ano tem uma quantidade impar de meses).
        Se o ultimo rotulo mostrado de um ano acabar colado no Janeiro do ano seguinte
        (ano com quantidade impar de meses), o rotulo anterior e' ocultado para não colidir."""
        labels = []
        ano_atual_iter = None
        indice_no_ano = 0
        for ano, mes in chaves:
            if ano != ano_atual_iter:
                ano_atual_iter = ano
                indice_no_ano = 0
            rotulo = f"{MESES_NOMES[mes - 1]}/{str(ano)[2:]}"
            labels.append(rotulo if indice_no_ano % 2 == 0 else "")
            indice_no_ano += 1

        for i in range(len(labels) - 1):
            if labels[i] and labels[i + 1]:
                labels[i] = ""

        return labels

    def _evolucao_mensal_slide(self, resumo: ResumoSellIn) -> bytes:
        meses = resumo.meses_comparados
        labels_mes = self._labels_mes(meses, resumo.periodo_atual_chaves)
        ano_ant, ano_atu = resumo.ano_anterior, resumo.ano_atual
        x = list(range(len(meses)))

        series = []
        if resumo.comparar_ano_anterior:
            valores_ant = [float(resumo.faturamento_mensal.get((ano_ant, m), Decimal(0))) / 1_000 for m in meses]
            series.append((resumo.rotulo_anterior, valores_ant, COR_ANO_ANTERIOR))
        valores_atu = [float(resumo.faturamento_mensal.get((ano_atu, m), Decimal(0))) / 1_000 for m in meses]
        series.append((resumo.rotulo_atual, valores_atu, COR_ANO_ATUAL))
        if resumo.outro_periodo is not None:
            media_outro = float(resumo.outro_periodo.faturamento_mensal_medio) / 1_000
            series.append((resumo.outro_periodo.label, [media_outro] * len(meses), COR_OUTRO_PERIODO))

        fig, ax = plt.subplots(figsize=(8.6, 3.6))
        self._desenhar_barras_agrupadas(ax, x, 0.7, series, fontsize=9)
        ax.set_xticks(x)
        ax.set_xticklabels(labels_mes, fontsize=11)
        ax.spines[["top", "right", "left"]].set_visible(False)
        ax.yaxis.set_visible(False)
        ax.tick_params(axis="x", length=0)
        ax.margins(y=0.2)
        ax.legend(loc="upper left", frameon=False, ncols=min(len(series), 3), fontsize=10)
        fig.tight_layout()
        return self._salvar(fig, transparente=True)

    def _representatividade_slide(self, resumo: ResumoSellIn) -> bytes:
        outro = resumo.outro_periodo.faturamento_por_tipologia if resumo.outro_periodo else None
        return self._representatividade_generica_slide(resumo, resumo.faturamento_por_tipologia, outro)

    def _representatividade_volume_slide(self, resumo: ResumoSellIn) -> bytes:
        outro = resumo.outro_periodo.qtde_por_tipologia if resumo.outro_periodo else None
        return self._representatividade_generica_slide(resumo, resumo.qtde_por_tipologia, outro)

    def _representatividade_generica_slide(self, resumo: ResumoSellIn, por_ano: dict, outro_totais: dict | None) -> bytes:
        """Desenha a barra empilhada de representatividade por tipologia a partir de
        um dicionario {ano: {tipologia: valor}} generico -- usado tanto para
        faturamento quanto para volume (m²), so trocando o dicionario de entrada."""
        linhas = []
        if resumo.outro_periodo is not None and outro_totais is not None:
            linhas.append((resumo.outro_periodo.label, outro_totais))
        if resumo.comparar_ano_anterior:
            linhas.append((resumo.rotulo_anterior, por_ano.get(resumo.ano_anterior, {})))
        linhas.append((resumo.rotulo_atual, por_ano.get(resumo.ano_atual, {})))

        # mostrar_legenda=True: esse grafico agora e' o conteudo principal (as vezes
        # unico) do slide, sem mais o painel lateral com os nomes das tipologias ao
        # lado -- sem legenda, as cores da barra ficavam sem identificacao nenhuma.
        return self._barra_empilhada_proporcao(linhas, mostrar_legenda=True, largura_fig=8.6)

    def _paleta_formatos(self, cor_base_hex: str, n: int) -> list[str]:
        """Gera N tons distintos (do mais escuro ao mais claro) a partir de UMA cor
        base -- ficou vestigial pro estudo de formatos (ver _paleta_distinta_formatos)
        depois que o usuario reportou que tons de uma so cor confundiam a leitura do
        grafico com ate 9 formatos, mas mantido caso sirva pra outro uso futuro."""
        r, g, b = mcolors.to_rgb(cor_base_hex)
        escuro = (r * 0.55, g * 0.55, b * 0.55)
        claro = (r + (1 - r) * 0.7, g + (1 - g) * 0.7, b + (1 - b) * 0.7)
        if n <= 1:
            return [cor_base_hex]
        return [
            mcolors.to_hex(tuple(escuro[k] + (claro[k] - escuro[k]) * (i / (n - 1)) for k in range(3)))
            for i in range(n)
        ]

    def _paleta_distinta_formatos(self, n: int) -> list[str]:
        """Retorna N cores bem distintas entre si (nao tons de uma mesma cor) pra
        colorir os formatos dentro de uma tipologia -- uma cor por formato, sempre na
        mesma ordem, entao o mesmo formato (ex: 33x46) fica com a mesma cor em
        qualquer grafico. Repete a paleta em ciclo se precisar de mais de 9 (nao deve
        acontecer com os dados atuais, mas evita erro caso apareca um formato novo)."""
        if n <= len(PALETA_FORMATOS_DISTINTA):
            return PALETA_FORMATOS_DISTINTA[:n]
        return [PALETA_FORMATOS_DISTINTA[i % len(PALETA_FORMATOS_DISTINTA)] for i in range(n)]

    def _barra_empilhada_proporcao(self, linhas: list[tuple[str, dict]],
                                    categorias: list[str] | None = None,
                                    cores: dict[str, str] | None = None,
                                    mostrar_legenda: bool = False,
                                    largura_fig: float | None = None) -> bytes:
        """Desenha N barras horizontais empilhadas (uma por linha de 'linhas'), cada
        uma repartida por categoria em %. Por padrao a categoria e' a tipologia (3
        cores fixas), mas tambem e' usada pro estudo de formatos dentro de UMA
        tipologia (ate 9 categorias, cores em tons da cor da tipologia) -- generico
        o bastante pra servir tanto na comparacao ano a ano quanto periodo a periodo."""
        categorias = categorias if categorias is not None else ["Cerâmica", "Porcelanato", "Super Prime"]
        cores = cores if cores is not None else COR_TIPOLOGIA

        altura_base = 2.5 if len(linhas) <= 2 else 3.1
        largura = 4.0
        if mostrar_legenda:
            # Com muitas categorias (ex: 9 formatos) a legenda vira varias linhas --
            # da mais espaco vertical embaixo do grafico pra ela nao ficar espremida.
            linhas_legenda = -(-len(categorias) // 3)  # arredonda pra cima (ncols fixo em 3)
            altura_base += max(0, linhas_legenda - 1) * 0.3
            largura = 4.4
            if len(linhas) == 2:
                altura_base += 0.5  # espaco extra pro afastamento entre as 2 barras (ver espacamento abaixo)
        if largura_fig is not None:
            largura = largura_fig
        fig, ax = plt.subplots(figsize=(largura, altura_base))

        # Barra e' estreita, entao fatias pequenas (ex: 13%, 11% lado a lado) nao tem
        # espaco pro texto branco em negrito sem colidir com a fatia vizinha. Fatias
        # grandes o bastante ganham o rotulo branco centralizado DENTRO da barra;
        # fatias estreitas ganham o rotulo POR FORA, alternando acima/abaixo a cada
        # fatia estreita consecutiva, pra que duas fatias estreitas vizinhas nunca
        # disputem a mesma faixa horizontal.
        LIMITE_ROTULO_INTERNO = 15
        # Com muitas categorias (formatos), fatias bem pequenas (ex: 2%, 4%) acabam
        # coladas umas nas outras -- rotula-las por fora so criaria uma pilha de
        # numeros ilegivel. Nesses casos, a cor + legenda ja identificam a fatia; so
        # fatias menores acima desse limite ganham rotulo POR FORA da barra.
        LIMITE_ROTULO_MINIMO = 5 if mostrar_legenda else 0
        # Quando ha' rotulos POR FORA da barra (mostrar_legenda=True, ate' 9 fatias
        # pequenas por linha) e exatamente 2 linhas, o espaco entre elas e' estreito
        # demais: o rotulo "de cima" da linha de baixo e o rotulo "de baixo" da linha
        # de cima acabam colidindo no meio. Nesse caso especifico, afasta as duas
        # barras uma da outra (mais espaco em branco no meio) sem mudar a altura de
        # cada barra em si.
        espacamento = 1.6 if (mostrar_legenda and len(linhas) == 2) else 1.0
        posicoes = [i * espacamento for i in range(len(linhas))]
        for i, (rotulo, totais), pos in zip(range(len(linhas)), linhas, posicoes):
            total = sum(totais.values()) or Decimal(1)
            esquerda = 0.0
            lado_externo = 1
            for categoria in categorias:
                participacao = float(totais.get(categoria, Decimal(0)) / total) * 100
                if participacao <= 0:
                    continue
                ax.barh(pos, participacao, left=esquerda, color=cores[categoria], height=0.55,
                        label=categoria if i == 0 else None)
                centro = esquerda + participacao / 2
                if participacao >= LIMITE_ROTULO_INTERNO:
                    ax.text(centro, pos, f"{participacao:.0f}%", ha="center", va="center",
                            color=self._cor_texto_sobre_fundo(cores[categoria]), fontsize=10, fontweight="bold")
                elif participacao >= LIMITE_ROTULO_MINIMO:
                    y_rotulo = pos + 0.4 * lado_externo
                    va = "bottom" if lado_externo > 0 else "top"
                    ax.text(centro, y_rotulo, f"{participacao:.0f}%", ha="center", va=va,
                            color=cores[categoria], fontsize=9, fontweight="bold")
                    lado_externo *= -1
                esquerda += participacao

        ax.set_yticks(posicoes)
        ax.set_yticklabels([rotulo for rotulo, _ in linhas], fontsize=10)
        ax.set_xlim(0, 100)
        ax.set_ylim(-0.75, (posicoes[-1] if posicoes else 0) + 0.75)
        ax.xaxis.set_visible(False)
        ax.spines[:].set_visible(False)
        if mostrar_legenda:
            ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncols=min(len(categorias), 3),
                      frameon=False, fontsize=8)
        fig.tight_layout()
        return self._salvar(fig, transparente=True)

    def _tipologia_mensal_slide(self, resumo: ResumoSellIn) -> bytes:
        tipologias = ["Cerâmica", "Porcelanato", "Super Prime"]
        ano_ant, ano_atu = resumo.ano_anterior, resumo.ano_atual

        if resumo.comparar_ano_anterior:
            chaves = [(ano, mes) for ano in (ano_ant, ano_atu) for mes in resumo.meses_comparados]
            chaves_display = resumo.periodo_anterior_chaves + resumo.periodo_atual_chaves
            if ano_ant == ano_atu:
                chaves = [(ano_atu, mes) for mes in resumo.meses_comparados]
                chaves_display = resumo.periodo_atual_chaves
        else:
            chaves = [(ano_atu, mes) for mes in resumo.meses_comparados]
            chaves_display = resumo.periodo_atual_chaves

        xr = range(len(chaves))
        series = {t: [] for t in tipologias}
        for chave in chaves:
            totais_mes = resumo.faturamento_tipologia_mensal.get(chave, {})
            total_mes = sum(totais_mes.values()) or Decimal(1)
            for t in tipologias:
                series[t].append(float(totais_mes.get(t, Decimal(0)) / total_mes) * 100)

        fig, ax = plt.subplots(figsize=(4.0, 2.7))
        ax.stackplot(list(xr), *[series[t] for t in tipologias],
                     labels=tipologias, colors=[COR_TIPOLOGIA[t] for t in tipologias], alpha=0.9)
        ax.set_xticks(list(xr))
        # Usa as chaves REAIS (nao as sinteticas de _agregar) so pra montar o rotulo de
        # texto -- assim, se o periodo cruzar a virada do ano, o mes mostrado no eixo
        # (ex: "Out/25") reflete o ano de verdade daquela venda, nao o rotulo interno.
        labels_reduzidos = self._reduzir_labels_por_ano(chaves_display)
        ax.set_xticklabels(labels_reduzidos, fontsize=8)
        ax.set_ylim(0, 100)
        ax.yaxis.set_major_formatter(mticker.PercentFormatter())
        ax.tick_params(axis="y", labelsize=9)
        ax.spines[["top", "right"]].set_visible(False)
        if resumo.comparar_ano_anterior and ano_ant != ano_atu:
            ax.axvline(x=len(resumo.meses_comparados) - 0.5, color="white", linewidth=2,
                       linestyle="--", alpha=0.8)
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.16), ncols=3, frameon=False, fontsize=8)
        fig.tight_layout()
        return self._salvar(fig, transparente=True)

    def _evolucao_mensal_linha_slide(self, resumo: ResumoSellIn) -> bytes:
        meses = resumo.meses_comparados
        labels_mes = self._labels_mes(meses, resumo.periodo_atual_chaves)
        ano_ant, ano_atu = resumo.ano_anterior, resumo.ano_atual
        x = list(range(len(meses)))

        fig, ax = plt.subplots(figsize=(8.6, 3.15))
        valores_ant = [float(resumo.faturamento_mensal.get((ano_ant, m), Decimal(0))) / 1_000 for m in meses]
        valores_atu = [float(resumo.faturamento_mensal.get((ano_atu, m), Decimal(0))) / 1_000 for m in meses]

        ax.plot(x, valores_ant, marker="o", linewidth=2.5, color=COR_ANO_ANTERIOR, label=resumo.rotulo_anterior)
        ax.plot(x, valores_atu, marker="o", linewidth=2.5, color=COR_ANO_ATUAL, label=resumo.rotulo_atual)

        for xi, v in zip(x, valores_ant):
            ax.annotate(f"{v:,.0f}", (xi, v), textcoords="offset points", xytext=(0, -14),
                        ha="center", fontsize=8, color="#6B7280")
        for xi, v in zip(x, valores_atu):
            ax.annotate(f"{v:,.0f}", (xi, v), textcoords="offset points", xytext=(0, 8),
                        ha="center", fontsize=8, color="#374151", fontweight="bold")

        ax.set_xticks(x)
        ax.set_xticklabels(labels_mes, fontsize=11)
        ax.spines[["top", "right", "left"]].set_visible(False)
        ax.yaxis.set_visible(False)
        ax.tick_params(axis="x", length=0)
        ax.margins(y=0.25)
        ax.legend(loc="upper left", frameon=False, ncols=2, fontsize=11)
        fig.tight_layout()
        return self._salvar(fig, transparente=True)

    def _representatividade_linha_slide(self, resumo: ResumoSellIn) -> bytes:
        tipologias = ["Cerâmica", "Porcelanato", "Super Prime"]
        ano_ant, ano_atu = resumo.ano_anterior, resumo.ano_atual
        x = [0, 1]

        fig, ax = plt.subplots(figsize=(4.0, 2.7))
        for tipologia in tipologias:
            valores = []
            for ano in (ano_ant, ano_atu):
                totais_ano = resumo.faturamento_por_tipologia.get(ano, {})
                total_ano = sum(totais_ano.values()) or Decimal(1)
                valores.append(float(totais_ano.get(tipologia, Decimal(0)) / total_ano) * 100)
            ax.plot(x, valores, marker="o", linewidth=2.5, markersize=7,
                    color=COR_TIPOLOGIA[tipologia], label=tipologia)
            ax.annotate(f"{valores[0]:.0f}%", (x[0], valores[0]), textcoords="offset points",
                        xytext=(-8, 0), ha="right", va="center", fontsize=9, fontweight="bold",
                        color=COR_TIPOLOGIA[tipologia])
            ax.annotate(f"{valores[-1]:.0f}%", (x[-1], valores[-1]), textcoords="offset points",
                        xytext=(8, 0), ha="left", va="center", fontsize=9, fontweight="bold",
                        color=COR_TIPOLOGIA[tipologia])

        ax.set_xlim(-0.3, 1.5)
        ax.set_xticks(x)
        ax.set_xticklabels([resumo.rotulo_anterior, resumo.rotulo_atual], fontsize=11)
        ax.yaxis.set_visible(False)
        ax.spines[["top", "right", "left"]].set_visible(False)
        ax.tick_params(axis="x", length=0)
        ax.legend(loc="upper center", bbox_to_anchor=(0.4, -0.14), ncols=3, frameon=False, fontsize=7.5)
        fig.tight_layout()
        return self._salvar(fig, transparente=True)

    def _tipologia_mensal_linha_slide(self, resumo: ResumoSellIn) -> bytes:
        tipologias = ["Cerâmica", "Porcelanato", "Super Prime"]
        ano_ant, ano_atu = resumo.ano_anterior, resumo.ano_atual
        chaves = [(ano, mes) for ano in (ano_ant, ano_atu) for mes in resumo.meses_comparados]
        chaves_display = resumo.periodo_anterior_chaves + resumo.periodo_atual_chaves
        if ano_ant == ano_atu:
            chaves = [(ano_atu, mes) for mes in resumo.meses_comparados]
            chaves_display = resumo.periodo_atual_chaves

        xr = list(range(len(chaves)))
        series = {t: [] for t in tipologias}
        for chave in chaves:
            totais_mes = resumo.faturamento_tipologia_mensal.get(chave, {})
            total_mes = sum(totais_mes.values()) or Decimal(1)
            for t in tipologias:
                series[t].append(float(totais_mes.get(t, Decimal(0)) / total_mes) * 100)

        fig, ax = plt.subplots(figsize=(4.0, 2.7))
        for tipologia in tipologias:
            ax.plot(xr, series[tipologia], linewidth=2, color=COR_TIPOLOGIA[tipologia], label=tipologia)

        ax.set_xticks(xr)
        labels_reduzidos = self._reduzir_labels_por_ano(chaves_display)
        ax.set_xticklabels(labels_reduzidos, fontsize=8)
        ax.set_ylim(0, 100)
        ax.yaxis.set_major_formatter(mticker.PercentFormatter())
        ax.tick_params(axis="y", labelsize=9)
        ax.spines[["top", "right"]].set_visible(False)
        if ano_ant != ano_atu:
            ax.axvline(x=len(resumo.meses_comparados) - 0.5, color="#D1D5DB", linewidth=2,
                       linestyle="--", alpha=0.8)
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.16), ncols=3, frameon=False, fontsize=8)
        fig.tight_layout()
        return self._salvar(fig, transparente=True)

    def _ticket_medio_tipologia_slide(self, resumo: ResumoSellIn, tipologia: str) -> bytes:
        """Apesar do nome (mantido por compatibilidade com as chaves de arquivo ja
        usadas em outros pontos do codigo), este grafico mostra o VOLUME vendido (mil
        m²) mes a mes de uma tipologia -- nao o ticket medio (R$/m²). O ticket medio
        continua disponivel como estatistica no painel lateral do slide; o grafico em
        si e' sobre volume, que e' a metrica analisada nestes slides."""
        meses = resumo.meses_comparados
        labels_mes = self._labels_mes(meses, resumo.periodo_atual_chaves)
        ano_ant, ano_atu = resumo.ano_anterior, resumo.ano_atual
        x = list(range(len(meses)))
        cor = COR_TIPOLOGIA[tipologia]

        def volume(ano: int, mes: int) -> float:
            qtd = resumo.qtde_tipologia_mensal.get((ano, mes), {}).get(tipologia, Decimal(0))
            return float(qtd) / 1_000

        fmt_vol = lambda v: f"{v:,.0f}".replace(".", ",") + "K m²"

        valores_atu = [volume(ano_atu, m) for m in meses]

        fig, ax = plt.subplots(figsize=(8.6, 3.4))

        if resumo.comparar_ano_anterior:
            valores_ant = [volume(ano_ant, m) for m in meses]
            ax.plot(x, valores_ant, marker="o", markersize=5, linewidth=2.5, color="#B0B7C6", label=resumo.rotulo_anterior)
            ax.plot(x, valores_atu, marker="o", markersize=5, linewidth=2.5, color=cor, label=resumo.rotulo_atual)

            # Rotula todo ponto. Como as duas linhas ficam proximas e as vezes se cruzam,
            # decide o lado (acima/abaixo) ponto a ponto -- quem esta mais alto naquele
            # mes recebe o rotulo acima, quem esta mais baixo, abaixo. Isso evita que os
            # dois numeros colem quando as linhas quase se tocam.
            #
            # O texto agora inclui a unidade ("mil m²"), entao ficou mais largo -- quando
            # o proximo ponto sobe muito (rotulo acima) ou desce muito (rotulo abaixo), a
            # propria linha pode cortar o texto pela direita. Por isso desloca o rotulo
            # para a esquerda nesses casos, em vez de deixar sempre centralizado.
            def deslocamento(i: int, valores: list[float], acima: bool) -> tuple[int, str]:
                if i < len(valores) - 1:
                    proximo, atual_v = valores[i + 1], valores[i]
                    risco = (proximo > atual_v) if acima else (proximo < atual_v)
                    if risco:
                        return -6, "right"
                return 0, "center"

            for i in range(len(x)):
                v_ant, v_atu = valores_ant[i], valores_atu[i]
                if v_ant:
                    acima = v_ant >= v_atu
                    dx, ha = deslocamento(i, valores_ant, acima)
                    ax.annotate(fmt_vol(v_ant), (x[i], v_ant),
                                textcoords="offset points", xytext=(dx, 9 if acima else -15),
                                ha=ha, fontsize=8, color="#6B7280", fontweight="bold")
                if v_atu:
                    acima = v_atu > v_ant
                    dx, ha = deslocamento(i, valores_atu, acima)
                    ax.annotate(fmt_vol(v_atu), (x[i], v_atu),
                                textcoords="offset points", xytext=(dx, 9 if acima else -15),
                                ha=ha, fontsize=8, color=cor, fontweight="bold")
        else:
            ax.plot(x, valores_atu, marker="o", markersize=5, linewidth=2.5, color=cor, label=resumo.rotulo_atual)
            for i in range(len(x)):
                if valores_atu[i]:
                    dx, ha = (-6, "right") if (i < len(x) - 1 and valores_atu[i + 1] > valores_atu[i]) else (0, "center")
                    ax.annotate(fmt_vol(valores_atu[i]), (x[i], valores_atu[i]),
                                textcoords="offset points", xytext=(dx, 9),
                                ha=ha, fontsize=8, color=cor, fontweight="bold")

        ax.set_xticks(x)
        ax.set_xticklabels(labels_mes, fontsize=11)
        ax.spines[["top", "right", "left"]].set_visible(False)
        ax.yaxis.set_visible(False)
        ax.tick_params(axis="x", length=0)
        ax.margins(y=0.35)
        ax.legend(loc="upper left", frameon=False, ncols=2, fontsize=11)
        fig.tight_layout()
        return self._salvar(fig, transparente=True)
    def _faturamento_tipologia_slide(self, resumo: ResumoSellIn, tipologia: str) -> bytes:
        meses = resumo.meses_comparados
        labels_mes = self._labels_mes(meses, resumo.periodo_atual_chaves)
        ano_ant, ano_atu = resumo.ano_anterior, resumo.ano_atual
        x = list(range(len(meses)))
        cor = COR_TIPOLOGIA[tipologia]

        def faturamento(ano: int, mes: int) -> float:
            valor = resumo.faturamento_tipologia_mensal.get((ano, mes), {}).get(tipologia, Decimal(0))
            return float(valor) / 1_000

        valores_atu = [faturamento(ano_atu, m) for m in meses]

        fig, ax = plt.subplots(figsize=(8.6, 3.4))

        if resumo.comparar_ano_anterior:
            valores_ant = [faturamento(ano_ant, m) for m in meses]
            ax.plot(x, valores_ant, marker="o", markersize=5, linewidth=2.5, color="#B0B7C6", label=resumo.rotulo_anterior)
            ax.plot(x, valores_atu, marker="o", markersize=5, linewidth=2.5, color=cor, label=resumo.rotulo_atual)

            # O texto agora inclui a unidade ("mil" ou "mi"), entao ficou mais largo --
            # quando o proximo ponto sobe muito (rotulo acima) ou desce muito (rotulo
            # abaixo), a propria linha pode cortar o texto pela direita. Por isso
            # desloca o rotulo para a esquerda nesses casos.
            def deslocamento(i: int, valores: list[float], acima: bool) -> tuple[int, str]:
                if i < len(valores) - 1:
                    risco = (valores[i + 1] > valores[i]) if acima else (valores[i + 1] < valores[i])
                    if risco:
                        return -6, "right"
                return 0, "center"

            for i in range(len(x)):
                v_ant, v_atu = valores_ant[i], valores_atu[i]
                if v_ant:
                    acima = v_ant >= v_atu
                    dx, ha = deslocamento(i, valores_ant, acima)
                    ax.annotate(self._fmt_faturamento_dinamico(v_ant), (x[i], v_ant),
                                textcoords="offset points", xytext=(dx, 9 if acima else -15),
                                ha=ha, fontsize=8, color="#6B7280", fontweight="bold")
                if v_atu:
                    acima = v_atu > v_ant
                    dx, ha = deslocamento(i, valores_atu, acima)
                    ax.annotate(self._fmt_faturamento_dinamico(v_atu), (x[i], v_atu),
                                textcoords="offset points", xytext=(dx, 9 if acima else -15),
                                ha=ha, fontsize=8, color=cor, fontweight="bold")
        else:
            ax.plot(x, valores_atu, marker="o", markersize=5, linewidth=2.5, color=cor, label=resumo.rotulo_atual)
            for i in range(len(x)):
                if valores_atu[i]:
                    dx, ha = (-6, "right") if (i < len(x) - 1 and valores_atu[i + 1] > valores_atu[i]) else (0, "center")
                    ax.annotate(self._fmt_faturamento_dinamico(valores_atu[i]), (x[i], valores_atu[i]),
                                textcoords="offset points", xytext=(dx, 9),
                                ha=ha, fontsize=8, color=cor, fontweight="bold")

        ax.set_xticks(x)
        ax.set_xticklabels(labels_mes, fontsize=11)
        ax.spines[["top", "right", "left"]].set_visible(False)
        ax.yaxis.set_visible(False)
        ax.tick_params(axis="x", length=0)
        ax.margins(y=0.35)
        ax.legend(loc="upper left", frameon=False, ncols=2, fontsize=11)
        fig.tight_layout()
        return self._salvar(fig, transparente=True)

    def _participacao_tipologia_slide(self, resumo: ResumoSellIn, tipologia: str) -> bytes:
        meses = resumo.meses_comparados
        labels_mes = self._labels_mes(meses, resumo.periodo_atual_chaves)
        ano_ant, ano_atu = resumo.ano_anterior, resumo.ano_atual
        x = list(range(len(meses)))
        cor = COR_TIPOLOGIA[tipologia]

        def participacao(ano: int, mes: int) -> float:
            totais_mes = resumo.faturamento_tipologia_mensal.get((ano, mes), {})
            total_mes = sum(totais_mes.values()) or Decimal(1)
            return float(totais_mes.get(tipologia, Decimal(0)) / total_mes) * 100

        valores_atu = [participacao(ano_atu, m) for m in meses]

        fig, ax = plt.subplots(figsize=(8.6, 3.4))

        if resumo.comparar_ano_anterior:
            valores_ant = [participacao(ano_ant, m) for m in meses]
            ax.plot(x, valores_ant, marker="o", markersize=5, linewidth=2.5, color="#B0B7C6", label=resumo.rotulo_anterior)
            ax.plot(x, valores_atu, marker="o", markersize=5, linewidth=2.5, color=cor, label=resumo.rotulo_atual)

            for i in range(len(x)):
                v_ant, v_atu = valores_ant[i], valores_atu[i]
                acima_ant = v_ant >= v_atu
                ax.annotate(f"{v_ant:.0f}%", (x[i], v_ant),
                            textcoords="offset points", xytext=(0, 9 if acima_ant else -15),
                            ha="center", fontsize=8, color="#6B7280", fontweight="bold")
                acima_atu = v_atu > v_ant
                ax.annotate(f"{v_atu:.0f}%", (x[i], v_atu),
                            textcoords="offset points", xytext=(0, 9 if acima_atu else -15),
                            ha="center", fontsize=8, color=cor, fontweight="bold")
        else:
            ax.plot(x, valores_atu, marker="o", markersize=5, linewidth=2.5, color=cor, label=resumo.rotulo_atual)
            for i in range(len(x)):
                ax.annotate(f"{valores_atu[i]:.0f}%", (x[i], valores_atu[i]),
                            textcoords="offset points", xytext=(0, 9),
                            ha="center", fontsize=8, color=cor, fontweight="bold")

        ax.set_xticks(x)
        ax.set_xticklabels(labels_mes, fontsize=11)
        ax.spines[["top", "right", "left"]].set_visible(False)
        ax.yaxis.set_visible(False)
        ax.tick_params(axis="x", length=0)
        ax.margins(y=0.35)
        ax.legend(loc="upper left", frameon=False, ncols=2, fontsize=11)
        fig.tight_layout()
        return self._salvar(fig, transparente=True)

    def _volume_mensal_slide(self, resumo: ResumoSellIn) -> bytes:
        meses = resumo.meses_comparados
        labels_mes = self._labels_mes(meses, resumo.periodo_atual_chaves)
        ano_ant, ano_atu = resumo.ano_anterior, resumo.ano_atual
        x = list(range(len(meses)))

        fmt_vol = lambda v: f"{v:,.0f}".replace(".", ",")

        series = []
        if resumo.comparar_ano_anterior:
            valores_ant = [float(resumo.volume_mensal.get((ano_ant, m), Decimal(0))) / 1_000 for m in meses]
            series.append((resumo.rotulo_anterior, valores_ant, COR_ANO_ANTERIOR))
        valores_atu = [float(resumo.volume_mensal.get((ano_atu, m), Decimal(0))) / 1_000 for m in meses]
        series.append((resumo.rotulo_atual, valores_atu, COR_ANO_ATUAL))
        if resumo.outro_periodo is not None:
            media_outro = float(resumo.outro_periodo.volume_mensal_medio) / 1_000
            series.append((resumo.outro_periodo.label, [media_outro] * len(meses), COR_OUTRO_PERIODO))

        fig, ax = plt.subplots(figsize=(8.6, 3.6))
        self._desenhar_barras_agrupadas(ax, x, 0.7, series, fmt=fmt_vol, fontsize=9)
        ax.set_xticks(x)
        ax.set_xticklabels(labels_mes, fontsize=11)
        ax.spines[["top", "right", "left"]].set_visible(False)
        ax.yaxis.set_visible(False)
        ax.tick_params(axis="x", length=0)
        ax.margins(y=0.2)
        ax.legend(loc="upper left", frameon=False, ncols=min(len(series), 3), fontsize=10)
        fig.tight_layout()
        return self._salvar(fig, transparente=True)

    def _ticket_medio_geral_slide(self, resumo: ResumoSellIn) -> bytes:
        meses = resumo.meses_comparados
        labels_mes = self._labels_mes(meses, resumo.periodo_atual_chaves)
        ano_ant, ano_atu = resumo.ano_anterior, resumo.ano_atual
        x = list(range(len(meses)))

        def ticket_medio(ano: int, mes: int) -> float:
            fat = resumo.faturamento_mensal.get((ano, mes), Decimal(0))
            vol = resumo.volume_mensal.get((ano, mes), Decimal(0))
            return float(fat / vol) if vol else 0.0

        valores_atu = [ticket_medio(ano_atu, m) for m in meses]

        fig, ax = plt.subplots(figsize=(8.6, 3.4))

        if resumo.comparar_ano_anterior:
            valores_ant = [ticket_medio(ano_ant, m) for m in meses]
            ax.plot(x, valores_ant, marker="o", markersize=5, linewidth=2.5, color=COR_ANO_ANTERIOR, label=resumo.rotulo_anterior)
            ax.plot(x, valores_atu, marker="o", markersize=5, linewidth=2.5, color=COR_ANO_ATUAL, label=resumo.rotulo_atual)

            for i in range(len(x)):
                v_ant, v_atu = valores_ant[i], valores_atu[i]
                if v_ant:
                    acima = v_ant >= v_atu
                    ax.annotate(f"{v_ant:,.0f}".replace(".", ","), (x[i], v_ant),
                                textcoords="offset points", xytext=(0, 9 if acima else -15),
                                ha="center", fontsize=8, color="#6B7280", fontweight="bold")
                if v_atu:
                    acima = v_atu > v_ant
                    ax.annotate(f"{v_atu:,.0f}".replace(".", ","), (x[i], v_atu),
                                textcoords="offset points", xytext=(0, 9 if acima else -15),
                                ha="center", fontsize=8, color=COR_ANO_ATUAL, fontweight="bold")
        else:
            ax.plot(x, valores_atu, marker="o", markersize=5, linewidth=2.5, color=COR_ANO_ATUAL, label=resumo.rotulo_atual)
            for i in range(len(x)):
                if valores_atu[i]:
                    ax.annotate(f"{valores_atu[i]:,.0f}".replace(".", ","), (x[i], valores_atu[i]),
                                textcoords="offset points", xytext=(0, 9),
                                ha="center", fontsize=8, color=COR_ANO_ATUAL, fontweight="bold")

        ax.set_xticks(x)
        ax.set_xticklabels(labels_mes, fontsize=11)
        ax.spines[["top", "right", "left"]].set_visible(False)
        ax.yaxis.set_visible(False)
        ax.tick_params(axis="x", length=0)
        ax.margins(y=0.35)
        ax.legend(loc="upper left", frameon=False, ncols=2, fontsize=11)
        fig.tight_layout()
        return self._salvar(fig, transparente=True)

    def _crescimento_ticket_medio_slide(self, resumo: ResumoSellIn) -> bytes:
        meses = resumo.meses_comparados
        labels_mes = self._labels_mes(meses, resumo.periodo_atual_chaves)
        ano_ant, ano_atu = resumo.ano_anterior, resumo.ano_atual
        x = list(range(len(meses)))

        def ticket_medio(ano: int, mes: int) -> float:
            fat = resumo.faturamento_mensal.get((ano, mes), Decimal(0))
            vol = resumo.volume_mensal.get((ano, mes), Decimal(0))
            return float(fat / vol) if vol else 0.0

        # Baseline da comparacao: ano anterior, se ativo; senao, a media do outro
        # periodo (unico jeito de calcular "crescimento" sem um ano anterior); se
        # nenhuma das duas comparacoes estiver ativa, nao ha crescimento a mostrar.
        if resumo.comparar_ano_anterior:
            baseline = lambda m: ticket_medio(ano_ant, m)
        elif resumo.outro_periodo is not None:
            tm_outro = float(resumo.outro_periodo.ticket_medio)
            baseline = lambda m: tm_outro
        else:
            baseline = lambda m: 0.0

        crescimentos = []
        for m in meses:
            tm_base = baseline(m)
            tm_atu = ticket_medio(ano_atu, m)
            crescimentos.append(((tm_atu / tm_base) - 1) * 100 if tm_base else 0.0)

        cores = ["#4E9F63" if v >= 0 else "#C0392B" for v in crescimentos]

        fig, ax = plt.subplots(figsize=(8.6, 3.6))
        barras = ax.bar(x, crescimentos, color=cores, width=0.5)
        # bar_label nao aceita uma cor de texto diferente por barra -- como aqui as
        # cores (verde/vermelho) sao ambas escuras o bastante pro texto branco, a
        # checagem de contraste e' feita uma vez soh, em cima da primeira cor.
        ax.bar_label(barras, labels=[f"{v:+.0f}%".replace(".", ",") for v in crescimentos],
                     label_type="center", fontsize=9, color=self._cor_texto_sobre_fundo(cores[0]),
                     fontweight="bold")
        ax.axhline(0, color="#9CA3AF", linewidth=1)
        ax.set_xticks(x)
        ax.set_xticklabels(labels_mes, fontsize=11)
        ax.spines[["top", "right", "left"]].set_visible(False)
        ax.yaxis.set_visible(False)
        ax.tick_params(axis="x", length=0)
        ax.margins(y=0.3)
        fig.tight_layout()
        return self._salvar(fig, transparente=True)

    def _desempenho_tipologias_slide(self, resumo: ResumoSellIn) -> bytes:
        tipologias = ["Cerâmica", "Porcelanato", "Super Prime"]
        ano_ant, ano_atu = resumo.ano_anterior, resumo.ano_atual
        x = list(range(len(tipologias)))

        fmt_mi = lambda v: f"R$ {v:,.0f} mi".replace(",", "§").replace(".", ",").replace("§", ".")

        series = []
        if resumo.comparar_ano_anterior:
            valores_ant = [float(resumo.faturamento_por_tipologia.get(ano_ant, {}).get(t, Decimal(0))) / 1_000_000
                           for t in tipologias]
            series.append((resumo.rotulo_anterior, valores_ant, COR_ANO_ANTERIOR))
        valores_atu = [float(resumo.faturamento_por_tipologia.get(ano_atu, {}).get(t, Decimal(0))) / 1_000_000
                       for t in tipologias]
        series.append((resumo.rotulo_atual, valores_atu, COR_ANO_ATUAL))
        if resumo.outro_periodo is not None:
            valores_outro = [float(resumo.outro_periodo.faturamento_por_tipologia.get(t, Decimal(0))) / 1_000_000
                              for t in tipologias]
            series.append((resumo.outro_periodo.label, valores_outro, COR_OUTRO_PERIODO))

        fig, ax = plt.subplots(figsize=(8.6, 4.0))
        self._desenhar_barras_agrupadas(ax, x, 0.7, series, fmt=fmt_mi, fontsize=9 if len(series) <= 2 else 8)
        ax.set_xticks(x)
        ax.set_xticklabels(tipologias, fontsize=12)
        ax.spines[["top", "right", "left"]].set_visible(False)
        ax.yaxis.set_visible(False)
        ax.tick_params(axis="x", length=0)
        ax.margins(y=0.2)
        ax.legend(loc="upper right", frameon=False, ncols=min(len(series), 3), fontsize=10)
        fig.tight_layout()
        return self._salvar(fig, transparente=True)

    def _tipologias_juntas_slide(self, resumo: ResumoSellIn, metrica: str) -> bytes:
        """Grafico de linhas com as 3 tipologias juntas, cada uma com 2 linhas (ano
        anterior tracejado/claro, ano atual solido) -- a cor identifica a tipologia,
        o traco identifica o ano. metrica: 'ticket_medio' (R$/m²), 'volume' (mil m²)
        ou 'faturamento' (R$ mil)."""
        tipologias = ["Cerâmica", "Porcelanato", "Super Prime"]
        meses = resumo.meses_comparados
        labels_mes = self._labels_mes(meses, resumo.periodo_atual_chaves)
        ano_ant, ano_atu = resumo.ano_anterior, resumo.ano_atual
        x = list(range(len(meses)))

        def valor(tipologia: str, ano: int, mes: int) -> float:
            if metrica == "volume":
                qtd = resumo.qtde_tipologia_mensal.get((ano, mes), {}).get(tipologia, Decimal(0))
                return float(qtd) / 1_000
            fat = resumo.faturamento_tipologia_mensal.get((ano, mes), {}).get(tipologia, Decimal(0))
            if metrica == "ticket_medio":
                qtd = resumo.qtde_tipologia_mensal.get((ano, mes), {}).get(tipologia, Decimal(0))
                return float(fat / qtd) if qtd else 0.0
            return float(fat) / 1_000

        if metrica == "volume":
            fmt = lambda v: f"{v:,.0f}".replace(".", ",") + "K m²"
        elif metrica == "ticket_medio":
            fmt = lambda v: f"{v:,.0f}".replace(".", ",")
        else:
            fmt = self._fmt_faturamento_dinamico

        valores_atu_por_tipologia = {t: [valor(t, ano_atu, m) for m in meses] for t in tipologias}
        valores_ant_por_tipologia = (
            {t: [valor(t, ano_ant, m) for m in meses] for t in tipologias}
            if resumo.comparar_ano_anterior else {}
        )

        fig, ax = plt.subplots(figsize=(8.6, 3.9))
        for tipologia in tipologias:
            cor = COR_TIPOLOGIA[tipologia]
            if resumo.comparar_ano_anterior:
                ax.plot(x, valores_ant_por_tipologia[tipologia], marker="o", markersize=4, linewidth=2,
                        linestyle="--", color=cor, alpha=0.55, label=f"{tipologia} {resumo.rotulo_anterior}")
            ax.plot(x, valores_atu_por_tipologia[tipologia], marker="o", markersize=4, linewidth=2.3,
                    color=cor, label=f"{tipologia} {resumo.rotulo_atual}")

        ax.margins(y=0.35)
        ax.set_xticks(x)
        ax.set_xticklabels(labels_mes, fontsize=11)
        ax.spines[["top", "right", "left"]].set_visible(False)
        ax.yaxis.set_visible(False)
        ax.tick_params(axis="x", length=0)
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.14), ncols=3, frameon=False, fontsize=8)
        fig.tight_layout()
        # So depois do layout final (tight_layout pode alterar a area do grafico e,
        # com isso, a escala pixel-por-valor) e que da pra medir com precisao onde
        # cada ponto cai na tela para decidir se dois rotulos vao colidir.
        ax.figure.canvas.draw()

        def anotar_grupo(valores_por_tipologia: dict, deslocamento_base: int, **kwargs_extra):
            """Anota os pontos de um grupo (ano atual ou ano anterior). O problema mais
            comum aqui nao e um rotulo colidir com o rotulo vizinho, e sim o MARCADOR
            de uma tipologia com valor mais alto (ou mais baixo) ficar bem em cima de
            onde o rotulo da tipologia vizinha cairia -- ja que o offset padrao (acima
            para o ano atual, abaixo para o ano anterior) e pequeno. Por isso, quando o
            ponto vizinho na direcao do offset padrao esta perto demais NA TELA (em
            pixels, nao so em valor bruto), o rotulo e colocado do lado oposto da linha
            em vez de tentar empurra-lo ainda mais para longe."""
            sinal = 1 if deslocamento_base > 0 else -1
            magnitude = abs(deslocamento_base)
            for xi in x:
                pontos = [(t, valores_por_tipologia[t][xi]) for t in tipologias if valores_por_tipologia[t][xi]]
                pontos_px = [(t, v, ax.transData.transform((xi, v))[1]) for t, v in pontos]
                pontos_px.sort(key=lambda item: item[2])
                n = len(pontos_px)
                for idx, (tipologia, v, py) in enumerate(pontos_px):
                    direcao = sinal
                    vizinho_idx = idx + 1 if sinal > 0 else idx - 1
                    if 0 <= vizinho_idx < n:
                        py_vizinho = pontos_px[vizinho_idx][2]
                        if abs(py_vizinho - py) < 22:
                            direcao = -sinal
                    offset_y = direcao * magnitude
                    ax.annotate(fmt(v), (xi, v), textcoords="offset points", xytext=(0, offset_y),
                                ha="center", fontsize=7, color=COR_TIPOLOGIA[tipologia], **kwargs_extra)

        anotar_grupo(valores_atu_por_tipologia, 7, fontweight="bold")
        if resumo.comparar_ano_anterior:
            anotar_grupo(valores_ant_por_tipologia, -13, alpha=0.8)

        return self._salvar(fig, transparente=True)

    # --------------------------------------- bloco 3: periodo livre x periodo livre
    #
    # Os graficos abaixo comparam DOIS periodos escolhidos pelo usuario (que podem
    # ter quantidades de meses diferentes, ex: Jan-Mar/2026 vs Mar-Jul/2025). Como os
    # periodos nao tem necessariamente o mesmo numero de meses, nao da pra desenhar
    # um grafico de linha mes a mes -- por isso essa comparacao e sempre feita em
    # cima de TOTAIS (2 barras: periodo 1 x periodo 2), igual a logica ja usada para
    # o "outro_periodo" (OutroPeriodoTotais) em outros pontos deste arquivo.

    def _grafico_periodo_duas_barras(self, periodo1: OutroPeriodoTotais, periodo2: OutroPeriodoTotais,
                                      valor1: float, valor2: float, cor: str, fmt, figsize=(8.6, 3.9)) -> bytes:
        """Grafico simples de 2 barras comparando o total do periodo 1 com o total do
        periodo 2. A barra do periodo 2 usa a mesma cor com menos opacidade, seguindo
        a mesma logica visual ja usada nos graficos de linha (atual = solido/forte,
        comparacao = mais claro). Os valores ficam DENTRO de cada barra, com a cor do
        texto calculada em cima da cor efetiva de cada barra (considerando a opacidade
        reduzida da segunda, que fica visualmente mais clara)."""
        fig, ax = plt.subplots(figsize=figsize)
        x = [0, 1]
        valores = [valor1, valor2]
        alphas = [1.0, 0.5]
        barras = ax.bar(x, valores, width=0.45, color=cor)
        barras.patches[1].set_alpha(0.5)
        for xi, valor, alpha in zip(x, valores, alphas):
            cor_efetiva = self._blend_com_branco(cor, alpha)
            ax.text(xi, valor / 2, fmt(valor), ha="center", va="center", fontsize=12,
                    color=self._cor_texto_sobre_fundo(cor_efetiva), fontweight="bold")
        ax.set_xticks(x)
        ax.set_xticklabels([periodo1.label, periodo2.label], fontsize=10)
        ax.spines[["top", "right", "left"]].set_visible(False)
        ax.yaxis.set_visible(False)
        ax.tick_params(axis="x", length=0)
        ax.margins(y=0.25)
        fig.tight_layout()
        return self._salvar(fig, transparente=True)

    def gerar_graficos_periodo_ticket_medio(self, periodo1: OutroPeriodoTotais,
                                             periodo2: OutroPeriodoTotais) -> dict[str, bytes]:
        """Preco por m² (R$/m²), periodo 1 x periodo 2, um grafico por tipologia."""
        plt.rcParams["font.family"] = "sans-serif"
        plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial"]

        chaves_arquivo = {
            "Cerâmica": "periodo_ticket_medio_ceramica.png",
            "Porcelanato": "periodo_ticket_medio_porcelanato.png",
            "Super Prime": "periodo_ticket_medio_super_prime.png",
        }

        def ticket_medio(periodo: OutroPeriodoTotais, tipologia: str) -> float:
            fat = periodo.faturamento_por_tipologia.get(tipologia, Decimal(0))
            vol = periodo.qtde_por_tipologia.get(tipologia, Decimal(0))
            return float(fat / vol) if vol else 0.0

        fmt = lambda v: f"{v:,.0f}".replace(".", ",")
        return {
            chave: self._grafico_periodo_duas_barras(
                periodo1, periodo2, ticket_medio(periodo1, tipologia), ticket_medio(periodo2, tipologia),
                COR_TIPOLOGIA[tipologia], fmt, figsize=(4.3, 4.1),
            )
            for tipologia, chave in chaves_arquivo.items()
        }

    def gerar_graficos_periodo_volume(self, periodo1: OutroPeriodoTotais,
                                       periodo2: OutroPeriodoTotais) -> dict[str, bytes]:
        """Volume vendido (mil m²), periodo 1 x periodo 2, um grafico por tipologia."""
        plt.rcParams["font.family"] = "sans-serif"
        plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial"]

        chaves_arquivo = {
            "Cerâmica": "periodo_volume_ceramica.png",
            "Porcelanato": "periodo_volume_porcelanato.png",
            "Super Prime": "periodo_volume_super_prime.png",
        }
        fmt = lambda v: f"{v:,.0f}".replace(".", ",")
        return {
            chave: self._grafico_periodo_duas_barras(
                periodo1, periodo2,
                float(periodo1.qtde_por_tipologia.get(tipologia, Decimal(0))) / 1_000,
                float(periodo2.qtde_por_tipologia.get(tipologia, Decimal(0))) / 1_000,
                COR_TIPOLOGIA[tipologia], fmt, figsize=(4.3, 4.1),
            )
            for tipologia, chave in chaves_arquivo.items()
        }

    def gerar_graficos_periodo_faturamento(self, periodo1: OutroPeriodoTotais,
                                            periodo2: OutroPeriodoTotais) -> dict[str, bytes]:
        """Faturamento (R$ mil), periodo 1 x periodo 2, um grafico por tipologia."""
        plt.rcParams["font.family"] = "sans-serif"
        plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial"]

        chaves_arquivo = {
            "Cerâmica": "periodo_faturamento_ceramica.png",
            "Porcelanato": "periodo_faturamento_porcelanato.png",
            "Super Prime": "periodo_faturamento_super_prime.png",
        }
        return {
            chave: self._grafico_periodo_duas_barras(
                periodo1, periodo2,
                float(periodo1.faturamento_por_tipologia.get(tipologia, Decimal(0))) / 1_000,
                float(periodo2.faturamento_por_tipologia.get(tipologia, Decimal(0))) / 1_000,
                COR_TIPOLOGIA[tipologia], self._fmt_faturamento_dinamico, figsize=(8.6, 3.9),
            )
            for tipologia, chave in chaves_arquivo.items()
        }

    def _grafico_periodo_tipologias_juntas(self, periodo1: OutroPeriodoTotais, periodo2: OutroPeriodoTotais,
                                            valores1: list[float], valores2: list[float], fmt,
                                            figsize=(4.3, 4.1)) -> bytes:
        """Barras agrupadas por tipologia (3 categorias), 2 series: periodo 1 (cor
        forte) e periodo 2 (cor mais clara/dourada) -- mesma paleta ja usada para
        'outro periodo' em outros graficos deste arquivo."""
        tipologias = ["Cerâmica", "Porcelanato", "Super Prime"]
        series = [(periodo1.label, valores1, COR_ANO_ATUAL), (periodo2.label, valores2, COR_OUTRO_PERIODO)]

        fig, ax = plt.subplots(figsize=figsize)
        x = list(range(len(tipologias)))
        self._desenhar_barras_agrupadas(ax, x, 0.7, series, fmt=fmt, fontsize=8)
        ax.set_xticks(x)
        ax.set_xticklabels(tipologias, fontsize=9)
        ax.spines[["top", "right", "left"]].set_visible(False)
        ax.yaxis.set_visible(False)
        ax.tick_params(axis="x", length=0)
        ax.margins(y=0.25)
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.16), ncols=2, frameon=False, fontsize=8)
        fig.tight_layout()
        return self._salvar(fig, transparente=True)

    def gerar_grafico_periodo_ticket_medio_tipologias_juntas(self, periodo1: OutroPeriodoTotais,
                                                               periodo2: OutroPeriodoTotais) -> bytes:
        plt.rcParams["font.family"] = "sans-serif"
        plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial"]
        tipologias = ["Cerâmica", "Porcelanato", "Super Prime"]

        def ticket_medio(periodo: OutroPeriodoTotais, tipologia: str) -> float:
            fat = periodo.faturamento_por_tipologia.get(tipologia, Decimal(0))
            vol = periodo.qtde_por_tipologia.get(tipologia, Decimal(0))
            return float(fat / vol) if vol else 0.0

        valores1 = [ticket_medio(periodo1, t) for t in tipologias]
        valores2 = [ticket_medio(periodo2, t) for t in tipologias]
        fmt = lambda v: f"{v:,.0f}".replace(".", ",")
        return self._grafico_periodo_tipologias_juntas(periodo1, periodo2, valores1, valores2, fmt,
                                                         figsize=(4.3, 4.1))

    def gerar_grafico_periodo_volume_tipologias_juntas(self, periodo1: OutroPeriodoTotais,
                                                         periodo2: OutroPeriodoTotais) -> bytes:
        plt.rcParams["font.family"] = "sans-serif"
        plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial"]
        tipologias = ["Cerâmica", "Porcelanato", "Super Prime"]

        valores1 = [float(periodo1.qtde_por_tipologia.get(t, Decimal(0))) / 1_000 for t in tipologias]
        valores2 = [float(periodo2.qtde_por_tipologia.get(t, Decimal(0))) / 1_000 for t in tipologias]
        fmt = lambda v: f"{v:,.0f}".replace(".", ",")
        return self._grafico_periodo_tipologias_juntas(periodo1, periodo2, valores1, valores2, fmt,
                                                         figsize=(4.3, 4.1))

    def gerar_grafico_periodo_faturamento_tipologias_juntas(self, periodo1: OutroPeriodoTotais,
                                                              periodo2: OutroPeriodoTotais) -> bytes:
        plt.rcParams["font.family"] = "sans-serif"
        plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial"]
        tipologias = ["Cerâmica", "Porcelanato", "Super Prime"]

        valores1 = [float(periodo1.faturamento_por_tipologia.get(t, Decimal(0))) / 1_000 for t in tipologias]
        valores2 = [float(periodo2.faturamento_por_tipologia.get(t, Decimal(0))) / 1_000 for t in tipologias]
        return self._grafico_periodo_tipologias_juntas(periodo1, periodo2, valores1, valores2,
                                                         self._fmt_faturamento_dinamico, figsize=(8.6, 4.1))

    def gerar_grafico_periodo_proporcao_volume(self, periodo1: OutroPeriodoTotais,
                                                periodo2: OutroPeriodoTotais) -> bytes:
        plt.rcParams["font.family"] = "sans-serif"
        plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial"]
        linhas = [(periodo1.label, periodo1.qtde_por_tipologia), (periodo2.label, periodo2.qtde_por_tipologia)]
        return self._barra_empilhada_proporcao(linhas)

    def gerar_grafico_periodo_proporcao_faturamento(self, periodo1: OutroPeriodoTotais,
                                                     periodo2: OutroPeriodoTotais) -> bytes:
        plt.rcParams["font.family"] = "sans-serif"
        plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial"]
        linhas = [(periodo1.label, periodo1.faturamento_por_tipologia),
                  (periodo2.label, periodo2.faturamento_por_tipologia)]
        return self._barra_empilhada_proporcao(linhas)

    def _periodo_formatos_tipologia_slide(self, periodo1: OutroPeriodoTotais, periodo2: OutroPeriodoTotais,
                                           tipologia: str, atributo: str) -> bytes:
        """Estudo de formatos, versao periodo 1 x periodo 2 (bloco 3) -- mesma ideia
        de _formatos_tipologia_slide, so que as duas linhas sao os dois periodos
        livres em vez de ano atual/anterior. atributo: 'qtde_por_formato' (volume)
        ou 'faturamento_por_formato'."""
        linhas = [
            (periodo1.label, getattr(periodo1, atributo).get(tipologia, {})),
            (periodo2.label, getattr(periodo2, atributo).get(tipologia, {})),
        ]
        formatos = FORMATOS_POR_TIPOLOGIA[tipologia]
        cores = dict(zip(formatos, self._paleta_distinta_formatos(len(formatos))))
        return self._barra_empilhada_proporcao(linhas, categorias=formatos, cores=cores,
                                                mostrar_legenda=True, largura_fig=8.6)

    def gerar_grafico_periodo_formatos_tipologia_volume(self, periodo1: OutroPeriodoTotais,
                                                          periodo2: OutroPeriodoTotais, tipologia: str) -> bytes:
        plt.rcParams["font.family"] = "sans-serif"
        plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial"]
        return self._periodo_formatos_tipologia_slide(periodo1, periodo2, tipologia, "qtde_por_formato")

    def gerar_grafico_periodo_formatos_tipologia_faturamento(self, periodo1: OutroPeriodoTotais,
                                                               periodo2: OutroPeriodoTotais, tipologia: str) -> bytes:
        plt.rcParams["font.family"] = "sans-serif"
        plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial"]
        return self._periodo_formatos_tipologia_slide(periodo1, periodo2, tipologia, "faturamento_por_formato")

    # ------------------------------------------------------- ranking de clientes

    def _truncar_cliente(self, nome: str, limite: int = 26) -> str:
        """Trunca o nome do cliente pra nao estourar o espaco do eixo (razao social
        pode ser bem longa) -- essa versao truncada e' so pra exibicao no grafico, o
        agrupamento/ranking em si continua usando o nome inteiro."""
        nome = (nome or "").strip()
        return nome if len(nome) <= limite else nome[: limite - 1].rstrip() + "…"

    def _ranking_clientes_slide(self, series: list[tuple[str, dict, str]]) -> bytes:
        """Ranking horizontal com o Top 10 clientes por faturamento. 'series' e' uma
        lista de (rotulo, {cliente: valor em R$}, cor) com 1 serie (Bloco 1, sem
        comparacao) ou 2 series (Bloco 2: ano atual x anterior; Bloco 3: periodo 1 x
        periodo 2). O Top 10 e a ordem do ranking sao sempre definidos pela PRIMEIRA
        serie da lista (o periodo/ano principal) -- a segunda serie so mostra, pra
        esses mesmos 10 clientes, o valor no periodo de comparacao (que pode ser 0 se
        o cliente nao aparece nesse outro periodo)."""
        _, valores_principal, _ = series[0]
        top10 = sorted(valores_principal.items(), key=lambda kv: kv[1], reverse=True)[:10]
        clientes = [c for c, _ in top10]
        # #1 no topo do grafico -- barh empilha de baixo pra cima, entao inverte a
        # ordem de plotagem (mantendo o rotulo do eixo com o nome de cada um).
        clientes_exibicao = list(reversed(clientes))
        y = list(range(len(clientes_exibicao)))

        n = len(series)
        altura_categoria = 0.7
        altura_barra = altura_categoria / n
        deslocamentos = [(-((n - 1) / 2) + i) * altura_barra for i in range(n)]

        fig, ax = plt.subplots(figsize=(8.6, 0.68 * len(clientes_exibicao) + 1.3))
        for (rotulo, valores, cor), deslocamento in zip(series, deslocamentos):
            alturas = [float(valores.get(c, Decimal(0))) / 1000 for c in clientes_exibicao]
            y_pos = [yi + deslocamento for yi in y]
            barras = ax.barh(y_pos, alturas, height=altura_barra * 0.85, color=cor, label=rotulo)
            # Pedido explicito do usuario: preto sempre, mesmo em cima da barra azul-
            # marinho escura -- o contorno branco ao redor do texto garante que ele
            # continue legivel nesse caso (sem o contorno, preto em cima de azul
            # escuro quase some).
            ax.bar_label(barras, labels=[self._fmt_faturamento_dinamico(v) for v in alturas],
                          label_type="center", color="black", fontsize=11, fontweight="bold",
                          path_effects=[patheffects.withStroke(linewidth=3, foreground="white")])

        ax.set_yticks(y)
        ax.set_yticklabels([self._truncar_cliente(c) for c in clientes_exibicao], fontsize=10)
        ax.xaxis.set_visible(False)
        ax.spines[["top", "right", "bottom"]].set_visible(False)
        ax.tick_params(axis="y", length=0)
        ax.margins(x=0.15, y=0.03)
        if n > 1:
            ax.legend(loc="lower right", frameon=False, fontsize=9)
        fig.tight_layout()
        return self._salvar(fig, transparente=True)

    def gerar_grafico_ranking_clientes(self, resumo: ResumoSellIn) -> bytes:
        """Top 10 clientes por faturamento -- 1 barra por cliente no modo absoluto
        (Bloco 1), 2 barras (ano atual x anterior) quando ha comparacao ano a ano
        (Bloco 2)."""
        plt.rcParams["font.family"] = "sans-serif"
        plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial"]
        series = [(resumo.rotulo_atual, resumo.faturamento_por_cliente.get(resumo.ano_atual, {}), COR_ANO_ATUAL)]
        if resumo.comparar_ano_anterior:
            series.append(
                (resumo.rotulo_anterior, resumo.faturamento_por_cliente.get(resumo.ano_anterior, {}), COR_ANO_ANTERIOR)
            )
        return self._ranking_clientes_slide(series)

    def gerar_grafico_periodo_ranking_clientes(self, periodo1: OutroPeriodoTotais,
                                                periodo2: OutroPeriodoTotais) -> bytes:
        """Top 10 clientes por faturamento no periodo 1, comparado com o periodo 2
        (Bloco 3)."""
        plt.rcParams["font.family"] = "sans-serif"
        plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial"]
        series = [
            (periodo1.label, periodo1.faturamento_por_cliente, COR_ANO_ATUAL),
            (periodo2.label, periodo2.faturamento_por_cliente, COR_OUTRO_PERIODO),
        ]
        return self._ranking_clientes_slide(series)
