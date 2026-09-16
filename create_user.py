from database import SessionLocal, UserModel
from domain.value_objects.password import hash_password

username = input("Nome de usuário: ")
password = input("Senha: ")

with SessionLocal() as session:
    existing = session.query(UserModel).filter_by(username=username).first()
    if existing:
        print("Já existe um usuário com esse nome.")
    else:
        session.add(UserModel(username=username, password_hash=hash_password(password)))
        session.commit()
        print(f"Usuário '{username}' criado com sucesso.")