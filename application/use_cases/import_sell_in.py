from dataclasses import dataclass, field

from domain.entities.sell_in import SellIn
from domain.ports.sell_in_repository import SellInRepository
from domain.ports.spreadsheet_reader import SpreadsheetReader
from domain.ports.typology_repository import TypologyRepository
from domain.value_objects.cnpj import format_cnpj, is_valid_cnpj
from domain.value_objects.dimension import find_dimension
from domain.value_objects.parsing import parse_date, parse_decimal

EXPECTED_HEADERS = ["NF", "Cliente", "CNPJ", "Representante", "Cod Produto", "Produto", "Data", "Qtde", "Valor"]
REQUIRED_TEXT_FIELDS = ["NF", "Cliente", "CNPJ", "Representante", "Cod Produto", "Produto"]


@dataclass
class ImportResult:
    status: str
    message: str = ""
    total_rows: int = 0
    persisted_rows: int = 0
    total_errors: int = 0
    errors: list[dict] = field(default_factory=list)
    skipped_rows: list[dict] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.status == "success"


def _is_row_empty(row) -> bool:
    return all(value is None or str(value).strip() == "" for value in row)


def _is_footer_or_empty_row(row) -> bool:
    if _is_row_empty(row):
        return True
    cliente_empty = row[1] is None or str(row[1]).strip() == ""
    cnpj_empty = row[2] is None or str(row[2]).strip() == ""
    return cliente_empty and cnpj_empty


