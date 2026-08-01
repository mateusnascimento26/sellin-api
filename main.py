import os

from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, HTTPException

from adapters.outbound.openpyxl_spreadsheet_reader import OpenPyXLSpreadsheetReader
from adapters.outbound.sqlalchemy_sell_in_repository import SqlAlchemySellInRepository
from adapters.outbound.sqlalchemy_typology_repository import SqlAlchemyTypologyRepository
from application.use_cases.import_sell_in import ImportSellIn
from database import SessionLocal
from domain.exceptions import SpreadsheetReadError

load_dotenv()

app = FastAPI()

MAX_UPLOAD_SIZE_BYTES = int(os.getenv("MAX_UPLOAD_SIZE_BYTES", 20 * 1024 * 1024))


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=415, detail="Tipo ou extensão de arquivo não suportado. Envie um arquivo .xlsx.")

    content = await file.read()

    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Nenhum conteúdo foi enviado no arquivo.")

    if len(content) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="Arquivo acima do tamanho máximo permitido.")

    session = SessionLocal()
    try:
        use_case = ImportSellIn(
            spreadsheet_reader=OpenPyXLSpreadsheetReader(),
            sell_in_repository=SqlAlchemySellInRepository(session),
            typology_repository=SqlAlchemyTypologyRepository(session),
        )

        try:
            result = use_case.execute(content)
        except SpreadsheetReadError as exc:
            raise HTTPException(status_code=422, detail=str(exc))

        if result.status == "validation_error":
            session.rollback()
            if result.header_error:
                return {"status": "validation_error", "message": result.header_error}
            return {"status": "validation_error", "total_errors": result.total_errors, "errors": result.errors}

        session.commit()
        return {
            "status": "success",
            "total_rows": result.total_rows,
            "persisted_rows": result.persisted_rows,
            "skipped_rows": {"count": len(result.skipped_rows), "details": result.skipped_rows},
        }
    finally:
        session.close()