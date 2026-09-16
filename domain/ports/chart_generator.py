from typing import Protocol

from domain.value_objects.sell_in_aggregation import OutroPeriodoTotais, ResumoSellIn


class ChartGenerator(Protocol):
    def gerar_graficos(self, resumo: ResumoSellIn) -> dict[str, bytes]:
        ...

    def gerar_graficos_slide(self, resumo: ResumoSellIn) -> dict[str, bytes]:
        ...

    def gerar_graficos_slide_linha(self, resumo: ResumoSellIn) -> dict[str, bytes]:
        ...

    def gerar_graficos_ticket_medio(self, resumo: ResumoSellIn) -> dict[str, bytes]:
        ...

    def gerar_graficos_faturamento_tipologia(self, resumo: ResumoSellIn) -> dict[str, bytes]:
        ...

    def gerar_graficos_participacao_tipologia(self, resumo: ResumoSellIn) -> dict[str, bytes]:
        ...

    def gerar_grafico_volume_mensal(self, resumo: ResumoSellIn) -> bytes:
        ...

    def gerar_grafico_ticket_medio_geral(self, resumo: ResumoSellIn) -> bytes:
        ...

    def gerar_grafico_crescimento_ticket_medio(self, resumo: ResumoSellIn) -> bytes:
        ...

    def gerar_grafico_desempenho_tipologias(self, resumo: ResumoSellIn) -> bytes:
        ...

    def gerar_grafico_ticket_medio_tipologias(self, resumo: ResumoSellIn) -> bytes:
        ...

    def gerar_grafico_faturamento_tipologias(self, resumo: ResumoSellIn) -> bytes:
        ...

    def gerar_grafico_representatividade_volume(self, resumo: ResumoSellIn) -> bytes:
        ...

    def gerar_grafico_formatos_tipologia_volume(self, resumo: ResumoSellIn, tipologia: str) -> bytes:
        ...

    def gerar_grafico_formatos_tipologia_faturamento(self, resumo: ResumoSellIn, tipologia: str) -> bytes:
        ...

    def gerar_graficos_periodo_ticket_medio(self, periodo1: OutroPeriodoTotais,
                                             periodo2: OutroPeriodoTotais) -> dict[str, bytes]:
        ...

    def gerar_graficos_periodo_volume(self, periodo1: OutroPeriodoTotais,
                                       periodo2: OutroPeriodoTotais) -> dict[str, bytes]:
        ...

    def gerar_graficos_periodo_faturamento(self, periodo1: OutroPeriodoTotais,
                                            periodo2: OutroPeriodoTotais) -> dict[str, bytes]:
        ...

    def gerar_grafico_periodo_ticket_medio_tipologias_juntas(self, periodo1: OutroPeriodoTotais,
                                                               periodo2: OutroPeriodoTotais) -> bytes:
        ...

    def gerar_grafico_periodo_volume_tipologias_juntas(self, periodo1: OutroPeriodoTotais,
                                                         periodo2: OutroPeriodoTotais) -> bytes:
        ...

    def gerar_grafico_periodo_faturamento_tipologias_juntas(self, periodo1: OutroPeriodoTotais,
                                                              periodo2: OutroPeriodoTotais) -> bytes:
        ...

    def gerar_grafico_periodo_proporcao_volume(self, periodo1: OutroPeriodoTotais,
                                                periodo2: OutroPeriodoTotais) -> bytes:
        ...

    def gerar_grafico_periodo_proporcao_faturamento(self, periodo1: OutroPeriodoTotais,
                                                     periodo2: OutroPeriodoTotais) -> bytes:
        ...

    def gerar_grafico_periodo_formatos_tipologia_volume(self, periodo1: OutroPeriodoTotais,
                                                          periodo2: OutroPeriodoTotais, tipologia: str) -> bytes:
        ...

    def gerar_grafico_periodo_formatos_tipologia_faturamento(self, periodo1: OutroPeriodoTotais,
                                                               periodo2: OutroPeriodoTotais, tipologia: str) -> bytes:
        ...

    def gerar_grafico_ranking_clientes(self, resumo: ResumoSellIn) -> bytes:
        ...

    def gerar_grafico_periodo_ranking_clientes(self, periodo1: OutroPeriodoTotais,
                                                periodo2: OutroPeriodoTotais) -> bytes:
        ...

    def gerar_grafico_pizza_tipologia(self, totais: dict) -> bytes:
        ...

    def gerar_grafico_crescimento_tipologia_mensal(self, resumo: ResumoSellIn) -> bytes:
        ...