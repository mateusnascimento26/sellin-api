from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from domain.entities.sale_record import SaleRecord
from domain.value_objects.dimension import find_dimension

TIPOLOGIA_POR_DIMENSAO = {
    "33x46": "Cerâmica", "46x46": "Cerâmica", "57x57": "Cerâmica",
    "30x61": "Porcelanato", "34x70": "Porcelanato", "60x120": "Porcelanato",
    "120x120": "Porcelanato", "70x70": "Porcelanato", "94.5x94.5": "Porcelanato",
    "50x100": "Porcelanato", "16x101": "Porcelanato", "24.5x101": "Porcelanato",
    "32x65": "Super Prime", "17x106": "Super Prime", "56x56": "Super Prime",
    "75x75": "Super Prime", "100x100": "Super Prime", "33x66": "Super Prime",
}

MESES_NOMES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]

# Formatos (dimensoes) agrupados por tipologia, na ordem em que aparecem em
# TIPOLOGIA_POR_DIMENSAO -- usado no "estudo de formatos" (participacao de cada
# formato, ex: 33x46, dentro da propria tipologia).
FORMATOS_POR_TIPOLOGIA: dict[str, list[str]] = {}
for _dimensao, _tipologia in TIPOLOGIA_POR_DIMENSAO.items():
    FORMATOS_POR_TIPOLOGIA.setdefault(_tipologia, []).append(_dimensao)


@dataclass
class OutroPeriodoTotais:
    """Totais de um periodo de comparacao 'livre', escolhido pelo usuario, que pode ter
    duracao (numero de meses) diferente do periodo de analise. Por isso so guarda totais
    (nao guarda quebra mes a mes) -- nao da pra alinhar mes a mes dois periodos de tamanhos
    diferentes. Usado hoje apenas nos graficos de barra."""
    label: str
    faturamento_total: Decimal
    volume_total: Decimal
    faturamento_por_tipologia: dict
    qtde_por_tipologia: dict
    num_meses: int
    # {tipologia: {formato: valor}} -- estudo de formatos dentro de cada tipologia.
    faturamento_por_formato: dict = field(default_factory=dict)
    qtde_por_formato: dict = field(default_factory=dict)
    # {cliente: valor} -- ranking de Top 10 clientes por faturamento.
    faturamento_por_cliente: dict = field(default_factory=dict)

    @property
    def faturamento_mensal_medio(self) -> Decimal:
        return self.faturamento_total / self.num_meses if self.num_meses else Decimal(0)

    @property
    def volume_mensal_medio(self) -> Decimal:
        return self.volume_total / self.num_meses if self.num_meses else Decimal(0)

    @property
    def ticket_medio(self) -> Decimal:
        return self.faturamento_total / self.volume_total if self.volume_total else Decimal(0)


@dataclass
class ResumoSellIn:
    ano_anterior: int
    ano_atual: int
    meses_comparados: list[int]
    faturamento_mensal: dict
    volume_mensal: dict
    faturamento_por_tipologia: dict
    faturamento_tipologia_mensal: dict
    qtde_por_tipologia: dict
    qtde_tipologia_mensal: dict
    dimensoes_nao_mapeadas: dict
    # {ano_atual|ano_anterior: {tipologia: {formato: valor}}} -- estudo de formatos.
    faturamento_por_formato: dict = field(default_factory=dict)
    qtde_por_formato: dict = field(default_factory=dict)
    # {ano_atual|ano_anterior: {cliente: valor}} -- ranking de Top 10 clientes.
    faturamento_por_cliente: dict = field(default_factory=dict)
    mes_atual_excluido: bool = False
    comparar_ano_anterior: bool = True
    outro_periodo: OutroPeriodoTotais | None = None
    # As chaves (ano, mes) REAIS de cada mes do periodo atual/anterior, na ordem
    # cronologica -- usadas so pra exibicao (rotulos de eixo, "melhor mes" etc.),
    # quando o periodo cruza a virada do ano e o mes sozinho (ex: "Out") fica
    # ambiguo sem o ano. Os dicionarios acima (faturamento_mensal etc.) continuam
    # indexados por (ano_atual|ano_anterior, mes) -- ver comentario em _agregar.
    periodo_atual_chaves: list = field(default_factory=list)
    periodo_anterior_chaves: list = field(default_factory=list)
    # Rotulo curto pronto pra exibir (legendas, titulos): "2026" quando o periodo
    # cabe num unico ano civil (como sempre foi), ou "Out/25 a Fev/26" quando cruza
    # a virada do ano.
    rotulo_atual: str = ""
    rotulo_anterior: str = ""


