from typing import Protocol


class SpreadsheetReader(Protocol):
    def read_export_sheet(self, content: bytes) -> tuple[list[str], list[list[object]]]:
        """Lê o arquivo e retorna (cabeçalho, linhas de dados) da aba 'Export'.

        Deve levantar SpreadsheetReadError se a aba não existir ou o arquivo
        estiver corrompido/protegido por senha.
        """
        ...