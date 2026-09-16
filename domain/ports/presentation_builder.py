from typing import Protocol

from domain.value_objects.periodo_comparativo_insights import InsightsComparativoPeriodos
from domain.value_objects.sell_in_insights import InsightsSellIn


class PresentationBuilder(Protocol):
    def montar_apresentacao(self, insights_absoluto: InsightsSellIn, insights_comparativo: InsightsSellIn,
                             graficos: dict[str, bytes],
                             insights_periodos: InsightsComparativoPeriodos | None = None) -> bytes:
        ...