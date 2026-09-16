from dataclasses import dataclass

from domain.ports.chart_generator import ChartGenerator
from domain.ports.sell_in_reader import SellInReader
from domain.value_objects.sell_in_aggregation import montar_resumo


@dataclass
class GenerateSellInChartsResult:
    ok: bool
    message: str
    graficos: dict[str, bytes] | None = None
    dimensoes_nao_mapeadas: dict[str, int] | None = None


class GenerateSellInCharts:
    def __init__(self, sell_in_reader: SellInReader, chart_generator: ChartGenerator):
        self.sell_in_reader = sell_in_reader
        self.chart_generator = chart_generator

    def execute(self, file_content: bytes) -> GenerateSellInChartsResult:
        registros = self.sell_in_reader.read(file_content)
        if not registros:
            return GenerateSellInChartsResult(ok=False, message="Nenhum dado válido encontrado no arquivo.")

        resumo = montar_resumo(registros)
        graficos = self.chart_generator.gerar_graficos(resumo)

        return GenerateSellInChartsResult(
            ok=True,
            message="Gráficos gerados com sucesso.",
            graficos=graficos,
            dimensoes_nao_mapeadas=resumo.dimensoes_nao_mapeadas or None,
        )