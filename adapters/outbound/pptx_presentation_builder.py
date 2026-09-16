import io
from decimal import Decimal

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Emu, Inches, Pt

from domain.value_objects.periodo_comparativo_insights import InsightsComparativoPeriodos
from domain.value_objects.sell_in_insights import InsightsSellIn

LARGURA_SLIDE = Inches(13.333)
ALTURA_SLIDE = Inches(7.5)
LARGURA_PAINEL = Inches(4.2)

NAVY = RGBColor(0x1F, 0x4E, 0x79)
GRAY_BLUE = RGBColor(0x8F, 0xA6, 0xC7)
GOLD = RGBColor(0xD9, 0xA4, 0x41)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
DARK_TEXT = RGBColor(0x1F, 0x2A, 0x37)

VERDE_CERAMICA = RGBColor(0x4E, 0x9F, 0x63)
LARANJA_PORCELANATO = RGBColor(0xE0, 0x79, 0x3E)
ROXO_SUPER_PRIME = RGBColor(0x9B, 0x87, 0xC4)
MUTED_TEXT = RGBColor(0x6B, 0x72, 0x80)

FONTE = "Calibri"

CORES_TIPOLOGIA = {"Cerâmica": VERDE_CERAMICA, "Porcelanato": LARANJA_PORCELANATO, "Super Prime": ROXO_SUPER_PRIME}
CHAVES_ARQUIVO_TIPOLOGIA = {"Cerâmica": "ceramica", "Porcelanato": "porcelanato", "Super Prime": "super_prime"}
CHAVES_IMAGEM_TICKET_MEDIO = {
    "Cerâmica": "ticket_medio_ceramica.png",
    "Porcelanato": "ticket_medio_porcelanato.png",
    "Super Prime": "ticket_medio_super_prime.png",
}
CHAVES_IMAGEM_FATURAMENTO_TIPOLOGIA = {
    "Cerâmica": "faturamento_tipologia_ceramica.png",
    "Porcelanato": "faturamento_tipologia_porcelanato.png",
    "Super Prime": "faturamento_tipologia_super_prime.png",
}
CHAVES_IMAGEM_PARTICIPACAO_TIPOLOGIA = {
    "Cerâmica": "participacao_tipologia_ceramica.png",
    "Porcelanato": "participacao_tipologia_porcelanato.png",
    "Super Prime": "participacao_tipologia_super_prime.png",
}
IMAGEM_VOLUME_MENSAL = "volume_mensal.png"
IMAGEM_TICKET_MEDIO_GERAL = "ticket_medio_geral.png"
IMAGEM_CRESCIMENTO_TICKET_MEDIO = "crescimento_ticket_medio.png"
IMAGEM_DESEMPENHO_TIPOLOGIAS = "desempenho_tipologias.png"