def _sequencia_ano_mes(data_inicial: date, data_final: date) -> list[tuple[int, int]]:
    """Gera a lista ordenada de (ano, mes) entre data_inicial e data_final (inclusive),
    mes a mes -- suporta cruzar a virada do ano (ex: Out/2025 a Fev/2026), diferente de
    um simples range() que so funciona dentro de um unico ano."""
    chaves = []
    ano, mes = data_inicial.year, data_inicial.month
    fim = (data_final.year, data_final.month)
    while (ano, mes) <= fim:
        chaves.append((ano, mes))
        mes += 1
        if mes > 12:
            mes = 1
            ano += 1
    return chaves


def _rotulo_periodo(chaves: list[tuple[int, int]], rotulo_ano_unico: str) -> str:
    """Rotulo curto pra exibicao: se o periodo fica dentro de um unico ano civil, usa
    so o ano (comportamento de sempre, ex: '2026'); se cruza a virada do ano, usa o
    intervalo por extenso (ex: 'Out/25 a Fev/26'), pra nao ficar ambiguo."""
    anos = {ano for ano, _ in chaves}
    if len(anos) <= 1:
        return rotulo_ano_unico
    primeiro, ultimo = chaves[0], chaves[-1]
    inicio = f"{MESES_NOMES[primeiro[1] - 1]}/{str(primeiro[0])[2:]}"
    fim = f"{MESES_NOMES[ultimo[1] - 1]}/{str(ultimo[0])[2:]}"
    return f"{inicio} a {fim}"


def montar_resumo(registros: list[SaleRecord]) -> ResumoSellIn:
    anos = sorted({r.ano for r in registros})
    if not anos:
        raise ValueError("Nenhum registro válido encontrado no arquivo para gerar os gráficos.")

    ano_atual = anos[-1]
    ano_anterior = anos[-2] if len(anos) > 1 else anos[-1]

    meses_do_ano_atual = sorted({r.mes for r in registros if r.ano == ano_atual})
    mes_mais_recente = max(meses_do_ano_atual, default=12)
    mes_atual_excluido = len(meses_do_ano_atual) > 1
    if mes_atual_excluido:
        mes_limite = mes_mais_recente - 1
    else:
        mes_limite = mes_mais_recente
    meses_comparados = list(range(1, mes_limite + 1))
    periodo_atual_chaves = [(ano_atual, m) for m in meses_comparados]
    periodo_anterior_chaves = [(ano_anterior, m) for m in meses_comparados]

    return _agregar(registros, ano_anterior, ano_atual, meses_comparados,
                     periodo_atual_chaves, periodo_anterior_chaves, mes_atual_excluido=mes_atual_excluido)


def montar_resumo_periodo(
    registros: list[SaleRecord],
    data_inicial: date,
    data_final: date,
    comparar_ano_anterior: bool = True,
    outro_periodo_inicio: date | None = None,
    outro_periodo_fim: date | None = None,
) -> ResumoSellIn:
    """Agrega um periodo escolhido pelo usuario (ex: 01/01/2026 a 01/03/2026).

    A granularidade e' de mes inteiro: o dia dentro do mes e' ignorado (o banco so guarda
    ano e mes de cada venda). O periodo PODE cruzar a virada do ano (ex: Out/2025 a
    Fev/2026), mas nao pode ultrapassar 12 meses no total -- isso garante que sempre da
    pra comparar mes a mes 1-pra-1 com o mesmo periodo do ano anterior, sem ambiguidade
    de qual mes e' qual (ex: um periodo de 14 meses repetiria algum mes duas vezes).

    Tres entradas controlam a comparacao:
    - comparar_ano_anterior: se True (padrao), compara automaticamente com o mesmo periodo
      do ano anterior (ex: Jan-Mar/2026 vs Jan-Mar/2025).
    - outro_periodo_inicio / outro_periodo_fim: um segundo periodo de comparacao, livre
      (pode ter duracao diferente do periodo de analise, inclusive cruzar anos). So e'
      usado nos graficos de barra, como uma comparacao adicional de totais.
    Se nenhuma das duas comparacoes estiver ativa, o resumo fica em "modo absoluto":
    mostra so os valores do periodo selecionado, sem nenhuma comparacao."""
    if data_inicial > data_final:
        raise ValueError("A data inicial não pode ser depois da data final.")

    periodo_atual_chaves = _sequencia_ano_mes(data_inicial, data_final)
    if len(periodo_atual_chaves) > 12:
        raise ValueError(
            "O período não pode ter mais de 12 meses. Ele pode cruzar a virada do ano "
            "(ex: Out/2025 a Fev/2026), mas o total não pode ultrapassar 12 meses."
        )
    if (outro_periodo_inicio is None) != (outro_periodo_fim is None):
        raise ValueError("Informe o início e o fim do outro período juntos.")
    if outro_periodo_inicio is not None and outro_periodo_inicio > outro_periodo_fim:
        raise ValueError("A data inicial do outro período não pode ser depois da data final.")

    ano_atual = data_final.year
    ano_anterior = ano_atual - 1
    meses_comparados = [mes for _, mes in periodo_atual_chaves]
    periodo_anterior_chaves = [(ano - 1, mes) for ano, mes in periodo_atual_chaves]

    outro_periodo = None
    if outro_periodo_inicio is not None:
        outro_periodo = montar_totais_periodo(registros, outro_periodo_inicio, outro_periodo_fim)

    return _agregar(registros, ano_anterior, ano_atual, meses_comparados,
                     periodo_atual_chaves, periodo_anterior_chaves,
                     comparar_ano_anterior=comparar_ano_anterior, outro_periodo=outro_periodo)


