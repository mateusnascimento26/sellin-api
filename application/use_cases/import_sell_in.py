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
    total_rows: int = 0
    persisted_rows: int = 0
    total_errors: int = 0
    errors: list[dict] = field(default_factory=list)
    skipped_rows: list[dict] = field(default_factory=list)
    header_error: str | None = None


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
                header_error=f"Cabeçalho inválido. Esperado: {EXPECTED_HEADERS}. Recebido: {header}",
            )

        last_real_index = -1
        for index, row in enumerate(all_rows):
            if not _is_footer_or_empty_row(row):
                last_real_index = index
        data_rows = all_rows[: last_real_index + 1]

        if not data_rows:
            return ImportResult(status="validation_error", header_error="A planilha não contém nenhuma linha de dados.")

        typologies_by_dimension = {t.dimension: t.id for t in self.typology_repository.list_all()}

        errors = []
        skipped_rows = []
        valid_records = []

        for index, row in enumerate(data_rows):
            row_number = index + 2

            if _is_row_empty(row):
                errors.append({"row": row_number, "field": None, "value": None, "message": "Linha vazia encontrada entre registros."})
                continue

            row_dict = dict(zip(EXPECTED_HEADERS, row))
            row_errors = []

            for field_name in REQUIRED_TEXT_FIELDS:
                value = row_dict[field_name]
                if value is None or str(value).strip() == "":
                    row_errors.append({"row": row_number, "field": field_name, "value": value, "message": f"O campo '{field_name}' é obrigatório."})
                    continue
                if field_name == "CNPJ" and not is_valid_cnpj(str(value)):
                    row_errors.append({"row": row_number, "field": "CNPJ", "value": value, "message": "O CNPJ informado é inválido."})

            sale_date = parse_date(row_dict["Data"])
            if sale_date is None:
                row_errors.append({"row": row_number, "field": "Data", "value": row_dict["Data"], "message": "A data informada é inválida."})

            quantity = parse_decimal(row_dict["Qtde"])
            if quantity is None:
                row_errors.append({"row": row_number, "field": "Qtde", "value": row_dict["Qtde"], "message": "O campo 'Qtde' deve ser numérico e obrigatório."})
            elif quantity <= 0:
                row_errors.append({"row": row_number, "field": "Qtde", "value": row_dict["Qtde"], "message": "A quantidade deve ser maior que zero."})

            amount = parse_decimal(row_dict["Valor"])
            if amount is None:
                row_errors.append({"row": row_number, "field": "Valor", "value": row_dict["Valor"], "message": "O campo 'Valor' deve ser numérico e obrigatório."})
            elif amount < 0:
                row_errors.append({"row": row_number, "field": "Valor", "value": row_dict["Valor"], "message": "O valor não pode ser negativo."})

            product_name = str(row_dict["Produto"] or "").strip()
            typology_id = None
            missing_typology = False
            dimension = None

            if not product_name:
                row_errors.append({"row": row_number, "field": "Produto", "value": row_dict["Produto"], "message": "O campo 'Produto' é obrigatório."})
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
            return ImportResult(status="validation_error", total_errors=len(errors), errors=errors[:50])

        self.sell_in_repository.delete_all()
        self.sell_in_repository.save_all(valid_records)

        return ImportResult(
            status="success",
            total_rows=len(data_rows),
            persisted_rows=len(valid_records),
            skipped_rows=skipped_rows[:50],
        )