class PythonPptxPresentationBuilder:
    def montar_apresentacao(self, insights_absoluto: InsightsSellIn, insights_comparativo: InsightsSellIn,
                             graficos: dict[str, bytes],
                             insights_periodos: InsightsComparativoPeriodos | None = None) -> bytes:
        """Monta a apresentacao a partir de UM UNICO periodo informado pelo usuario, em
        2 blocos fixos:

        Bloco 1 - so o periodo selecionado, sem nenhuma comparacao (slides 1-12)
        1) Capa
        2) Resumo executivo
        3-5) M² por tipologia (Ceramica, Porcelanato, Super Prime) -- com volume (m²)
        6) M² de todas as tipologias juntas
        7-9) Faturamento por tipologia (Ceramica, Porcelanato, Super Prime)
        10) Faturamento das 3 tipologias juntas
        11) Proporcao por m² e por faturamento lado a lado (2 barras empilhadas)
        12) Participacao mensal de cada tipologia (area empilhada)

        Bloco 2 - periodo selecionado vs mesmo periodo do ano anterior (slides 13-21)
        13) Resumo executivo, periodo x periodo
        14-16) M² por tipologia (Ceramica, Porcelanato, Super Prime) -- com volume (m²)
        17-19) Faturamento por tipologia (Ceramica, Porcelanato, Super Prime)
        20) Proporcao por m², periodo x periodo (2 barras empilhadas)
        21) Proporcao por faturamento, periodo x periodo (2 barras empilhadas)

        Bloco 3 (opcional, so aparece se insights_periodos for informado) - compara
        DOIS periodos livres escolhidos pelo usuario (podem ter duracoes diferentes,
        ex: Jan-Mar/2026 vs Mar-Jul/2025) -- slides 22-31
        22-24) M² por tipologia (Ceramica, Porcelanato, Super Prime) -- valor e volume
               lado a lado, periodo 1 x periodo 2
        25) M² de todas as tipologias juntas -- valor e volume lado a lado
        26-28) Faturamento por tipologia (Ceramica, Porcelanato, Super Prime)
        29) Faturamento das 3 tipologias juntas
        30) Proporcao por m², periodo 1 x periodo 2
        31) Proporcao por faturamento, periodo 1 x periodo 2

        Os demais graficos/slides (das versoes antigas do deck) continuam implementados
        abaixo, só não entram nesta ordem -- ficam guardados para uso futuro se precisar."""
        apresentacao = Presentation()
        apresentacao.slide_width = LARGURA_SLIDE
        apresentacao.slide_height = ALTURA_SLIDE
        layout_em_branco = apresentacao.slide_layouts[6]

        def novo_slide():
            return apresentacao.slides.add_slide(layout_em_branco)

        # Bloco 1 - so o periodo selecionado
        self._slide_capa(novo_slide(), insights_absoluto)
        self._slide_resumo_executivo(novo_slide(), insights_absoluto)

        for tipologia in ("Cerâmica", "Porcelanato", "Super Prime"):
            self._slide_ticket_medio(novo_slide(), insights_absoluto, graficos, tipologia, prefixo="abs_")

        self._slide_ticket_medio_tipologias_juntas(novo_slide(), insights_absoluto, graficos, prefixo="abs_")

        for tipologia in ("Cerâmica", "Porcelanato", "Super Prime"):
            self._slide_faturamento_tipologia(novo_slide(), insights_absoluto, graficos, tipologia, prefixo="abs_")

        self._slide_faturamento_tipologias_juntas(novo_slide(), insights_absoluto, graficos, prefixo="abs_")

        self._slide_proporcao_dupla(novo_slide(), insights_absoluto, graficos, prefixo="abs_")
        self._slide_tipologia_mensal(novo_slide(), insights_absoluto, graficos, prefixo="abs_")

        # Estudo de formatos dentro de cada tipologia -- sempre por ultimo no bloco.
        for tipologia in ("Cerâmica", "Porcelanato", "Super Prime"):
            self._slide_formatos_tipologia(novo_slide(), insights_absoluto, graficos, tipologia, prefixo="abs_")

        self._slide_ranking_clientes(novo_slide(), insights_absoluto, graficos, prefixo="abs_")

        # Bloco 2 - periodo selecionado vs mesmo periodo do ano anterior
        self._slide_resumo_executivo(novo_slide(), insights_comparativo)

        for tipologia in ("Cerâmica", "Porcelanato", "Super Prime"):
            self._slide_ticket_medio(novo_slide(), insights_comparativo, graficos, tipologia, prefixo="cmp_")

        for tipologia in ("Cerâmica", "Porcelanato", "Super Prime"):
            self._slide_faturamento_tipologia(novo_slide(), insights_comparativo, graficos, tipologia, prefixo="cmp_")

        self._slide_representatividade_volume(novo_slide(), insights_comparativo, graficos, prefixo="cmp_")
        self._slide_representatividade(novo_slide(), insights_comparativo, graficos, prefixo="cmp_")

        # Estudo de formatos dentro de cada tipologia -- sempre por ultimo no bloco.
        for tipologia in ("Cerâmica", "Porcelanato", "Super Prime"):
            self._slide_formatos_tipologia(novo_slide(), insights_comparativo, graficos, tipologia, prefixo="cmp_")

        self._slide_ranking_clientes(novo_slide(), insights_comparativo, graficos, prefixo="cmp_")

        # Bloco 3 (opcional) - periodo 1 livre x periodo 2 livre, escolhidos pelo usuario
        if insights_periodos is not None:
            for tipologia in ("Cerâmica", "Porcelanato", "Super Prime"):
                self._slide_periodo_m2_tipologia(novo_slide(), insights_periodos, graficos, tipologia)
            self._slide_periodo_m2_tipologias_juntas(novo_slide(), insights_periodos, graficos)

            for tipologia in ("Cerâmica", "Porcelanato", "Super Prime"):
                self._slide_periodo_faturamento_tipologia(novo_slide(), insights_periodos, graficos, tipologia)
            self._slide_periodo_faturamento_tipologias_juntas(novo_slide(), insights_periodos, graficos)

            self._slide_periodo_proporcao_volume(novo_slide(), insights_periodos, graficos)
            self._slide_periodo_proporcao_faturamento(novo_slide(), insights_periodos, graficos)

            # Estudo de formatos dentro de cada tipologia -- sempre por ultimo no bloco.
            for tipologia in ("Cerâmica", "Porcelanato", "Super Prime"):
                self._slide_periodo_formatos_tipologia(novo_slide(), insights_periodos, graficos, tipologia)

            self._slide_periodo_ranking_clientes(novo_slide(), insights_periodos, graficos)

        buffer = io.BytesIO()
        apresentacao.save(buffer)
        return buffer.getvalue()

    # ------------------------------------------------------------------ util

    def _painel_lateral(self, slide, titulo: str, periodo: str | None = None):
        painel = slide.shapes.add_shape(1, Emu(0), Emu(0), LARGURA_PAINEL, ALTURA_SLIDE)
        painel.fill.solid()
        painel.fill.fore_color.rgb = NAVY
        painel.line.fill.background()
        painel.shadow.inherit = False

        if periodo:
            # Badge com o periodo analisado, sempre visivel no topo do painel -- antes
            # essa informacao so aparecia (pequena, em italico) no rodape, o que fazia
            # passar despercebido qual periodo estava sendo mostrado. Agora fica logo
            # acima do titulo, em todo slide, destacada em dourado.
            caixa_periodo = slide.shapes.add_textbox(Inches(0.5), Inches(0.18),
                                                       LARGURA_PAINEL - Inches(1.0), Inches(0.32))
            tf_periodo = caixa_periodo.text_frame
            tf_periodo.word_wrap = True
            p_periodo = tf_periodo.paragraphs[0]
            p_periodo.text = periodo.upper()
            p_periodo.font.size = Pt(11)
            p_periodo.font.bold = True
            p_periodo.font.color.rgb = GOLD
            p_periodo.font.name = FONTE

        caixa_titulo = slide.shapes.add_textbox(Inches(0.5), Inches(0.55), LARGURA_PAINEL - Inches(1.0), Inches(1.4))
        tf = caixa_titulo.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = titulo
        p.font.size = Pt(26)
        p.font.bold = True
        p.font.color.rgb = WHITE
        p.font.name = FONTE

        return painel

    def _cabecalho(self, slide, titulo: str, periodo: str | None = None,
                   stats: list[tuple[str, str, "RGBColor | None"]] | None = None) -> float:
        """Novo cabecalho compacto no topo do slide, substituindo o antigo painel
        lateral em navy (removido a pedido do usuario, pra deixar o slide mais 'clean').
        Titulo + periodo ficam no canto superior esquerdo; ate 3 estatisticas-chave
        (valor + rotulo curto) ficam alinhadas a direita, na mesma faixa; uma linha
        fina dourada separa o cabecalho do grafico, que passa a ocupar quase o slide
        inteiro. Retorna a coordenada Y (em polegadas) onde o conteudo abaixo do
        cabecalho (titulo do grafico / imagem) deve comecar."""
        stats = stats or []

        caixa_titulo = slide.shapes.add_textbox(Inches(0.5), Inches(0.25), Inches(6.6), Inches(0.5))
        tf = caixa_titulo.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = titulo.replace("\n", " ")
        p.font.size = Pt(23)
        p.font.bold = True
        p.font.color.rgb = NAVY
        p.font.name = FONTE

        if periodo:
            caixa_periodo = slide.shapes.add_textbox(Inches(0.5), Inches(0.74), Inches(6.6), Inches(0.3))
            tfp = caixa_periodo.text_frame
            tfp.word_wrap = True
            pp = tfp.paragraphs[0]
            pp.text = periodo.upper()
            pp.font.size = Pt(11)
            pp.font.bold = True
            pp.font.color.rgb = MUTED_TEXT
            pp.font.name = FONTE

        n = len(stats)
        if n:
            largura_bloco = 2.55
            x_direita = 12.83  # LARGURA_SLIDE (13.333") - margem de 0.5"
            for i, (valor, rotulo, cor) in enumerate(stats):
                x = x_direita - largura_bloco * (n - i)
                caixa = slide.shapes.add_textbox(Inches(x), Inches(0.25), Inches(largura_bloco - 0.15), Inches(0.85))
                tfs = caixa.text_frame
                tfs.word_wrap = True
                tfs.margin_top = 0
                tfs.margin_bottom = 0
                ps = tfs.paragraphs[0]
                ps.text = valor
                ps.font.size = Pt(21)
                ps.font.bold = True
                ps.font.color.rgb = cor or NAVY
                ps.font.name = FONTE
                ps.alignment = PP_ALIGN.RIGHT
                pr = tfs.add_paragraph()
                pr.text = rotulo
                pr.font.size = Pt(9.5)
                pr.font.color.rgb = MUTED_TEXT
                pr.font.name = FONTE
                pr.alignment = PP_ALIGN.RIGHT

        linha = slide.shapes.add_shape(1, Inches(0.5), Inches(1.14), LARGURA_SLIDE - Inches(1.0), Pt(2))
        linha.fill.solid()
        linha.fill.fore_color.rgb = GOLD
        linha.line.fill.background()
        linha.shadow.inherit = False

        return 1.34

    def _slide_capa(self, slide, insights: InsightsSellIn):
        fundo = slide.shapes.add_shape(1, Emu(0), Emu(0), LARGURA_SLIDE, ALTURA_SLIDE)
        fundo.fill.solid()
        fundo.fill.fore_color.rgb = NAVY
        fundo.line.fill.background()
        fundo.shadow.inherit = False

        linha = slide.shapes.add_shape(1, Inches(1.0), Inches(3.55), Inches(1.4), Pt(4))
        linha.fill.solid()
        linha.fill.fore_color.rgb = GOLD
        linha.line.fill.background()
        linha.shadow.inherit = False

        caixa_titulo = slide.shapes.add_textbox(Inches(1.0), Inches(2.55), LARGURA_SLIDE - Inches(2.0), Inches(1.0))
        tf = caixa_titulo.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = "Análise Comercial Sell-in"
        p.font.size = Pt(44)
        p.font.bold = True
        p.font.color.rgb = WHITE
        p.font.name = FONTE

        caixa_subtitulo = slide.shapes.add_textbox(Inches(1.0), Inches(3.85), LARGURA_SLIDE - Inches(2.0), Inches(0.7))
        tf2 = caixa_subtitulo.text_frame
        p2 = tf2.paragraphs[0]
        if insights.periodo_cruza_ano:
            # periodo_label ja e' auto-descritivo quando cruza a virada do ano (ex:
            # "Out/25 a Fev/26") -- nao precisa (nem faz sentido) colar "de {ano}" ou
            # "{ano_anterior} x {ano_atual}" atras, como no caso de um ano so.
            subtitulo = f"{insights.periodo_label} — vs {insights.rotulo_anterior}" \
                if insights.comparar_ano_anterior else insights.periodo_label
        elif insights.comparar_ano_anterior:
            subtitulo = f"{insights.periodo_label} — {insights.rotulo_anterior} x {insights.rotulo_atual}"
        else:
            subtitulo = f"{insights.periodo_label} de {insights.rotulo_atual}"
        if insights.outro_periodo is not None:
            subtitulo += f" · vs {insights.outro_periodo.label}"
        p2.text = subtitulo
        p2.font.size = Pt(18)
        p2.font.color.rgb = GRAY_BLUE
        p2.font.name = FONTE

    def _cartao_resumo(self, slide, x: float, y: float, largura: float, altura: float,
                        rotulo: str, valor_atual: str, texto_anterior: str, cor_destaque):
        caixa_fundo = slide.shapes.add_shape(1, Inches(x), Inches(y), Inches(largura), Inches(altura))
        caixa_fundo.fill.solid()
        caixa_fundo.fill.fore_color.rgb = RGBColor(0xF2, 0xF4, 0xF8)
        caixa_fundo.line.fill.background()
        caixa_fundo.shadow.inherit = False

        caixa_texto = slide.shapes.add_textbox(Inches(x + 0.3), Inches(y + 0.25),
                                                Inches(largura - 0.6), Inches(altura - 0.5))
        tf = caixa_texto.text_frame
        tf.word_wrap = True

        p_rotulo = tf.paragraphs[0]
        p_rotulo.text = rotulo.upper()
        p_rotulo.font.size = Pt(13)
        p_rotulo.font.bold = True
        p_rotulo.font.color.rgb = MUTED_TEXT
        p_rotulo.font.name = FONTE
        p_rotulo.space_after = Pt(8)

        p_valor = tf.add_paragraph()
        p_valor.text = valor_atual
        p_valor.font.size = Pt(30)
        p_valor.font.bold = True
        p_valor.font.color.rgb = cor_destaque
        p_valor.font.name = FONTE
        p_valor.space_after = Pt(6)

        p_anterior = tf.add_paragraph()
        p_anterior.text = texto_anterior
        p_anterior.font.size = Pt(13)
        p_anterior.font.color.rgb = MUTED_TEXT
        p_anterior.font.name = FONTE

    def _slide_resumo_executivo(self, slide, insights: InsightsSellIn):
        self._cabecalho(slide, "Resumo Executivo", periodo=self._periodo_texto(insights))

        x_col1, x_col2 = 0.5, 6.87
        y_lin1, y_lin2 = 1.55, 4.45
        largura_cartao, altura_cartao = 5.96, 2.7

        texto_anterior = lambda valor_fmt, pct: (
            f"{insights.rotulo_anterior}: {valor_fmt} ({self._fmt_pct(pct)})" if insights.comparar_ano_anterior else ""
        )

        self._cartao_resumo(
            slide, x_col1, y_lin1, largura_cartao, altura_cartao, "Faturamento",
            self._fmt_mi(insights.faturamento_atual),
            texto_anterior(self._fmt_mi(insights.faturamento_anterior), insights.faturamento_variacao_pct),
            NAVY,
        )
        self._cartao_resumo(
            slide, x_col2, y_lin1, largura_cartao, altura_cartao, "Volume",
            self._fmt_mil(insights.volume_atual),
            texto_anterior(self._fmt_mil(insights.volume_anterior), insights.volume_variacao_pct),
            GOLD,
        )
        self._cartao_resumo(
            slide, x_col1, y_lin2, largura_cartao, altura_cartao, "Preço médio por m²",
            self._fmt_r_por_m2(insights.ticket_medio_geral_atual),
            texto_anterior(self._fmt_r_por_m2(insights.ticket_medio_geral_anterior), insights.ticket_medio_geral_variacao_pct),
            NAVY,
        )
        self._cartao_resumo(
            slide, x_col2, y_lin2, largura_cartao, altura_cartao, "Melhor mês",
            f"{insights.melhor_mes_label} ({self._fmt_mi(insights.melhor_mes_valor)})",
            (f"{insights.rotulo_anterior}: {insights.melhor_mes_anterior_label} "
             f"({self._fmt_mi(insights.melhor_mes_anterior_valor)})") if insights.comparar_ano_anterior else "",
            GOLD,
        )

    def _stat(self, slide, y: float, valor: str, rotulo: str, cor_valor=None, altura: float = 1.05):
        cor_valor = cor_valor or WHITE
        caixa = slide.shapes.add_textbox(Inches(0.5), Inches(y), LARGURA_PAINEL - Inches(0.9), Inches(altura))
        tf = caixa.text_frame
        tf.word_wrap = True
        tf.margin_top = 0
        tf.margin_bottom = 0

        p_valor = tf.paragraphs[0]
        p_valor.text = valor
        p_valor.font.size = Pt(30)
        p_valor.font.bold = True
        p_valor.font.color.rgb = cor_valor
        p_valor.font.name = FONTE
        p_valor.space_after = Pt(2)

        p_rotulo = tf.add_paragraph()
        p_rotulo.text = rotulo
        p_rotulo.font.size = Pt(12)
        p_rotulo.font.color.rgb = GRAY_BLUE
        p_rotulo.font.name = FONTE

        return caixa

    def _stat_tipologia(self, slide, y: float, valor_pct: str, nome_tipologia: str, rotulo: str, cor=None):
        cor = cor or WHITE
        caixa = slide.shapes.add_textbox(Inches(0.5), Inches(y), LARGURA_PAINEL - Inches(0.9), Inches(1.3))
        tf = caixa.text_frame
        tf.word_wrap = True
        tf.margin_top = 0
        tf.margin_bottom = 0

        p_valor = tf.paragraphs[0]
        p_valor.text = valor_pct
        p_valor.font.size = Pt(30)
        p_valor.font.bold = True
        p_valor.font.color.rgb = cor
        p_valor.font.name = FONTE
        p_valor.space_after = Pt(0)

        p_nome = tf.add_paragraph()
        p_nome.text = nome_tipologia
        p_nome.font.size = Pt(15)
        p_nome.font.bold = True
        p_nome.font.color.rgb = cor
        p_nome.font.name = FONTE
        p_nome.space_after = Pt(2)

        p_rotulo = tf.add_paragraph()
        p_rotulo.text = rotulo
        p_rotulo.font.size = Pt(11)
        p_rotulo.font.color.rgb = GRAY_BLUE
        p_rotulo.font.name = FONTE

        return caixa

    def _rodape_painel(self, slide, texto: str):
        caixa = slide.shapes.add_textbox(Inches(0.5), ALTURA_SLIDE - Inches(1.0),
                                          LARGURA_PAINEL - Inches(1.0), Inches(0.8))
        tf = caixa.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = texto
        p.font.size = Pt(10)
        p.font.italic = True
        p.font.color.rgb = GRAY_BLUE
        p.font.name = FONTE

    def _titulo_grafico(self, slide, texto: str, x=None, largura=None, tamanho_fonte: int = 20, y=None):
        x = x if x is not None else LARGURA_PAINEL + Inches(0.4)
        largura = largura if largura is not None else LARGURA_SLIDE - LARGURA_PAINEL - Inches(0.8)
        y = y if y is not None else Inches(0.4)
        caixa = slide.shapes.add_textbox(x, y, largura, Inches(0.4))
        tf = caixa.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = texto
        p.font.size = Pt(tamanho_fonte)
        p.font.bold = True
        p.font.color.rgb = DARK_TEXT
        p.font.name = FONTE

    def _grafico_cheio(self, slide, dados: bytes, y_topo: float = 1.34, titulo_grafico: str | None = None):
        """Grafico ocupando (quase) o slide inteiro, usado no novo layout sem painel
        lateral -- a margem esquerda/direita e' fixa em 0.5", so a altura disponivel
        muda conforme y_topo (logo abaixo do cabecalho compacto)."""
        x = Inches(0.5)
        largura = LARGURA_SLIDE - Inches(1.0)
        y = Inches(y_topo)
        if titulo_grafico:
            self._titulo_grafico(slide, titulo_grafico, x=x, largura=largura, y=y, tamanho_fonte=14)
            y = Inches(y_topo + 0.38)
        altura = ALTURA_SLIDE - y - Inches(0.3)
        self._imagem_ajustada(slide, dados, x, y, largura, altura)

    def _duas_imagens(self, slide, dados_esq: bytes, titulo_esq: str, dados_dir: bytes, titulo_dir: str,
                       y_topo: float = 1.34):
        """Duas imagens lado a lado (cada uma com seu proprio titulo pequeno em cima),
        dividindo a largura util do slide -- usado nos slides com 2 metricas/periodos
        lado a lado (ex: pizzas de volume x faturamento)."""
        margem = Inches(0.4)
        largura_meio = (LARGURA_SLIDE - Inches(1.0) - margem) / 2
        x_esq = Inches(0.5)
        x_dir = x_esq + largura_meio + margem

        self._titulo_grafico(slide, titulo_esq, x=x_esq, largura=largura_meio, y=Inches(y_topo), tamanho_fonte=14)
        self._titulo_grafico(slide, titulo_dir, x=x_dir, largura=largura_meio, y=Inches(y_topo), tamanho_fonte=14)
        y_img = Inches(y_topo + 0.38)
        altura = ALTURA_SLIDE - y_img - Inches(0.3)
        self._imagem_ajustada(slide, dados_esq, x_esq, y_img, largura_meio, altura)
        self._imagem_ajustada(slide, dados_dir, x_dir, y_img, largura_meio, altura)

    def _imagem_ajustada(self, slide, dados: bytes, x: Emu, y: Emu, largura_max: Emu, altura_max: Emu):
        from PIL import Image
        img = Image.open(io.BytesIO(dados))
        razao = img.width / img.height
        largura, altura = largura_max, int(largura_max / razao)
        if altura > altura_max:
            altura, largura = altura_max, int(altura_max * razao)
        pos_x = x + int((largura_max - largura) / 2)
        # Alinhado pelo topo (nao centralizado verticalmente) -- assim o grafico
        # comeca logo abaixo do titulo, em vez de sobrar um vao quando a imagem e'
        # mais baixa que o espaco disponivel (a folga fica embaixo, nao dividida
        # entre cima e baixo).
        pos_y = y
        slide.shapes.add_picture(io.BytesIO(dados), pos_x, pos_y, width=largura, height=altura)

    def _numero_br(self, valor: float, casas: int = 1) -> str:
        texto = f"{valor:,.{casas}f}"
        return texto.replace(",", "§").replace(".", ",").replace("§", ".")

    def _fmt_mi(self, valor: Decimal) -> str:
        return f"R$ {self._numero_br(float(valor) / 1_000_000, 0)} mi"

    def _fmt_mil(self, valor: Decimal) -> str:
        return f"{self._numero_br(float(valor) / 1_000, 0)}K m²"

    def _fmt_r_dinamico(self, valor: Decimal) -> str:
        """Formata um valor de faturamento em reais escolhendo a unidade mais legivel:
        'mi' (milhoes) a partir de R$ 1 milhao, senao 'K' (milhares) -- mesma logica
        do _fmt_faturamento_dinamico usado nos graficos. Usado no stat do cliente
        lider do ranking, que costuma ser bem menor que o faturamento de uma
        tipologia inteira (onde _fmt_mi, sempre em milhoes, funciona bem)."""
        valor_mil = float(valor) / 1_000
        if abs(valor_mil) >= 1000:
            return f"R$ {self._numero_br(valor_mil / 1000, 0)} mi"
        return f"R$ {self._numero_br(valor_mil, 0)}K"

    def _fmt_pct(self, valor: Decimal) -> str:
        sinal = "+" if valor >= 0 else ""
        return f"{sinal}{self._numero_br(float(valor), 0)}%"

    def _fmt_r_por_m2(self, valor: Decimal) -> str:
        return f"R$ {self._numero_br(float(valor), 0)}/m²"

    def _comparativo(self, insights: InsightsSellIn, pct: Decimal, valor_formatado: str) -> str:
        """Texto '(<pct> vs <valor> em <ano_anterior>)' para usar dentro de uma frase, ou
        vazio se a comparação com ano anterior não estiver ativa (modo absoluto)."""
        if not insights.comparar_ano_anterior:
            return ""
        return f" ({self._fmt_pct(pct)} vs {valor_formatado} em {insights.rotulo_anterior})"

    def _periodo_texto(self, insights: InsightsSellIn) -> str:
        """Texto curto identificando o(s) periodo(s) mostrados nos graficos do slide --
        usado no badge no topo do painel lateral, pra deixar sempre claro, de cara,
        qual periodo esta sendo analisado (sem precisar ler o rodape)."""
        if insights.periodo_cruza_ano:
            return f"{insights.periodo_label} vs {insights.rotulo_anterior}" \
                if insights.comparar_ano_anterior else insights.periodo_label
        if insights.comparar_ano_anterior:
            return f"{insights.periodo_label}: {insights.rotulo_anterior} x {insights.rotulo_atual}"
        return f"{insights.periodo_label} de {insights.rotulo_atual}"

    def _periodo_texto_bloco3(self, insights: InsightsComparativoPeriodos) -> str:
        """Mesma ideia de _periodo_texto, para os slides do bloco 3 (periodo 1 livre
        x periodo 2 livre, escolhidos pelo usuario)."""
        return f"{insights.periodo1_label} x {insights.periodo2_label}"

    def _formato_lider(self, totais: dict) -> tuple[str, Decimal]:
        """Formato com maior participacao dentro de um dicionario {formato: valor} --
        usado nos slides de 'estudo de formatos' pra destacar o formato mais vendido
        de cada tipologia no painel lateral."""
        if not totais:
            return "—", Decimal(0)
        total = sum(totais.values()) or Decimal(1)
        formato = max(totais, key=totais.get)
        return formato, (totais[formato] / total) * 100

    def _rodape_periodo(self, insights: InsightsSellIn, nota_extra: str = "", com_outro_periodo: bool = False) -> str:
        """Frase padrão de rodapé descrevendo o período analisado e a comparação ativa.
        com_outro_periodo=True adiciona uma nota sobre o outro período (só usado nos
        gráficos de barra que de fato desenham essa 3ª série)."""
        if insights.periodo_cruza_ano:
            base = (f"Período comparado: {insights.periodo_label} (vs {insights.rotulo_anterior})."
                    if insights.comparar_ano_anterior else
                    f"Período analisado: {insights.periodo_label} (sem comparação com ano anterior).")
        elif insights.comparar_ano_anterior:
            base = f"Período comparado: {insights.periodo_label} ({insights.rotulo_anterior} x {insights.rotulo_atual})."
        else:
            base = f"Período analisado: {insights.periodo_label} de {insights.rotulo_atual} (sem comparação com ano anterior)."
        if com_outro_periodo and insights.outro_periodo is not None:
            base += f" Também comparado com {insights.outro_periodo.label}."
        return base + nota_extra

    # --------------------------------------------------------------- slides

    def _slide_evolucao_mensal(self, slide, insights: InsightsSellIn, graficos: dict[str, bytes],
                                sufixo_titulo: str = "", mostrar_volume: bool = True):
        self._painel_lateral(slide, "Evolução Mensal\nde Faturamento", periodo=self._periodo_texto(insights))
        self._stat(slide, 2.1, self._fmt_mi(insights.faturamento_atual),
                    f"Faturamento em {insights.rotulo_atual}"
                    f"{self._comparativo(insights, insights.faturamento_variacao_pct, self._fmt_mi(insights.faturamento_anterior))}",
                    altura=1.3)
        if mostrar_volume:
            self._stat(slide, 3.55, self._fmt_mil(insights.volume_atual),
                        f"Volume vendido em {insights.rotulo_atual}"
                        f"{self._comparativo(insights, insights.volume_variacao_pct, self._fmt_mil(insights.volume_anterior))}",
                        cor_valor=GOLD, altura=1.3)
            y_melhor_mes = 5.0
        else:
            y_melhor_mes = 3.55
        self._stat(slide, y_melhor_mes, self._fmt_mi(insights.melhor_mes_valor),
                    f"Melhor mês em {insights.rotulo_atual}: {insights.melhor_mes_label}")
        nota_extra = " Mês em andamento excluído da comparação." if insights.mes_atual_excluido else ""
        self._rodape_painel(slide, self._rodape_periodo(insights, nota_extra, com_outro_periodo=True))

        self._titulo_grafico(slide, f"Faturamento mensal (R$ K){sufixo_titulo}")
        self._imagem_ajustada(slide, graficos["evolucao_mensal.png"],
                               LARGURA_PAINEL + Inches(0.4), Inches(1.0),
                               LARGURA_SLIDE - LARGURA_PAINEL - Inches(0.8), ALTURA_SLIDE - Inches(1.5))

    def _slide_representatividade(self, slide, insights: InsightsSellIn, graficos: dict[str, bytes],
                                   sufixo_titulo: str = "", prefixo: str = ""):
        stats = []
        if insights.tipologia_maior_alta:
            variacao = insights.tipologia_maior_alta_variacao_pp
            sinal = "+" if variacao >= 0 else ""
            stats.append((f"{sinal}{self._numero_br(float(variacao), 0)} p.p.",
                          f"Maior ganho: {insights.tipologia_maior_alta}", GOLD))

        y_topo = self._cabecalho(slide, "Proporção por Faturamento — Tipologia",
                                  periodo=self._periodo_texto(insights), stats=stats)
        self._duas_imagens(
            slide,
            graficos[f"{prefixo}pizza_faturamento_anterior.png"], f"{insights.rotulo_anterior}",
            graficos[f"{prefixo}pizza_faturamento_atual.png"], f"{insights.rotulo_atual}",
            y_topo,
        )

    def _slide_tipologia_mensal(self, slide, insights: InsightsSellIn, graficos: dict[str, bytes],
                                 sufixo_titulo: str = "", prefixo: str = ""):
        """Slide 'Análise por Tipologia' -- combina a participação mensal de cada
        tipologia no faturamento (área empilhada) com o crescimento mês a mês de cada
        uma (%), lado a lado, pra dar uma visão mais completa de como o mix de vendas
        está evoluindo dentro do próprio período."""
        y_topo = self._cabecalho(slide, "Análise por Tipologia", periodo=self._periodo_texto(insights), stats=[
            (insights.tipologia_dominante,
             f"Tipologia dominante ({float(insights.tipologia_dominante_pct_atual):.0f}% do faturamento)", NAVY),
        ])
        self._duas_imagens(
            slide,
            graficos[f"{prefixo}tipologia_mensal.png"], f"Participação mensal no faturamento (%){sufixo_titulo}",
            graficos[f"{prefixo}crescimento_tipologia_mensal.png"], "Crescimento mês a mês (%)",
            y_topo,
        )

    def _slide_evolucao_mensal_linha(self, slide, insights: InsightsSellIn, graficos: dict[str, bytes],
                                      sufixo_titulo: str = "", nota_mes_atual: bool = True):
        self._painel_lateral(slide, "Evolução Mensal", periodo=self._periodo_texto(insights))
        self._stat(slide, 2.1, self._fmt_mi(insights.faturamento_atual),
                    f"Faturamento em {insights.rotulo_atual} ({self._fmt_pct(insights.faturamento_variacao_pct)} "
                    f"vs {self._fmt_mi(insights.faturamento_anterior)} em {insights.rotulo_anterior})", altura=1.3)
        self._stat(slide, 3.55, self._fmt_mil(insights.volume_atual),
                    f"Volume vendido em {insights.rotulo_atual} ({self._fmt_pct(insights.volume_variacao_pct)} "
                    f"vs {self._fmt_mil(insights.volume_anterior)} em {insights.rotulo_anterior})",
                    cor_valor=GOLD, altura=1.3)
        self._stat(slide, 5.0, self._fmt_mi(insights.melhor_mes_valor),
                    f"Melhor mês em {insights.rotulo_atual}: {insights.melhor_mes_label}")
        nota_extra = " Mês em andamento excluído da comparação." if nota_mes_atual else ""
        self._rodape_painel(slide, f"Período comparado: {insights.periodo_label} "
                                    f"({insights.rotulo_anterior} x {insights.rotulo_atual}).{nota_extra}")

        self._titulo_grafico(slide, f"Faturamento mensal, ano a ano (R$ K) · Linha{sufixo_titulo}")
        self._imagem_ajustada(slide, graficos["evolucao_mensal_linha.png"],
                               LARGURA_PAINEL + Inches(0.4), Inches(1.0),
                               LARGURA_SLIDE - LARGURA_PAINEL - Inches(0.8), ALTURA_SLIDE - Inches(1.5))

    def _slide_representatividade_linha(self, slide, insights: InsightsSellIn, graficos: dict[str, bytes],
                                         sufixo_titulo: str = ""):
        self._painel_lateral(slide, "Representatividade\npor Tipologia", periodo=self._periodo_texto(insights))
        participacao_atual = insights.participacao_por_tipologia.get(insights.ano_atual, {})
        y = 2.15
        for tipologia in ("Cerâmica", "Porcelanato", "Super Prime"):
            pct = participacao_atual.get(tipologia, Decimal(0))
            self._stat_tipologia(slide, y, f"{self._numero_br(float(pct), 0)}%", tipologia,
                                  f"do faturamento em {insights.rotulo_atual}", cor=CORES_TIPOLOGIA[tipologia])
            y += 1.45

        if insights.tipologia_maior_alta:
            variacao = insights.tipologia_maior_alta_variacao_pp
            sinal = "+" if variacao >= 0 else ""
            self._rodape_painel(
                slide,
                f"{insights.tipologia_maior_alta} teve o maior ganho de participação: "
                f"{sinal}{self._numero_br(float(variacao), 0)} p.p. vs. {insights.rotulo_anterior}."
            )

        self._titulo_grafico(slide, f"Participação no faturamento — {insights.rotulo_anterior} x "
                                     f"{insights.rotulo_atual} · Linha{sufixo_titulo}")
        self._imagem_ajustada(slide, graficos["representatividade_linha.png"],
                               LARGURA_PAINEL + Inches(0.4), Inches(1.0),
                               LARGURA_SLIDE - LARGURA_PAINEL - Inches(0.8), ALTURA_SLIDE - Inches(1.5))

    def _slide_tipologia_mensal_linha(self, slide, insights: InsightsSellIn, graficos: dict[str, bytes],
                                       sufixo_titulo: str = ""):
        self._painel_lateral(slide, "Tendência Mensal\npor Tipologia", periodo=self._periodo_texto(insights))
        self._stat(slide, 2.1, insights.tipologia_dominante,
                    f"Tipologia dominante ({float(insights.tipologia_dominante_pct_atual):.0f}% do faturamento recente)")

        aviso_linhas = []
        if insights.dimensoes_nao_mapeadas:
            total_linhas = sum(insights.dimensoes_nao_mapeadas.values())
            dims = ", ".join(insights.dimensoes_nao_mapeadas.keys())
            aviso_linhas.append(f"{total_linhas} linha(s) com dimensão ainda sem tipologia cadastrada ({dims}) "
                                 f"não entraram nesta análise.")

        caixa = slide.shapes.add_textbox(Inches(0.5), Inches(3.4), LARGURA_PAINEL - Inches(1.0), Inches(2.5))
        tf = caixa.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = ("Acompanhamento mês a mês de como cada tipologia contribui para o faturamento total, "
                   "útil para identificar mudanças no mix de vendas.")
        p.font.size = Pt(13)
        p.font.color.rgb = WHITE
        p.font.name = FONTE

        if aviso_linhas:
            self._rodape_painel(slide, aviso_linhas[0])

        self._titulo_grafico(slide, f"Participação mensal de cada tipologia no faturamento · Linha{sufixo_titulo}")
        self._imagem_ajustada(slide, graficos["tipologia_mensal_linha.png"],
                               LARGURA_PAINEL + Inches(0.4), Inches(1.0),
                               LARGURA_SLIDE - LARGURA_PAINEL - Inches(0.8), ALTURA_SLIDE - Inches(1.5))

    def _slide_ticket_medio(self, slide, insights: InsightsSellIn, graficos: dict[str, bytes], tipologia: str,
                             prefixo: str = ""):
        cor = CORES_TIPOLOGIA[tipologia]

        tm_atual = insights.ticket_medio_atual.get(tipologia, Decimal(0))
        vol_atual = insights.volume_tipologia_atual.get(tipologia, Decimal(0))

        y_topo = self._cabecalho(slide, f"Preço por m² — {tipologia}", periodo=self._periodo_texto(insights),
                                  stats=[
                                      (self._fmt_r_por_m2(tm_atual), "Preço médio", cor),
                                      (self._fmt_mil(vol_atual), "Volume vendido", GOLD),
                                  ])

        self._grafico_cheio(slide, graficos[f"{prefixo}{CHAVES_IMAGEM_TICKET_MEDIO[tipologia]}"], y_topo,
                             titulo_grafico=f"Volume por m² — {tipologia}")

    def _slide_faturamento_tipologia(self, slide, insights: InsightsSellIn, graficos: dict[str, bytes],
                                      tipologia: str, prefixo: str = ""):
        cor = CORES_TIPOLOGIA[tipologia]
        fat_atual = insights.faturamento_tipologia_atual.get(tipologia, Decimal(0))

        y_topo = self._cabecalho(slide, f"Faturamento — {tipologia}", periodo=self._periodo_texto(insights),
                                  stats=[(self._fmt_mi(fat_atual), "Faturamento", cor)])

        self._grafico_cheio(slide, graficos[f"{prefixo}{CHAVES_IMAGEM_FATURAMENTO_TIPOLOGIA[tipologia]}"], y_topo,
                             titulo_grafico=f"Faturamento — {tipologia} (R$)")

    def _slide_participacao_tipologia(self, slide, insights: InsightsSellIn, graficos: dict[str, bytes],
                                       tipologia: str, desempenho_mensal: bool = False):
        cor = CORES_TIPOLOGIA[tipologia]
        titulo_painel = f"Desempenho Mensal\n{tipologia}" if desempenho_mensal else f"Participação\n{tipologia}"
        self._painel_lateral(slide, titulo_painel, periodo=self._periodo_texto(insights))

        pct_atual = insights.participacao_por_tipologia.get(insights.ano_atual, {}).get(tipologia, Decimal(0))

        if insights.comparar_ano_anterior:
            pct_anterior = insights.participacao_por_tipologia.get(insights.ano_anterior, {}).get(tipologia, Decimal(0))
            variacao_pp = pct_atual - pct_anterior
            sinal = "+" if variacao_pp >= 0 else ""
            rotulo_stat = (f"do faturamento em {insights.rotulo_atual} ({sinal}{self._numero_br(float(variacao_pp), 0)} "
                            f"p.p. vs {insights.rotulo_anterior})")
        else:
            rotulo_stat = f"do faturamento em {insights.rotulo_atual}"

        self._stat(slide, 2.3, f"{self._numero_br(float(pct_atual), 0)}%", rotulo_stat,
                    cor_valor=cor, altura=1.3)

        caixa = slide.shapes.add_textbox(Inches(0.5), Inches(4.0), LARGURA_PAINEL - Inches(1.0), Inches(2.2))
        tf = caixa.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        texto_desc = (f"Participação de {tipologia} no faturamento total, mês a mês, comparando os dois anos."
                      if insights.comparar_ano_anterior else
                      f"Participação de {tipologia} no faturamento total, mês a mês.")
        p.text = texto_desc
        p.font.size = Pt(13)
        p.font.color.rgb = WHITE
        p.font.name = FONTE

        self._rodape_painel(slide, self._rodape_periodo(insights))

        self._titulo_grafico(slide, f"Participação no faturamento — {tipologia} (%)")
        self._imagem_ajustada(slide, graficos[CHAVES_IMAGEM_PARTICIPACAO_TIPOLOGIA[tipologia]],
                               LARGURA_PAINEL + Inches(0.4), Inches(1.0),
                               LARGURA_SLIDE - LARGURA_PAINEL - Inches(0.8), ALTURA_SLIDE - Inches(1.5))
    def _slide_volume_mensal(self, slide, insights: InsightsSellIn, graficos: dict[str, bytes]):
        self._painel_lateral(slide, "Evolução Mensal\nde Volume", periodo=self._periodo_texto(insights))
        self._stat(slide, 2.1, self._fmt_mil(insights.volume_atual),
                    f"Volume vendido em {insights.rotulo_atual}"
                    f"{self._comparativo(insights, insights.volume_variacao_pct, self._fmt_mil(insights.volume_anterior))}",
                    cor_valor=GOLD, altura=1.3)

        caixa = slide.shapes.add_textbox(Inches(0.5), Inches(3.7), LARGURA_PAINEL - Inches(1.0), Inches(2.2))
        tf = caixa.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        texto_desc = ("Volume vendido (m²), mês a mês, comparando o período selecionado com o mesmo período "
                      "do ano anterior." if insights.comparar_ano_anterior else
                      "Volume vendido (m²), mês a mês, no período selecionado.")
        p.text = texto_desc
        p.font.size = Pt(13)
        p.font.color.rgb = WHITE
        p.font.name = FONTE

        self._rodape_painel(slide, self._rodape_periodo(insights, com_outro_periodo=True))

        self._titulo_grafico(slide, "Volume vendido, mês a mês (K m²)")
        self._imagem_ajustada(slide, graficos[IMAGEM_VOLUME_MENSAL],
                               LARGURA_PAINEL + Inches(0.4), Inches(1.0),
                               LARGURA_SLIDE - LARGURA_PAINEL - Inches(0.8), ALTURA_SLIDE - Inches(1.5))

    def _slide_valor_medio_mensal(self, slide, insights: InsightsSellIn, graficos: dict[str, bytes]):
        self._painel_lateral(slide, "Valor Médio\npor Unidade", periodo=self._periodo_texto(insights))
        self._stat(slide, 2.1, self._fmt_r_por_m2(insights.ticket_medio_geral_atual),
                    f"Valor médio em {insights.rotulo_atual}"
                    f"{self._comparativo(insights, insights.ticket_medio_geral_variacao_pct, self._fmt_r_por_m2(insights.ticket_medio_geral_anterior))}",
                    altura=1.3)

        caixa = slide.shapes.add_textbox(Inches(0.5), Inches(3.7), LARGURA_PAINEL - Inches(1.0), Inches(2.2))
        tf = caixa.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = ("Faturamento total dividido pelo volume total vendido (R$/m²), mês a mês, considerando "
                  "todas as tipologias juntas.")
        p.font.size = Pt(13)
        p.font.color.rgb = WHITE
        p.font.name = FONTE

        self._rodape_painel(slide, self._rodape_periodo(insights))

        self._titulo_grafico(slide, "Valor médio por unidade, mês a mês (R$/m²)")
        self._imagem_ajustada(slide, graficos[IMAGEM_TICKET_MEDIO_GERAL],
                               LARGURA_PAINEL + Inches(0.4), Inches(1.0),
                               LARGURA_SLIDE - LARGURA_PAINEL - Inches(0.8), ALTURA_SLIDE - Inches(1.5))

    def _slide_crescimento_ticket_medio(self, slide, insights: InsightsSellIn, graficos: dict[str, bytes]):
        self._painel_lateral(slide, "Crescimento Mensal\npor Unidade", periodo=self._periodo_texto(insights))
        if insights.comparar_ano_anterior:
            valor_stat = self._fmt_pct(insights.ticket_medio_geral_variacao_pct)
            rotulo_stat = (f"Variação do valor médio por unidade em {insights.periodo_label} de {insights.rotulo_atual} "
                            f"vs {insights.rotulo_anterior}")
        elif insights.outro_periodo is not None:
            tm_outro = insights.outro_periodo.ticket_medio
            variacao_outro = ((insights.ticket_medio_geral_atual / tm_outro - 1) * 100) if tm_outro else Decimal(0)
            valor_stat = self._fmt_pct(variacao_outro)
            rotulo_stat = (f"Variação do valor médio por unidade em {insights.periodo_label} de {insights.rotulo_atual} "
                            f"vs {insights.outro_periodo.label}")
        else:
            valor_stat = self._fmt_r_por_m2(insights.ticket_medio_geral_atual)
            rotulo_stat = f"Valor médio por unidade em {insights.periodo_label} de {insights.rotulo_atual} (sem comparação)"
        self._stat(slide, 2.1, valor_stat, rotulo_stat, altura=1.3)

        caixa = slide.shapes.add_textbox(Inches(0.5), Inches(3.7), LARGURA_PAINEL - Inches(1.0), Inches(2.2))
        tf = caixa.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        if insights.comparar_ano_anterior:
            base_comparacao = "o mesmo mês do ano anterior"
        elif insights.outro_periodo is not None:
            base_comparacao = f"a média mensal de {insights.outro_periodo.label}"
        else:
            base_comparacao = "nenhuma base de comparação selecionada"
        p.text = (f"Variação percentual, mês a mês, do valor médio por unidade (R$/m²) em relação a "
                  f"{base_comparacao}. Mostra se o preço praticado está subindo ou caindo.")
        p.font.size = Pt(13)
        p.font.color.rgb = WHITE
        p.font.name = FONTE

        self._rodape_painel(slide, self._rodape_periodo(insights, com_outro_periodo=True))

        self._titulo_grafico(slide, "Crescimento do valor médio por unidade, mês a mês (%)")
        self._imagem_ajustada(slide, graficos[IMAGEM_CRESCIMENTO_TICKET_MEDIO],
                               LARGURA_PAINEL + Inches(0.4), Inches(1.0),
                               LARGURA_SLIDE - LARGURA_PAINEL - Inches(0.8), ALTURA_SLIDE - Inches(1.5))

    def _slide_desempenho_tipologias(self, slide, insights: InsightsSellIn, graficos: dict[str, bytes]):
        self._painel_lateral(slide, "Desempenho Total\ndas Tipologias", periodo=self._periodo_texto(insights))
        y = 2.15
        for tipologia in ("Cerâmica", "Porcelanato", "Super Prime"):
            if insights.comparar_ano_anterior:
                variacao = insights.faturamento_tipologia_variacao_pct.get(tipologia, Decimal(0))
                valor_stat, rotulo_stat = self._fmt_pct(variacao), f"Crescimento de {tipologia}"
            elif insights.outro_periodo is not None:
                variacao = insights.faturamento_tipologia_variacao_outro_pct.get(tipologia, Decimal(0))
                valor_stat = self._fmt_pct(variacao)
                rotulo_stat = f"Crescimento de {tipologia} (vs {insights.outro_periodo.label})"
            else:
                valor_stat = self._fmt_mi(insights.faturamento_tipologia_atual.get(tipologia, Decimal(0)))
                rotulo_stat = f"Faturamento de {tipologia}"
            self._stat(slide, y, valor_stat, rotulo_stat,
                        cor_valor=CORES_TIPOLOGIA[tipologia], altura=1.05)
            y += 1.45

        self._rodape_painel(slide, self._rodape_periodo(insights, com_outro_periodo=True))

        titulo_periodos = f"{insights.rotulo_anterior} x {insights.rotulo_atual}" if insights.comparar_ano_anterior \
            else insights.rotulo_atual
        self._titulo_grafico(slide, f"Faturamento total por tipologia — {titulo_periodos}")
        self._imagem_ajustada(slide, graficos[IMAGEM_DESEMPENHO_TIPOLOGIAS],
                               LARGURA_PAINEL + Inches(0.4), Inches(1.0),
                               LARGURA_SLIDE - LARGURA_PAINEL - Inches(0.8), ALTURA_SLIDE - Inches(1.5))

    def _slide_ticket_medio_tipologias_juntas(self, slide, insights: InsightsSellIn, graficos: dict[str, bytes],
                                               prefixo: str = ""):
        """Slide 'Participação por Tipologia' -- passou a mostrar a % de participação
        de cada tipologia no volume (m²) vendido, em vez do volume absoluto de cada
        uma (que já aparecia nos slides individuais de cada tipologia)."""
        y_topo = self._cabecalho(slide, "Participação por Tipologia", periodo=self._periodo_texto(insights))
        self._grafico_cheio(slide, graficos[f"{prefixo}representatividade_volume.png"], y_topo,
                             titulo_grafico="Participação de cada tipologia no volume (m²)")

    def _slide_representatividade_volume(self, slide, insights: InsightsSellIn, graficos: dict[str, bytes],
                                          prefixo: str = ""):
        y_topo = self._cabecalho(slide, "Proporção por m² — Tipologia", periodo=self._periodo_texto(insights))
        self._duas_imagens(
            slide,
            graficos[f"{prefixo}pizza_volume_anterior.png"], f"{insights.rotulo_anterior}",
            graficos[f"{prefixo}pizza_volume_atual.png"], f"{insights.rotulo_atual}",
            y_topo,
        )

    def _slide_proporcao_dupla(self, slide, insights: InsightsSellIn, graficos: dict[str, bytes], prefixo: str = ""):
        """Um so slide com 2 graficos de pizza lado a lado: proporcao por m² e
        proporcao por faturamento, ambos do periodo selecionado (sem comparacao com
        ano anterior) -- ate a v5 do deck eram 2 barras empilhadas."""
        y_topo = self._cabecalho(slide, "Proporção por Tipologia", periodo=self._periodo_texto(insights))
        self._duas_imagens(
            slide,
            graficos[f"{prefixo}pizza_volume.png"], "Proporção por m² (%)",
            graficos[f"{prefixo}pizza_faturamento.png"], "Proporção por faturamento (%)",
            y_topo,
        )

    def _slide_faturamento_tipologias_juntas(self, slide, insights: InsightsSellIn, graficos: dict[str, bytes],
                                              prefixo: str = ""):
        y_topo = self._cabecalho(slide, "Faturamento — Todas as Tipologias", periodo=self._periodo_texto(insights),
                                  stats=[(self._fmt_mi(insights.faturamento_atual), "Faturamento total", NAVY)])
        self._grafico_cheio(slide, graficos[f"{prefixo}faturamento_tipologias.png"], y_topo,
                             titulo_grafico="Faturamento total — todas as tipologias (R$)")

    def _slide_formatos_tipologia(self, slide, insights: InsightsSellIn, graficos: dict[str, bytes],
                                   tipologia: str, prefixo: str = ""):
        """Estudo de formatos: participacao (%) de cada formato (ex: 33x46) DENTRO de
        uma tipologia, por volume (m²) vendido."""
        formato_vol, pct_vol = self._formato_lider(
            insights.qtde_por_formato.get(insights.ano_atual, {}).get(tipologia, {}))

        y_topo = self._cabecalho(slide, f"Formatos — {tipologia}", periodo=self._periodo_texto(insights), stats=[
            (formato_vol, f"Líder por volume ({self._numero_br(float(pct_vol), 0)}%)", GOLD),
        ])

        sufixo = CHAVES_ARQUIVO_TIPOLOGIA[tipologia]
        self._grafico_cheio(slide, graficos[f"{prefixo}formatos_{sufixo}_volume.png"], y_topo,
                             titulo_grafico="Participação de cada formato no volume (%)")

    def _slide_ranking_clientes(self, slide, insights: InsightsSellIn, graficos: dict[str, bytes], prefixo: str = ""):
        """Top 10 clientes por faturamento -- sempre por ultimo no bloco, depois do
        estudo de formatos. 1 barra por cliente no modo absoluto (Bloco 1), 2 barras
        (ano atual x anterior) quando ha comparacao (Bloco 2) -- o grafico em si ja'
        decide isso sozinho (ver gerar_grafico_ranking_clientes)."""
        faturamento_clientes_atual = insights.faturamento_por_cliente.get(insights.ano_atual, {})
        cliente_lider, pct_lider = self._formato_lider(faturamento_clientes_atual)
        valor_lider = faturamento_clientes_atual.get(cliente_lider, Decimal(0))

        y_topo = self._cabecalho(slide, "Ranking de Clientes", periodo=self._periodo_texto(insights), stats=[
            (self._fmt_r_dinamico(valor_lider),
             f"Líder: {cliente_lider} ({self._numero_br(float(pct_lider), 0)}%)", GOLD),
        ])

        self._grafico_cheio(slide, graficos[f"{prefixo}ranking_clientes.png"], y_topo,
                             titulo_grafico="Top 10 clientes por faturamento (R$)")

    # ------------------------------------- bloco 3: periodo livre x periodo livre

    def _slide_periodo_m2_tipologia(self, slide, insights: InsightsComparativoPeriodos, graficos: dict[str, bytes],
                                     tipologia: str):
        cor = CORES_TIPOLOGIA[tipologia]
        tm1 = insights.ticket_medio_tipologia_periodo1.get(tipologia, Decimal(0))
        vol1 = insights.volume_tipologia_periodo1.get(tipologia, Decimal(0))

        y_topo = self._cabecalho(slide, f"Preço por m² — {tipologia}", periodo=self._periodo_texto_bloco3(insights),
                                  stats=[
                                      (self._fmt_r_por_m2(tm1), f"Preço em {insights.periodo1_label}", cor),
                                      (self._fmt_mil(vol1), f"Volume em {insights.periodo1_label}", GOLD),
                                  ])

        sufixo = CHAVES_ARQUIVO_TIPOLOGIA[tipologia]
        self._duas_imagens(
            slide,
            graficos[f"periodo_ticket_medio_{sufixo}.png"], "Preço por m² (R$/m²)",
            graficos[f"periodo_volume_{sufixo}.png"], "Volume vendido (K m²)",
            y_topo,
        )

    def _slide_periodo_m2_tipologias_juntas(self, slide, insights: InsightsComparativoPeriodos,
                                             graficos: dict[str, bytes]):
        """Slide 'Participação por Tipologia' -- mesma logica do slide 6 do Bloco 1,
        so que aqui comparando periodo 1 x periodo 2 (a imagem ja existia, so passou
        a ser o grafico principal do slide em vez de compartilhar espaço com volume)."""
        y_topo = self._cabecalho(slide, "Participação por Tipologia", periodo=self._periodo_texto_bloco3(insights))
        self._grafico_cheio(slide, graficos["periodo_proporcao_volume.png"], y_topo,
                             titulo_grafico="Participação de cada tipologia no volume (m²)")

    def _slide_periodo_faturamento_tipologia(self, slide, insights: InsightsComparativoPeriodos,
                                              graficos: dict[str, bytes], tipologia: str):
        cor = CORES_TIPOLOGIA[tipologia]
        fat1 = insights.faturamento_tipologia_periodo1.get(tipologia, Decimal(0))

        y_topo = self._cabecalho(slide, f"Faturamento — {tipologia}", periodo=self._periodo_texto_bloco3(insights),
                                  stats=[(self._fmt_mi(fat1), f"Faturamento em {insights.periodo1_label}", cor)])

        sufixo = CHAVES_ARQUIVO_TIPOLOGIA[tipologia]
        self._grafico_cheio(slide, graficos[f"periodo_faturamento_{sufixo}.png"], y_topo,
                             titulo_grafico=f"Faturamento — {tipologia} (R$)")

    def _slide_periodo_faturamento_tipologias_juntas(self, slide, insights: InsightsComparativoPeriodos,
                                                       graficos: dict[str, bytes]):
        y_topo = self._cabecalho(slide, "Faturamento — Todas as Tipologias",
                                  periodo=self._periodo_texto_bloco3(insights))
        self._grafico_cheio(slide, graficos["periodo_faturamento_tipologias.png"], y_topo,
                             titulo_grafico="Faturamento total — todas as tipologias (R$)")

    def _slide_periodo_proporcao_volume(self, slide, insights: InsightsComparativoPeriodos,
                                         graficos: dict[str, bytes]):
        y_topo = self._cabecalho(slide, "Proporção por m² — Tipologia", periodo=self._periodo_texto_bloco3(insights))
        self._duas_imagens(
            slide,
            graficos["periodo_pizza_volume_p1.png"], f"{insights.periodo1_label}",
            graficos["periodo_pizza_volume_p2.png"], f"{insights.periodo2_label}",
            y_topo,
        )

    def _slide_periodo_proporcao_faturamento(self, slide, insights: InsightsComparativoPeriodos,
                                              graficos: dict[str, bytes]):
        y_topo = self._cabecalho(slide, "Proporção por Faturamento — Tipologia",
                                  periodo=self._periodo_texto_bloco3(insights))
        self._duas_imagens(
            slide,
            graficos["periodo_pizza_faturamento_p1.png"], f"{insights.periodo1_label}",
            graficos["periodo_pizza_faturamento_p2.png"], f"{insights.periodo2_label}",
            y_topo,
        )

    def _slide_periodo_formatos_tipologia(self, slide, insights: InsightsComparativoPeriodos,
                                           graficos: dict[str, bytes], tipologia: str):
        """Estudo de formatos, versao periodo 1 x periodo 2 (bloco 3) -- por volume (m²)."""
        formato_vol1, pct_vol1 = self._formato_lider(insights.qtde_por_formato_periodo1.get(tipologia, {}))

        y_topo = self._cabecalho(slide, f"Formatos — {tipologia}", periodo=self._periodo_texto_bloco3(insights),
                                  stats=[(formato_vol1,
                                          f"Líder em {insights.periodo1_label} ({self._numero_br(float(pct_vol1), 0)}%)",
                                          GOLD)])

        sufixo = CHAVES_ARQUIVO_TIPOLOGIA[tipologia]
        self._grafico_cheio(slide, graficos[f"periodo_formatos_{sufixo}_volume.png"], y_topo,
                             titulo_grafico="Participação de cada formato no volume (%)")

    def _slide_periodo_ranking_clientes(self, slide, insights: InsightsComparativoPeriodos,
                                         graficos: dict[str, bytes]):
        """Top 10 clientes por faturamento, versao periodo 1 x periodo 2 (bloco 3) --
        sempre por ultimo no bloco, depois do estudo de formatos."""
        cliente_lider, pct_lider = self._formato_lider(insights.faturamento_por_cliente_periodo1)
        valor_lider = insights.faturamento_por_cliente_periodo1.get(cliente_lider, Decimal(0))

        y_topo = self._cabecalho(slide, "Ranking de Clientes", periodo=self._periodo_texto_bloco3(insights),
                                  stats=[(self._fmt_r_dinamico(valor_lider),
                                          f"Líder em {insights.periodo1_label}: {cliente_lider} "
                                          f"({self._numero_br(float(pct_lider), 0)}%)", GOLD)])

        self._grafico_cheio(slide, graficos["periodo_ranking_clientes.png"], y_topo,
                             titulo_grafico="Top 10 clientes por faturamento (R$)")