class ImportSellIn:
    def __init__(
        self,
        spreadsheet_reader: SpreadsheetReader,
        sell_in_repository: SellInRepository,
        typology_repository: TypologyRepository,
    ):
        self.spreadsheet_reader = spreadsheet_reader
        self.sell_in_repository = sell_in_repository
        self.typology_repository = typology_repository

    def execute(self, content: bytes) -> ImportResult:
        header, all_rows = self.spreadsheet_reader.read_export_sheet(content)

        if header != EXPECTED_HEADERS:
            return ImportResult(
                status="validation_error",
                message=(
                    "O cabeçalho da planilha não está no formato esperado. Verifique se a "
                    "primeira linha da aba 'Export' contém exatamente estas colunas, nesta "
                    "ordem: " + ", ".join(EXPECTED_HEADERS) + "."
                ),
                errors=[{
                    "row": 1,
                    "field": "cabeçalho",
                    "value": list(header),
                    "message": f"Esperado: {EXPECTED_HEADERS}. Encontrado: {list(header)}.",
                }],
            )

        last_real_index = -1
        for index, row in enumerate(all_rows):
            if not _is_footer_or_empty_row(row):
                last_real_index = index
        data_rows = all_rows[: last_real_index + 1]

        if not data_rows:
            return ImportResult(
                status="validation_error",
                message="A planilha não contém nenhuma linha de dados para importar.",
                errors=[{
                    "row": None,
                    "field": None,
                    "value": None,
                    "message": "Nenhuma linha de dados encontrada abaixo do cabeçalho.",
                }],
            )

        typologies_by_dimension = {t.dimension: t.id for t in self.typology_repository.list_all()}

        errors = []
        skipped_rows = []
        valid_records = []

        for index, row in enumerate(data_rows):
            row_number = index + 2

            if _is_row_empty(row):
                errors.append({
                    "row": row_number,
                    "field": None,
                    "value": None,
                    "message": "Linha vazia encontrada entre registros. Remova essa linha ou preencha os dados.",
                })
                continue

            row_dict = dict(zip(EXPECTED_HEADERS, row))
            row_errors = []

            for field_name in REQUIRED_TEXT_FIELDS:
                value = row_dict[field_name]
                if value is None or str(value).strip() == "":
                    row_errors.append({
                        "row": row_number,
                        "field": field_name,
                        "value": value,
                        "message": f"O campo '{field_name}' está vazio. Preencha esse campo e envie o arquivo novamente.",
                    })
                    continue
                if field_name == "CNPJ" and not is_valid_cnpj(str(value)):
                    row_errors.append({
                        "row": row_number,
                        "field": "CNPJ",
                        "value": value,
                        "message": "O CNPJ informado é inválido. Confira os números e o dígito verificador.",
                    })

            sale_date = parse_date(row_dict["Data"])
            if sale_date is None:
                row_errors.append({
                    "row": row_number,
                    "field": "Data",
                    "value": row_dict["Data"],
                    "message": "A data informada é inválida. Use o formato AAAA-MM-DD ou DD/MM/AAAA.",
                })

            quantity = parse_decimal(row_dict["Qtde"])
            if quantity is None:
                row_errors.append({
                    "row": row_number,
                    "field": "Qtde",
                    "value": row_dict["Qtde"],
                    "message": "O campo 'Qtde' deve conter um número válido.",
                })
            elif quantity <= 0:
                row_errors.append({
                    "row": row_number,
                    "field": "Qtde",
                    "value": row_dict["Qtde"],
                    "message": "A quantidade deve ser maior que zero.",
                })

            amount = parse_decimal(row_dict["Valor"])
            if amount is None:
                row_errors.append({
                    "row": row_number,
                    "field": "Valor",
                    "value": row_dict["Valor"],
                    "message": "O campo 'Valor' deve conter um número válido.",
                })
            elif amount < 0:
                row_errors.append({
                    "row": row_number,
                    "field": "Valor",
                    "value": row_dict["Valor"],
                    "message": "O valor não pode ser negativo.",
                })

            product_name = str(row_dict["Produto"] or "").strip()
            typology_id = None
            missing_typology = False
            dimension = None

            if not product_name:
                row_errors.append({
                    "row": row_number,
                    "field": "Produto",
                    "value": row_dict["Produto"],
                    "message": "O campo 'Produto' está vazio. Preencha esse campo e envie o arquivo novamente.",
                })
            else:
                dimension = find_dimension(product_name)
                typology_id = typologies_by_dimension.get(dimension) if dimension else None
                if typology_id is None:
                    missing_typology = True

            if row_errors:
                errors.extend(row_errors)
                continue

            if missing_typology:
                skipped_rows.append({
                    "row": row_number,
                    "product": product_name,
                    "detected_dimension": dimension,
                    "reason": "TYPOLOGY_NOT_FOUND",
                    "message": (
                        f"Não foi possível identificar uma tipologia cadastrada para a dimensão "
                        f"'{dimension}' no produto '{product_name}'. Essa linha não foi importada; "
                        f"cadastre a tipologia correspondente e reenvie o arquivo."
                    ),
                })
                continue

            valid_records.append(
                SellIn(
                    invoice_number=str(row_dict["NF"]).strip(),
                    customer_name=str(row_dict["Cliente"]).strip(),
                    customer_cnpj=format_cnpj(str(row_dict["CNPJ"])),
                    representative_name=str(row_dict["Representante"]).strip(),
                    product_code=str(row_dict["Cod Produto"]).strip(),
                    product_name=product_name,
                    sale_date=sale_date,
                    quantity=quantity,
                    amount=amount,
                    typology_id=typology_id,
                )
            )

        if errors:
            return ImportResult(
                status="validation_error",
                message=(
                    f"Encontramos {len(errors)} erro(s) na planilha. Nenhum dado foi importado. "
                    f"Corrija as linhas indicadas abaixo e envie o arquivo novamente."
                ),
                total_errors=len(errors),
                errors=errors[:50],
            )

        self.sell_in_repository.delete_all()
        self.sell_in_repository.save_all(valid_records)

        message = f"Arquivo importado com sucesso. {len(valid_records)} registro(s) processado(s) e salvo(s)."
        if skipped_rows:
            message += f" {len(skipped_rows)} linha(s) foram ignoradas por falta de tipologia cadastrada — veja 'skipped_rows'."

        return ImportResult(
            status="success",
            message=message,
            total_rows=len(data_rows),
            persisted_rows=len(valid_records),
            skipped_rows=skipped_rows[:50],
        )