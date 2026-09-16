import io
import os
import zipfile
from contextlib import asynccontextmanager
from datetime import date

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, UploadFile, File, HTTPException, status
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from adapters.outbound.matplotlib_chart_generator import MatplotlibChartGenerator
from adapters.outbound.openpyxl_sell_in_reader import OpenPyXLSellInReader
from adapters.outbound.openpyxl_spreadsheet_reader import OpenPyXLSpreadsheetReader
from adapters.outbound.pptx_presentation_builder import PythonPptxPresentationBuilder
from adapters.outbound.sqlalchemy_sell_in_repository import SqlAlchemySellInRepository
from adapters.outbound.sqlalchemy_typology_repository import SqlAlchemyTypologyRepository
from adapters.outbound.sqlalchemy_user_repository import SqlAlchemyUserRepository
from application.use_cases.generate_sell_in_charts import GenerateSellInCharts
from application.use_cases.generate_sell_in_presentation import GenerateSellInPresentation
from application.use_cases.import_sell_in import ImportSellIn
from application.use_cases.login import Login
from database import SessionLocal, UserModel, create_tables_and_seed
from domain.exceptions import SpreadsheetReadError
from domain.value_objects.jwt_token import decode_access_token
from domain.value_objects.password import hash_password

load_dotenv()


def _seed_admin_user_se_configurado() -> None:
    """Cria automaticamente um usuário de login a partir das variáveis de ambiente
    ADMIN_USERNAME/ADMIN_PASSWORD, se elas existirem e esse usuário ainda não
    existir -- só pra permitir configurar o primeiro login num banco novo (ex: na
    nuvem) sem precisar de acesso a um terminal/shell pra rodar create_user.py."""
    admin_username = os.getenv("ADMIN_USERNAME")
    admin_password = os.getenv("ADMIN_PASSWORD")
    if not admin_username or not admin_password:
        return

    session = SessionLocal()
    try:
        if session.query(UserModel).filter_by(username=admin_username).first() is None:
            session.add(UserModel(username=admin_username, password_hash=hash_password(admin_password)))
            session.commit()
            print(f"Usuário '{admin_username}' criado a partir de ADMIN_USERNAME/ADMIN_PASSWORD.")
    finally:
        session.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Cria as tabelas (se ainda não existirem) e semeia as tipologias iniciais e o
    # usuário admin (se configurado) assim que a API sobe -- importante pra rodar
    # num banco novo na nuvem sem precisar rodar scripts manualmente antes.
    create_tables_and_seed()
    _seed_admin_user_se_configurado()
    yield


app = FastAPI(lifespan=lifespan)

MAX_UPLOAD_SIZE_BYTES = int(os.getenv("MAX_UPLOAD_SIZE_BYTES", 20 * 1024 * 1024))
SECRET_KEY = os.getenv("SECRET_KEY")

security = HTTPBearer()

def get_current_username(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    username = decode_access_token(credentials.credentials, SECRET_KEY)
    if username is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido ou expirado.")
    return username

class LoginRequest(BaseModel):
    username: str
    password: str

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/login")
def login(credentials: LoginRequest):
    session = SessionLocal()
    try:
        use_case = Login(user_repository=SqlAlchemyUserRepository(session), secret_key=SECRET_KEY)
        result = use_case.execute(credentials.username, credentials.password)

        if not result.success:
            raise HTTPException(status_code=401, detail=result.error)

        return {"access_token": result.token, "token_type": "bearer"}
    finally:
        session.close()

@app.post("/upload")
async def upload(file: UploadFile = File(...), current_username: str = Depends(get_current_username)):
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

        if not result.ok:
            session.rollback()
        else:
            session.commit()

        return {
            "ok": result.ok,
            "status": result.status,
            "message": result.message,
            "total_rows": result.total_rows,
            "persisted_rows": result.persisted_rows,
            "total_errors": result.total_errors,
            "errors": result.errors,
            "skipped_rows": result.skipped_rows,
        }
    finally:
        session.close()

@app.post("/graficos")
async def graficos(file: UploadFile = File(...), current_username: str = Depends(get_current_username)):
    if not file.filename or not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=415, detail="Tipo ou extensão de arquivo não suportado. Envie um arquivo .xlsx.")

    content = await file.read()

    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Nenhum conteúdo foi enviado no arquivo.")

    if len(content) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="Arquivo acima do tamanho máximo permitido.")

    use_case = GenerateSellInCharts(
        sell_in_reader=OpenPyXLSellInReader(),
        chart_generator=MatplotlibChartGenerator(),
    )

    try:
        result = use_case.execute(content)
    except SpreadsheetReadError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    if not result.ok:
        raise HTTPException(status_code=422, detail=result.message)

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as arquivo_zip:
        for nome, dados in result.graficos.items():
            arquivo_zip.writestr(nome, dados)
    buffer.seek(0)

    headers = {"Content-Disposition": "attachment; filename=graficos_sellin.zip"}
    if result.dimensoes_nao_mapeadas:
        aviso = "; ".join(f"{dim}: {qtd} linha(s)" for dim, qtd in result.dimensoes_nao_mapeadas.items())
        headers["X-Dimensoes-Sem-Tipologia"] = aviso

    return StreamingResponse(buffer, media_type="application/zip", headers=headers)

@app.get("/apresentacao")
async def apresentacao(
    file: UploadFile = File(...),
    data_inicial: date | None = None,
    data_final: date | None = None,
    data_inicial_2: date | None = None,
    data_final_2: date | None = None,
    current_username: str = Depends(get_current_username),
):
    if not file.filename or not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=415, detail="Tipo ou extensão de arquivo não suportado. Envie um arquivo .xlsx.")

    content = await file.read()

    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Nenhum conteúdo foi enviado no arquivo.")

    if len(content) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="Arquivo acima do tamanho máximo permitido.")

    use_case = GenerateSellInPresentation(
        sell_in_reader=OpenPyXLSellInReader(),
        chart_generator=MatplotlibChartGenerator(),
        presentation_builder=PythonPptxPresentationBuilder(),
    )

    try:
        result = use_case.execute(content, data_inicial=data_inicial, data_final=data_final,
                                   data_inicial_2=data_inicial_2, data_final_2=data_final_2)
    except SpreadsheetReadError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    if not result.ok:
        raise HTTPException(status_code=422, detail=result.message)

    headers = {"Content-Disposition": "attachment; filename=apresentacao_sellin.pptx"}
    if result.dimensoes_nao_mapeadas:
        aviso = "; ".join(f"{dim}: {qtd} linha(s)" for dim, qtd in result.dimensoes_nao_mapeadas.items())
        headers["X-Dimensoes-Sem-Tipologia"] = aviso

    return StreamingResponse(
        io.BytesIO(result.apresentacao),
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers=headers,
    )