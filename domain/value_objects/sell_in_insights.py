from dataclasses import dataclass
from decimal import Decimal

from domain.value_objects.sell_in_aggregation import MESES_NOMES, OutroPeriodoTotais, ResumoSellIn


@dataclass
class InsightsSellIn:
    periodo_label: str
    ano_anterior: int
    ano_atual: int
    rotulo_atual: str
    rotulo_anterior: str
    periodo_cruza_ano: bool
    faturamento_anterior: Decimal
    faturamento_atual: Decimal
    faturamento_variacao_pct: Decimal
    volume_anterior: Decimal
    volume_atual: Decimal
    volume_variacao_pct: Decimal
    melhor_mes_label: str
    melhor_mes_valor: Decimal
    melhor_mes_anterior_label: str
    melhor_mes_anterior_valor: Decimal
    ticket_medio_geral_atual: Decimal
    ticket_medio_geral_anterior: Decimal
    ticket_medio_geral_variacao_pct: Decimal
    participacao_por_tipologia: dict
    participacao_volume_por_tipologia: dict
    tipologia_maior_alta: str
    tipologia_maior_alta_variacao_pp: Decimal
    tipologia_dominante: str
    tipologia_dominante_pct_atual: Decimal
    ticket_medio_atual: dict
    ticket_medio_anterior: dict
    ticket_medio_variacao_pct: dict
    faturamento_tipologia_atual: dict
    faturamento_tipologia_anterior: dict
    faturamento_tipologia_variacao_pct: dict
    volume_tipologia_atual: dict
    volume_tipologia_anterior: dict
    volume_tipologia_variacao_pct: dict
    # {ano_atual|ano_anterior: {tipologia: {formato: valor}}} -- estudo de formatos.
    faturamento_por_formato: dict
    qtde_por_formato: dict
    # {ano_atual|ano_anterior: {cliente: valor}} -- ranking de Top 10 clientes.
    faturamento_por_cliente: dict
    dimensoes_nao_mapeadas: dict
    mes_atual_excluido: bool
    comparar_ano_anterior: bool
    outro_periodo: OutroPeriodoTotais | None
    outro_periodo_faturamento_variacao_pct: Decimal
    outro_periodo_volume_variacao_pct: Decimal
    faturamento_tipologia_variacao_outro_pct: dict


