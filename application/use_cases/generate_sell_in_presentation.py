from dataclasses import dataclass, replace
from datetime import date

from domain.ports.chart_generator import ChartGenerator
from domain.ports.presentation_builder import PresentationBuilder
from domain.ports.sell_in_reader import SellInReader
from domain.value_objects.periodo_comparativo_insights import montar_insights_comparativo_periodos
from domain.value_objects.sell_in_aggregation import montar_resumo, montar_resumo_periodo, montar_totais_periodo
from domain.value_objects.sell_in_insights import montar_insights

TIPOLOGIAS = ("Cerâmica", "Porcelanato", "Super Prime")
SUFIXO_TIPOLOGIA = {"Cerâmica": "ceramica", "Porcelanato": "porcelanato", "Super Prime": "super_prime"}


@dataclass
class GenerateSellInPresentationResult:
    ok: bool
    message: str
    apresentacao: bytes | None = None
    dimensoes_nao_mapeadas: dict[str, int] | None = None


class GenerateSellInPresentation:
    def __init__(self, sell_in_reader: SellInReader, chart_generator: ChartGenerator,
                 presentation_builder: PresentationBuilder):
        self.sell_in_reader = sell_in_reader
        self.chart_generator = chart_generator
        self.presentation_builder = presentation_builder

    def execute(self, file_content: bytes, data_inicial: date | None = None,
                data_final: date | None = None, data_inicial_2: date | None = None,
                data_final_2: date | None = None) -> GenerateSellInPresentationResult:
        """Gera a apresentacao a partir de UM periodo principal informado pelo usuario
        (data_inicial / data_final). A apresentacao sempre traz 2 blocos: um so com o
        periodo selecionado (sem comparacao) e outro comparando esse periodo com o mesmo
        periodo do ano anterior -- nao ha mais toggles, os dois blocos sempre aparecem.

        Se um SEGUNDO periodo livre tambem for informado (data_inicial_2 / data_final_2),
        um 3o bloco e adicionado ao final comparando o periodo 1 com o periodo 2 -- os
        dois podem ter quantidades de meses diferentes (ex: 3 meses vs 5 meses), ja que
        essa comparacao e feita em cima de totais, nao mes a mes."""
        registros = self.sell_in_reader.read(file_content)
        if not registros:
            return GenerateSellInPresentationResult(ok=False, message="Nenhum dado válido encontrado no arquivo.")

        if data_inicial is not None or data_final is not None:
            if data_inicial is None or data_final is None:
                return GenerateSellInPresentationResult(
                    ok=False, message="Informe data_inicial e data_final juntas para escolher o período."
                )
            try:
                resumo = montar_resumo_periodo(registros, data_inicial, data_final)
            except ValueError as erro:
                return GenerateSellInPresentationResult(ok=False, message=str(erro))
        else:
            resumo = montar_resumo(registros)

        # Duas "visoes" do mesmo resumo ja agregado: uma so com o periodo atual (bloco
        # absoluto, slides 1-10) e outra com a comparacao ano a ano (bloco comparativo,
        # slides 11-20). Nao precisa reagregar nada -- so troca a flag que controla o
        # que cada grafico/slide vai de fato desenhar/mostrar.
        resumo_absoluto = replace(resumo, comparar_ano_anterior=False)
        resumo_comparativo = replace(resumo, comparar_ano_anterior=True)

        insights_absoluto = montar_insights(resumo_absoluto)
        insights_comparativo = montar_insights(resumo_comparativo)

        graficos: dict[str, bytes] = {}
        for chave, dados in self.chart_generator.gerar_graficos_ticket_medio(resumo_absoluto).items():
            graficos[f"abs_{chave}"] = dados
        for chave, dados in self.chart_generator.gerar_graficos_faturamento_tipologia(resumo_absoluto).items():
            graficos[f"abs_{chave}"] = dados
        graficos_slide_absoluto = self.chart_generator.gerar_graficos_slide(resumo_absoluto)
        graficos["abs_tipologia_mensal.png"] = graficos_slide_absoluto["tipologia_mensal.png"]
        graficos["abs_representatividade.png"] = graficos_slide_absoluto["representatividade.png"]
        graficos["abs_representatividade_volume.png"] = \
            self.chart_generator.gerar_grafico_representatividade_volume(resumo_absoluto)
        graficos["abs_ticket_medio_tipologias.png"] = \
            self.chart_generator.gerar_grafico_ticket_medio_tipologias(resumo_absoluto)
        graficos["abs_faturamento_tipologias.png"] = \
            self.chart_generator.gerar_grafico_faturamento_tipologias(resumo_absoluto)
        for tipologia in TIPOLOGIAS:
            sufixo = SUFIXO_TIPOLOGIA[tipologia]
            graficos[f"abs_formatos_{sufixo}_volume.png"] = \
                self.chart_generator.gerar_grafico_formatos_tipologia_volume(resumo_absoluto, tipologia)
        graficos["abs_ranking_clientes.png"] = self.chart_generator.gerar_grafico_ranking_clientes(resumo_absoluto)
        # Slide "Participação por Tipologia" (ex-"M² todas as tipologias juntas") passou
        # a mostrar % de participação por tipologia -- reaproveita o mesmo grafico de
        # barra empilhada ja usado no Bloco 2, so que faltava gerar essa versao "abs".
        graficos["abs_representatividade_volume.png"] = \
            self.chart_generator.gerar_grafico_representatividade_volume(resumo_absoluto)
        # Slide "Proporção por Tipologia" virou 2 pizzas lado a lado (m² e faturamento).
        graficos["abs_pizza_volume.png"] = self.chart_generator.gerar_grafico_pizza_tipologia(
            resumo_absoluto.qtde_por_tipologia.get(resumo_absoluto.ano_atual, {}))
        graficos["abs_pizza_faturamento.png"] = self.chart_generator.gerar_grafico_pizza_tipologia(
            resumo_absoluto.faturamento_por_tipologia.get(resumo_absoluto.ano_atual, {}))
        # Slide "Análise por Tipologia" ganhou um 2º gráfico com o crescimento mês a mês.
        graficos["abs_crescimento_tipologia_mensal.png"] = \
            self.chart_generator.gerar_grafico_crescimento_tipologia_mensal(resumo_absoluto)

        for chave, dados in self.chart_generator.gerar_graficos_ticket_medio(resumo_comparativo).items():
            graficos[f"cmp_{chave}"] = dados
        for chave, dados in self.chart_generator.gerar_graficos_faturamento_tipologia(resumo_comparativo).items():
            graficos[f"cmp_{chave}"] = dados
        graficos_slide_comparativo = self.chart_generator.gerar_graficos_slide(resumo_comparativo)
        graficos["cmp_representatividade.png"] = graficos_slide_comparativo["representatividade.png"]
        graficos["cmp_representatividade_volume.png"] = \
            self.chart_generator.gerar_grafico_representatividade_volume(resumo_comparativo)
        for tipologia in TIPOLOGIAS:
            sufixo = SUFIXO_TIPOLOGIA[tipologia]
            graficos[f"cmp_formatos_{sufixo}_volume.png"] = \
                self.chart_generator.gerar_grafico_formatos_tipologia_volume(resumo_comparativo, tipologia)
        graficos["cmp_ranking_clientes.png"] = self.chart_generator.gerar_grafico_ranking_clientes(resumo_comparativo)
        # Slides "Proporção por Tipologia" (Bloco 2) viraram 2 pizzas por metrica: ano
        # anterior x ano atual (em vez de 1 barra empilhada com as 2 barras juntas).
        graficos["cmp_pizza_volume_anterior.png"] = self.chart_generator.gerar_grafico_pizza_tipologia(
            resumo_comparativo.qtde_por_tipologia.get(resumo_comparativo.ano_anterior, {}))
        graficos["cmp_pizza_volume_atual.png"] = self.chart_generator.gerar_grafico_pizza_tipologia(
            resumo_comparativo.qtde_por_tipologia.get(resumo_comparativo.ano_atual, {}))
        graficos["cmp_pizza_faturamento_anterior.png"] = self.chart_generator.gerar_grafico_pizza_tipologia(
            resumo_comparativo.faturamento_por_tipologia.get(resumo_comparativo.ano_anterior, {}))
        graficos["cmp_pizza_faturamento_atual.png"] = self.chart_generator.gerar_grafico_pizza_tipologia(
            resumo_comparativo.faturamento_por_tipologia.get(resumo_comparativo.ano_atual, {}))

        insights_periodos = None
        if data_inicial_2 is not None or data_final_2 is not None:
            if data_inicial_2 is None or data_final_2 is None:
                return GenerateSellInPresentationResult(
                    ok=False, message="Informe o início e o fim do segundo período juntos."
                )
            if data_inicial is None or data_final is None:
                return GenerateSellInPresentationResult(
                    ok=False,
                    message="Para comparar com um segundo período, informe também o período 1 "
                            "(data_inicial e data_final).",
                )
            try:
                periodo1_totais = montar_totais_periodo(registros, data_inicial, data_final)
                periodo2_totais = montar_totais_periodo(registros, data_inicial_2, data_final_2)
            except ValueError as erro:
                return GenerateSellInPresentationResult(ok=False, message=str(erro))

            insights_periodos = montar_insights_comparativo_periodos(periodo1_totais, periodo2_totais)

            graficos.update(self.chart_generator.gerar_graficos_periodo_ticket_medio(periodo1_totais, periodo2_totais))
            graficos.update(self.chart_generator.gerar_graficos_periodo_volume(periodo1_totais, periodo2_totais))
            graficos.update(self.chart_generator.gerar_graficos_periodo_faturamento(periodo1_totais, periodo2_totais))
            graficos["periodo_ticket_medio_tipologias.png"] = \
                self.chart_generator.gerar_grafico_periodo_ticket_medio_tipologias_juntas(
                    periodo1_totais, periodo2_totais)
            graficos["periodo_volume_tipologias.png"] = \
                self.chart_generator.gerar_grafico_periodo_volume_tipologias_juntas(periodo1_totais, periodo2_totais)
            graficos["periodo_faturamento_tipologias.png"] = \
                self.chart_generator.gerar_grafico_periodo_faturamento_tipologias_juntas(
                    periodo1_totais, periodo2_totais)
            graficos["periodo_proporcao_volume.png"] = \
                self.chart_generator.gerar_grafico_periodo_proporcao_volume(periodo1_totais, periodo2_totais)
            graficos["periodo_proporcao_faturamento.png"] = \
                self.chart_generator.gerar_grafico_periodo_proporcao_faturamento(periodo1_totais, periodo2_totais)
            for tipologia in TIPOLOGIAS:
                sufixo = SUFIXO_TIPOLOGIA[tipologia]
                graficos[f"periodo_formatos_{sufixo}_volume.png"] = \
                    self.chart_generator.gerar_grafico_periodo_formatos_tipologia_volume(
                        periodo1_totais, periodo2_totais, tipologia)
            graficos["periodo_ranking_clientes.png"] = \
                self.chart_generator.gerar_grafico_periodo_ranking_clientes(periodo1_totais, periodo2_totais)
            # Slides "Proporção por Tipologia" (Bloco 3) viraram 2 pizzas por metrica:
            # período 1 x período 2.
            graficos["periodo_pizza_volume_p1.png"] = \
                self.chart_generator.gerar_grafico_pizza_tipologia(periodo1_totais.qtde_por_tipologia)
            graficos["periodo_pizza_volume_p2.png"] = \
                self.chart_generator.gerar_grafico_pizza_tipologia(periodo2_totais.qtde_por_tipologia)
            graficos["periodo_pizza_faturamento_p1.png"] = \
                self.chart_generator.gerar_grafico_pizza_tipologia(periodo1_totais.faturamento_por_tipologia)
            graficos["periodo_pizza_faturamento_p2.png"] = \
                self.chart_generator.gerar_grafico_pizza_tipologia(periodo2_totais.faturamento_por_tipologia)

        apresentacao = self.presentation_builder.montar_apresentacao(
            insights_absoluto, insights_comparativo, graficos, insights_periodos=insights_periodos
        )

        return GenerateSellInPresentationResult(
            ok=True,
            message="Apresentação gerada com sucesso.",
            apresentacao=apresentacao,
            dimensoes_nao_mapeadas=resumo.dimensoes_nao_mapeadas or None,
        )
