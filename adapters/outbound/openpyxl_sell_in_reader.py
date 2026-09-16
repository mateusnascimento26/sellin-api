import io
from decimal import Decimal

import openpyxl

from domain.entities.sale_record import SaleRecord
from domain.exceptions import SpreadsheetReadError


class OpenPyXLSellInReader:
    def read(self, file_content: bytes) -> list[SaleRecord]:
        try:
            workbook = openpyxl.load_workbook(io.BytesIO(file_content), data_only=True, read_only=True)
        except Exception as exc:
            raise SpreadsheetReadError(
                "Erro ao ler o arquivo: aba ausente, corrompido ou protegido por senha."
            ) from exc

        sheet = workbook["Export"] if "Export" in workbook.sheetnames else workbook[workbook.sheetnames[0]]
        rows = sheet.iter_rows(values_only=True)

        try:
            header = next(rows)
        except StopIteration:
            return []

        indice = {nome: posicao for posicao, nome in enumerate(header)}
        campos_necessarios = ("Data", "Produto", "Qtde", "Valor")
        if not all(campo in indice for campo in campos_necessarios):
            raise SpreadsheetReadError(
                "Erro ao ler o arquivo: colunas esperadas não encontradas (Data, Produto, Qtde, Valor)."
            )

        # "Cliente" nao e' uma coluna obrigatoria pra gerar os graficos/apresentacao
        # (so passa a ser usada no ranking de Top 10 clientes) -- se a planilha nao
        # tiver essa coluna, cai no default "Não informado" do SaleRecord.
        indice_cliente = indice.get("Cliente")

        registros: list[SaleRecord] = []
        for linha in rows:
            data = linha[indice["Data"]]
            valor = linha[indice["Valor"]]
            qtde = linha[indice["Qtde"]]
            if data is None or valor is None or qtde is None or not hasattr(data, "year"):
                continue

            valor_cliente = linha[indice_cliente] if indice_cliente is not None else None
            cliente = str(valor_cliente).strip() if valor_cliente is not None else ""
            if not cliente:
                cliente = "Não informado"

            registros.append(SaleRecord(
                ano=data.year,
                mes=data.month,
                produto=str(linha[indice["Produto"]] or ""),
                valor=Decimal(str(valor)),
                qtde=Decimal(str(qtde)),
                cliente=cliente,
            ))

        return registros