def montar_totais_periodo(registros: list[SaleRecord], data_inicial: date, data_final: date) -> OutroPeriodoTotais:
    """Agrega os totais (sem quebra mes a mes) de um periodo arbitrario -- pode ter
    qualquer duracao e cruzar a virada do ano -- para ser usado como um segundo
    periodo de comparacao nos graficos de barra."""
    if data_inicial > data_final:
        raise ValueError("A data inicial do outro período não pode ser depois da data final.")

    inicio_chave = (data_inicial.year, data_inicial.month)
    fim_chave = (data_final.year, data_final.month)
    num_meses = (data_final.year - data_inicial.year) * 12 + (data_final.month - data_inicial.month) + 1

    faturamento_total = Decimal(0)
    volume_total = Decimal(0)
    faturamento_por_tipologia = defaultdict(Decimal)
    qtde_por_tipologia = defaultdict(Decimal)
    faturamento_por_formato = defaultdict(lambda: defaultdict(Decimal))
    qtde_por_formato = defaultdict(lambda: defaultdict(Decimal))
    faturamento_por_cliente = defaultdict(Decimal)

    for r in registros:
        chave = (r.ano, r.mes)
        if not (inicio_chave <= chave <= fim_chave):
            continue

        faturamento_total += r.valor
        volume_total += r.qtde
        faturamento_por_cliente[r.cliente] += r.valor

        dimensao = find_dimension(r.produto)
        tipologia = TIPOLOGIA_POR_DIMENSAO.get(dimensao)
        if tipologia is None:
            continue

        faturamento_por_tipologia[tipologia] += r.valor
        qtde_por_tipologia[tipologia] += r.qtde
        faturamento_por_formato[tipologia][dimensao] += r.valor
        qtde_por_formato[tipologia][dimensao] += r.qtde

    label_inicio = f"{MESES_NOMES[data_inicial.month - 1]}/{str(data_inicial.year)[2:]}"
    label_fim = f"{MESES_NOMES[data_final.month - 1]}/{str(data_final.year)[2:]}"
    label = label_inicio if inicio_chave == fim_chave else f"{label_inicio} a {label_fim}"

    return OutroPeriodoTotais(
        label=label,
        faturamento_total=faturamento_total,
        volume_total=volume_total,
        faturamento_por_tipologia=dict(faturamento_por_tipologia),
        qtde_por_tipologia=dict(qtde_por_tipologia),
        num_meses=num_meses,
        faturamento_por_formato={t: dict(f) for t, f in faturamento_por_formato.items()},
        qtde_por_formato={t: dict(f) for t, f in qtde_por_formato.items()},
        faturamento_por_cliente=dict(faturamento_por_cliente),
    )