def montar_insights(resumo: ResumoSellIn) -> InsightsSellIn:
    meses = resumo.meses_comparados
    ano_ant, ano_atu = resumo.ano_anterior, resumo.ano_atual

    # Quando o periodo cruza a virada do ano, "Jan a Mar" fica ambiguo (nao mostra
    # que, por exemplo, "Out" e' de um ano e "Fev" e' do ano seguinte) -- nesse caso
    # o rotulo inclui o ano abreviado em cada ponta.
    periodo_cruza_ano = len({ano for ano, _ in resumo.periodo_atual_chaves}) > 1
    if periodo_cruza_ano:
        primeiro, ultimo = resumo.periodo_atual_chaves[0], resumo.periodo_atual_chaves[-1]
        periodo_label = (f"{MESES_NOMES[primeiro[1]-1]}/{str(primeiro[0])[2:]} a "
                          f"{MESES_NOMES[ultimo[1]-1]}/{str(ultimo[0])[2:]}")
    else:
        periodo_label = f"{MESES_NOMES[meses[0]-1]} a {MESES_NOMES[meses[-1]-1]}"

    def rotulo_mes(mes: int, chaves: list[tuple[int, int]]) -> str:
        if not periodo_cruza_ano:
            return MESES_NOMES[mes - 1]
        ano_real = next((ano for ano, m in chaves if m == mes), None)
        return f"{MESES_NOMES[mes-1]}/{str(ano_real)[2:]}" if ano_real else MESES_NOMES[mes - 1]

    fat_ant = sum(resumo.faturamento_mensal.get((ano_ant, m), Decimal(0)) for m in meses)
    fat_atu = sum(resumo.faturamento_mensal.get((ano_atu, m), Decimal(0)) for m in meses)
    fat_var = (fat_atu / fat_ant - 1) * 100 if fat_ant else Decimal(0)

    vol_ant = sum(resumo.volume_mensal.get((ano_ant, m), Decimal(0)) for m in meses)
    vol_atu = sum(resumo.volume_mensal.get((ano_atu, m), Decimal(0)) for m in meses)
    vol_var = (vol_atu / vol_ant - 1) * 100 if vol_ant else Decimal(0)

    melhor_mes = max(meses, key=lambda m: resumo.faturamento_mensal.get((ano_atu, m), Decimal(0)))
    melhor_mes_valor = resumo.faturamento_mensal.get((ano_atu, melhor_mes), Decimal(0))

    melhor_mes_anterior = max(meses, key=lambda m: resumo.faturamento_mensal.get((ano_ant, m), Decimal(0)))
    melhor_mes_anterior_valor = resumo.faturamento_mensal.get((ano_ant, melhor_mes_anterior), Decimal(0))

    ticket_medio_geral_atu = (fat_atu / vol_atu) if vol_atu else Decimal(0)
    ticket_medio_geral_ant = (fat_ant / vol_ant) if vol_ant else Decimal(0)
    ticket_medio_geral_var = (
        (ticket_medio_geral_atu / ticket_medio_geral_ant - 1) * 100 if ticket_medio_geral_ant else Decimal(0)
    )

    participacao = {}
    for ano in (ano_ant, ano_atu):
        totais = resumo.faturamento_por_tipologia.get(ano, {})
        total = sum(totais.values()) or Decimal(1)
        participacao[ano] = {t: (v / total) * 100 for t, v in totais.items()}

    participacao_volume = {}
    for ano in (ano_ant, ano_atu):
        totais_vol = resumo.qtde_por_tipologia.get(ano, {})
        total_vol = sum(totais_vol.values()) or Decimal(1)
        participacao_volume[ano] = {t: (v / total_vol) * 100 for t, v in totais_vol.items()}

    variacoes_pp = {}
    if resumo.comparar_ano_anterior:
        for tipologia in set(participacao.get(ano_ant, {})) | set(participacao.get(ano_atu, {})):
            antes = participacao.get(ano_ant, {}).get(tipologia, Decimal(0))
            depois = participacao.get(ano_atu, {}).get(tipologia, Decimal(0))
            variacoes_pp[tipologia] = depois - antes

    tipologia_maior_alta = max(variacoes_pp, key=variacoes_pp.get) if variacoes_pp else ""
    tipologia_dominante = (
        max(participacao.get(ano_atu, {}), key=participacao[ano_atu].get)
        if participacao.get(ano_atu) else ""
    )

    tipologias = set(resumo.faturamento_por_tipologia.get(ano_ant, {})) | set(resumo.faturamento_por_tipologia.get(ano_atu, {}))
    ticket_medio_atual = {}
    ticket_medio_anterior = {}
    ticket_medio_variacao_pct = {}
    for tipologia in tipologias:
        fat_t_atu = resumo.faturamento_por_tipologia.get(ano_atu, {}).get(tipologia, Decimal(0))
        qtd_t_atu = resumo.qtde_por_tipologia.get(ano_atu, {}).get(tipologia, Decimal(0))
        fat_t_ant = resumo.faturamento_por_tipologia.get(ano_ant, {}).get(tipologia, Decimal(0))
        qtd_t_ant = resumo.qtde_por_tipologia.get(ano_ant, {}).get(tipologia, Decimal(0))

        tm_atu = (fat_t_atu / qtd_t_atu) if qtd_t_atu else Decimal(0)
        tm_ant = (fat_t_ant / qtd_t_ant) if qtd_t_ant else Decimal(0)
        ticket_medio_atual[tipologia] = tm_atu
        ticket_medio_anterior[tipologia] = tm_ant
        ticket_medio_variacao_pct[tipologia] = (tm_atu / tm_ant - 1) * 100 if tm_ant else Decimal(0)

    faturamento_tipologia_atual = {}
    faturamento_tipologia_anterior = {}
    faturamento_tipologia_variacao_pct = {}
    faturamento_tipologia_variacao_outro_pct = {}
    for tipologia in tipologias | set(resumo.outro_periodo.faturamento_por_tipologia if resumo.outro_periodo else {}):
        ft_atu = resumo.faturamento_por_tipologia.get(ano_atu, {}).get(tipologia, Decimal(0))
        ft_ant = resumo.faturamento_por_tipologia.get(ano_ant, {}).get(tipologia, Decimal(0))
        faturamento_tipologia_atual[tipologia] = ft_atu
        faturamento_tipologia_anterior[tipologia] = ft_ant
        faturamento_tipologia_variacao_pct[tipologia] = (ft_atu / ft_ant - 1) * 100 if ft_ant else Decimal(0)

        if resumo.outro_periodo is not None:
            ft_outro = resumo.outro_periodo.faturamento_por_tipologia.get(tipologia, Decimal(0))
            faturamento_tipologia_variacao_outro_pct[tipologia] = (
                (ft_atu / ft_outro - 1) * 100 if ft_outro else Decimal(0)
            )
        else:
            faturamento_tipologia_variacao_outro_pct[tipologia] = Decimal(0)

    volume_tipologia_atual = {}
    volume_tipologia_anterior = {}
    volume_tipologia_variacao_pct = {}
    for tipologia in tipologias:
        vt_atu = resumo.qtde_por_tipologia.get(ano_atu, {}).get(tipologia, Decimal(0))
        vt_ant = resumo.qtde_por_tipologia.get(ano_ant, {}).get(tipologia, Decimal(0))
        volume_tipologia_atual[tipologia] = vt_atu
        volume_tipologia_anterior[tipologia] = vt_ant
        volume_tipologia_variacao_pct[tipologia] = (vt_atu / vt_ant - 1) * 100 if vt_ant else Decimal(0)

    if resumo.outro_periodo is not None:
        outro_periodo_faturamento_variacao_pct = (
            (fat_atu / resumo.outro_periodo.faturamento_total - 1) * 100
            if resumo.outro_periodo.faturamento_total else Decimal(0)
        )
        outro_periodo_volume_variacao_pct = (
            (vol_atu / resumo.outro_periodo.volume_total - 1) * 100
            if resumo.outro_periodo.volume_total else Decimal(0)
        )
    else:
        outro_periodo_faturamento_variacao_pct = Decimal(0)
        outro_periodo_volume_variacao_pct = Decimal(0)

    return InsightsSellIn(
        periodo_label=periodo_label,
        ano_anterior=ano_ant,
        ano_atual=ano_atu,
        rotulo_atual=resumo.rotulo_atual,
        rotulo_anterior=resumo.rotulo_anterior,
        periodo_cruza_ano=periodo_cruza_ano,
        faturamento_anterior=fat_ant,
        faturamento_atual=fat_atu,
        faturamento_variacao_pct=fat_var,
        volume_anterior=vol_ant,
        volume_atual=vol_atu,
        volume_variacao_pct=vol_var,
        melhor_mes_label=rotulo_mes(melhor_mes, resumo.periodo_atual_chaves),
        melhor_mes_valor=melhor_mes_valor,
        melhor_mes_anterior_label=rotulo_mes(melhor_mes_anterior, resumo.periodo_anterior_chaves),
        melhor_mes_anterior_valor=melhor_mes_anterior_valor,
        ticket_medio_geral_atual=ticket_medio_geral_atu,
        ticket_medio_geral_anterior=ticket_medio_geral_ant,
        ticket_medio_geral_variacao_pct=ticket_medio_geral_var,
        participacao_por_tipologia=participacao,
        participacao_volume_por_tipologia=participacao_volume,
        tipologia_maior_alta=tipologia_maior_alta,
        tipologia_maior_alta_variacao_pp=variacoes_pp.get(tipologia_maior_alta, Decimal(0)),
        tipologia_dominante=tipologia_dominante,
        tipologia_dominante_pct_atual=participacao.get(ano_atu, {}).get(tipologia_dominante, Decimal(0)),
        ticket_medio_atual=ticket_medio_atual,
        ticket_medio_anterior=ticket_medio_anterior,
        ticket_medio_variacao_pct=ticket_medio_variacao_pct,
        faturamento_tipologia_atual=faturamento_tipologia_atual,
        faturamento_tipologia_anterior=faturamento_tipologia_anterior,
        faturamento_tipologia_variacao_pct=faturamento_tipologia_variacao_pct,
        volume_tipologia_atual=volume_tipologia_atual,
        volume_tipologia_anterior=volume_tipologia_anterior,
        volume_tipologia_variacao_pct=volume_tipologia_variacao_pct,
        faturamento_por_formato=resumo.faturamento_por_formato,
        qtde_por_formato=resumo.qtde_por_formato,
        faturamento_por_cliente=resumo.faturamento_por_cliente,
        dimensoes_nao_mapeadas=resumo.dimensoes_nao_mapeadas,
        mes_atual_excluido=resumo.mes_atual_excluido,
        comparar_ano_anterior=resumo.comparar_ano_anterior,
        outro_periodo=resumo.outro_periodo,
        outro_periodo_faturamento_variacao_pct=outro_periodo_faturamento_variacao_pct,
        outro_periodo_volume_variacao_pct=outro_periodo_volume_variacao_pct,
        faturamento_tipologia_variacao_outro_pct=faturamento_tipologia_variacao_outro_pct,
    )
