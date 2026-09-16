from dataclasses import dataclass
from decimal import Decimal

from domain.value_objects.sell_in_aggregation import OutroPeriodoTotais

TIPOLOGIAS = ["Cerâmica", "Porcelanato", "Super Prime"]


@dataclass
class InsightsComparativoPeriodos:
    """Insights para a 3a parte do deck: compara DOIS periodos livres, escolhidos
    pelo usuario (ex: Jan-Mar/2026 vs Mar-Jul/2025), que podem ter quantidades de
    meses diferentes. Por isso a comparacao e sempre feita em cima de TOTAIS de
    cada periodo (nunca mes a mes) -- nao da pra alinhar um grafico de linha
    quando os dois periodos nao tem o mesmo numero de meses.

    Periodo 1 e tratado como o periodo "atual"/principal (variacoes percentuais
    sao sempre periodo1 vs periodo2, na mesma logica de "atual vs anterior" usada
    no resto do deck)."""
    periodo1_label: str
    periodo2_label: str

    faturamento_periodo1: Decimal
    faturamento_periodo2: Decimal
    faturamento_variacao_pct: Decimal

    volume_periodo1: Decimal
    volume_periodo2: Decimal
    volume_variacao_pct: Decimal

    ticket_medio_periodo1: Decimal
    ticket_medio_periodo2: Decimal
    ticket_medio_variacao_pct: Decimal

    ticket_medio_tipologia_periodo1: dict
    ticket_medio_tipologia_periodo2: dict
    ticket_medio_tipologia_variacao_pct: dict

    volume_tipologia_periodo1: dict
    volume_tipologia_periodo2: dict
    volume_tipologia_variacao_pct: dict

    faturamento_tipologia_periodo1: dict
    faturamento_tipologia_periodo2: dict
    faturamento_tipologia_variacao_pct: dict

    participacao_volume_periodo1: dict
    participacao_volume_periodo2: dict
    participacao_faturamento_periodo1: dict
    participacao_faturamento_periodo2: dict

    # {tipologia: {formato: valor}} -- estudo de formatos, um por periodo.
    faturamento_por_formato_periodo1: dict
    faturamento_por_formato_periodo2: dict
    qtde_por_formato_periodo1: dict
    qtde_por_formato_periodo2: dict

    # {cliente: valor} -- ranking de Top 10 clientes, um por periodo.
    faturamento_por_cliente_periodo1: dict
    faturamento_por_cliente_periodo2: dict


def _variacao_pct(atual: Decimal, base: Decimal) -> Decimal:
    return (atual / base - 1) * 100 if base else Decimal(0)


def montar_insights_comparativo_periodos(periodo1: OutroPeriodoTotais,
                                          periodo2: OutroPeriodoTotais) -> InsightsComparativoPeriodos:
    fat1, fat2 = periodo1.faturamento_total, periodo2.faturamento_total
    vol1, vol2 = periodo1.volume_total, periodo2.volume_total
    tm1, tm2 = periodo1.ticket_medio, periodo2.ticket_medio

    total_vol_p1 = sum(periodo1.qtde_por_tipologia.values()) or Decimal(1)
    total_vol_p2 = sum(periodo2.qtde_por_tipologia.values()) or Decimal(1)
    total_fat_p1 = sum(periodo1.faturamento_por_tipologia.values()) or Decimal(1)
    total_fat_p2 = sum(periodo2.faturamento_por_tipologia.values()) or Decimal(1)

    ticket_medio_tipologia_p1, ticket_medio_tipologia_p2, ticket_medio_tipologia_var = {}, {}, {}
    volume_tipologia_p1, volume_tipologia_p2, volume_tipologia_var = {}, {}, {}
    faturamento_tipologia_p1, faturamento_tipologia_p2, faturamento_tipologia_var = {}, {}, {}
    participacao_volume_p1, participacao_volume_p2 = {}, {}
    participacao_faturamento_p1, participacao_faturamento_p2 = {}, {}

    for tipologia in TIPOLOGIAS:
        fat_t1 = periodo1.faturamento_por_tipologia.get(tipologia, Decimal(0))
        fat_t2 = periodo2.faturamento_por_tipologia.get(tipologia, Decimal(0))
        vol_t1 = periodo1.qtde_por_tipologia.get(tipologia, Decimal(0))
        vol_t2 = periodo2.qtde_por_tipologia.get(tipologia, Decimal(0))

        tm_t1 = (fat_t1 / vol_t1) if vol_t1 else Decimal(0)
        tm_t2 = (fat_t2 / vol_t2) if vol_t2 else Decimal(0)

        ticket_medio_tipologia_p1[tipologia] = tm_t1
        ticket_medio_tipologia_p2[tipologia] = tm_t2
        ticket_medio_tipologia_var[tipologia] = _variacao_pct(tm_t1, tm_t2)

        volume_tipologia_p1[tipologia] = vol_t1
        volume_tipologia_p2[tipologia] = vol_t2
        volume_tipologia_var[tipologia] = _variacao_pct(vol_t1, vol_t2)

        faturamento_tipologia_p1[tipologia] = fat_t1
        faturamento_tipologia_p2[tipologia] = fat_t2
        faturamento_tipologia_var[tipologia] = _variacao_pct(fat_t1, fat_t2)

        participacao_volume_p1[tipologia] = (vol_t1 / total_vol_p1) * 100
        participacao_volume_p2[tipologia] = (vol_t2 / total_vol_p2) * 100
        participacao_faturamento_p1[tipologia] = (fat_t1 / total_fat_p1) * 100
        participacao_faturamento_p2[tipologia] = (fat_t2 / total_fat_p2) * 100

    return InsightsComparativoPeriodos(
        periodo1_label=periodo1.label,
        periodo2_label=periodo2.label,
        faturamento_periodo1=fat1,
        faturamento_periodo2=fat2,
        faturamento_variacao_pct=_variacao_pct(fat1, fat2),
        volume_periodo1=vol1,
        volume_periodo2=vol2,
        volume_variacao_pct=_variacao_pct(vol1, vol2),
        ticket_medio_periodo1=tm1,
        ticket_medio_periodo2=tm2,
        ticket_medio_variacao_pct=_variacao_pct(tm1, tm2),
        ticket_medio_tipologia_periodo1=ticket_medio_tipologia_p1,
        ticket_medio_tipologia_periodo2=ticket_medio_tipologia_p2,
        ticket_medio_tipologia_variacao_pct=ticket_medio_tipologia_var,
        volume_tipologia_periodo1=volume_tipologia_p1,
        volume_tipologia_periodo2=volume_tipologia_p2,
        volume_tipologia_variacao_pct=volume_tipologia_var,
        faturamento_tipologia_periodo1=faturamento_tipologia_p1,
        faturamento_tipologia_periodo2=faturamento_tipologia_p2,
        faturamento_tipologia_variacao_pct=faturamento_tipologia_var,
        participacao_volume_periodo1=participacao_volume_p1,
        participacao_volume_periodo2=participacao_volume_p2,
        participacao_faturamento_periodo1=participacao_faturamento_p1,
        participacao_faturamento_periodo2=participacao_faturamento_p2,
        faturamento_por_formato_periodo1=periodo1.faturamento_por_formato,
        faturamento_por_formato_periodo2=periodo2.faturamento_por_formato,
        qtde_por_formato_periodo1=periodo1.qtde_por_formato,
        qtde_por_formato_periodo2=periodo2.qtde_por_formato,
        faturamento_por_cliente_periodo1=periodo1.faturamento_por_cliente,
        faturamento_por_cliente_periodo2=periodo2.faturamento_por_cliente,
    )
