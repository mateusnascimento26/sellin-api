from dataclasses import dataclass
from decimal import Decimal


@dataclass
class SaleRecord:
    ano: int
    mes: int
    produto: str
    valor: Decimal
    qtde: Decimal
    # Nome do cliente (coluna "Cliente" da planilha) -- usado no ranking de Top 10
    # clientes por faturamento. Tem default pra nao quebrar quem ja constroi
    # SaleRecord sem esse campo (ex: testes antigos); a leitora usa "Não informado"
    # quando a coluna existe mas a celula esta vazia.
    cliente: str = "Não informado"