def _agregar(registros: list[SaleRecord], ano_anterior: int, ano_atual: int,
             meses_comparados: list[int],
             periodo_atual_chaves: list[tuple[int, int]], periodo_anterior_chaves: list[tuple[int, int]],
             mes_atual_excluido: bool = False,
             comparar_ano_anterior: bool = True,
             outro_periodo: OutroPeriodoTotais | None = None) -> ResumoSellIn:
    faturamento_mensal = defaultdict(Decimal)
    volume_mensal = defaultdict(Decimal)
    faturamento_por_tipologia = defaultdict(lambda: defaultdict(Decimal))
    faturamento_tipologia_mensal = defaultdict(lambda: defaultdict(Decimal))
    qtde_por_tipologia = defaultdict(lambda: defaultdict(Decimal))
    qtde_tipologia_mensal = defaultdict(lambda: defaultdict(Decimal))
    dimensoes_nao_mapeadas = defaultdict(int)
    faturamento_por_formato = defaultdict(lambda: defaultdict(lambda: defaultdict(Decimal)))
    qtde_por_formato = defaultdict(lambda: defaultdict(lambda: defaultdict(Decimal)))
    faturamento_por_cliente = defaultdict(lambda: defaultdict(Decimal))

    chaves_atual = set(periodo_atual_chaves)
    chaves_anterior = set(periodo_anterior_chaves) if comparar_ano_anterior else set()

    for r in registros:
        chave_real = (r.ano, r.mes)
        if chave_real in chaves_atual:
            rotulo_ano = ano_atual
        elif chave_real in chaves_anterior:
            rotulo_ano = ano_anterior
        else:
            continue

        # Os totais mes a mes ficam guardados sob um "rotulo" de ano (ano_atual ou
        # ano_anterior) -- nao sob o ano REAL da venda. E' isso que permite ao periodo
        # cruzar a virada do ano (ex: Out/2025 a Fev/2026): outubro e' de um ano civil
        # diferente de fevereiro, mas os dois entram no mesmo grupo ("periodo atual").
        # Quem consome esses dicionarios (graficos, insights) nao muda nada: continua
        # indexando por (ano_atual|ano_anterior, mes), exatamente como sempre foi no
        # caso (mais comum) de um periodo dentro de um unico ano.
        chave_rotulada = (rotulo_ano, r.mes)

        faturamento_mensal[chave_rotulada] += r.valor
        volume_mensal[chave_rotulada] += r.qtde
        faturamento_por_cliente[rotulo_ano][r.cliente] += r.valor

        dimensao = find_dimension(r.produto)
        tipologia = TIPOLOGIA_POR_DIMENSAO.get(dimensao)
        if tipologia is None:
            dimensoes_nao_mapeadas[dimensao] += 1
            continue

        faturamento_por_tipologia[rotulo_ano][tipologia] += r.valor
        faturamento_tipologia_mensal[chave_rotulada][tipologia] += r.valor
        qtde_por_tipologia[rotulo_ano][tipologia] += r.qtde
        qtde_tipologia_mensal[chave_rotulada][tipologia] += r.qtde
        faturamento_por_formato[rotulo_ano][tipologia][dimensao] += r.valor
        qtde_por_formato[rotulo_ano][tipologia][dimensao] += r.qtde

    return ResumoSellIn(
        ano_anterior=ano_anterior,
        ano_atual=ano_atual,
        meses_comparados=meses_comparados,
        faturamento_mensal=dict(faturamento_mensal),
        volume_mensal=dict(volume_mensal),
        faturamento_por_tipologia={ano: dict(v) for ano, v in faturamento_por_tipologia.items()},
        faturamento_tipologia_mensal={chave: dict(v) for chave, v in faturamento_tipologia_mensal.items()},
        qtde_por_tipologia={ano: dict(v) for ano, v in qtde_por_tipologia.items()},
        qtde_tipologia_mensal={chave: dict(v) for chave, v in qtde_tipologia_mensal.items()},
        dimensoes_nao_mapeadas=dict(dimensoes_nao_mapeadas),
        faturamento_por_formato={ano: {t: dict(f) for t, f in tv.items()}
                                  for ano, tv in faturamento_por_formato.items()},
        qtde_por_formato={ano: {t: dict(f) for t, f in tv.items()}
                           for ano, tv in qtde_por_formato.items()},
        faturamento_por_cliente={ano: dict(v) for ano, v in faturamento_por_cliente.items()},
        mes_atual_excluido=mes_atual_excluido,
        comparar_ano_anterior=comparar_ano_anterior,
        outro_periodo=outro_periodo,
        periodo_atual_chaves=periodo_atual_chaves,
        periodo_anterior_chaves=periodo_anterior_chaves,
        rotulo_atual=_rotulo_periodo(periodo_atual_chaves, str(ano_atual)),
        rotulo_anterior=_rotulo_periodo(periodo_anterior_chaves, str(ano_anterior)),
    )
