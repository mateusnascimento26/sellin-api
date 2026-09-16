from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal

from domain.entities.sale_record import SaleRecord


@dataclass
class EvolucaoAnoUnico:
    ano: int
    meses: list[int]
    faturamento_mensal: dict
    volume_mensal: dict


def montar_evolucao_ano_unico(registros: list[SaleRecord], ano: int) -> EvolucaoAnoUnico:
    """Agrega o faturamento e volume mes a mes de UM UNICO ano, sem compara-lo com
    nenhum outro (diferente de montar_resumo, que sempre compara dois anos).
    Usado quando o usuario pede para ver um periodo especifico, ex: "me mostra 2025"."""
    faturamento_mensal = defaultdict(Decimal)
    volume_mensal = defaultdict(Decimal)

    for r in registros:
        if r.ano != ano:
            continue
        faturamento_mensal[r.mes] += r.valor
        volume_mensal[r.mes] += r.qtde

    meses = sorted(faturamento_mensal.keys())
    if not meses:
        raise ValueError(f"Nenhum dado encontrado para o ano {ano} neste arquivo.")

    return EvolucaoAnoUnico(
        ano=ano,
        meses=meses,
        faturamento_mensal=dict(faturamento_mensal),
        volume_mensal=dict(volume_mensal),
    )