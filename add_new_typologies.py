from database import SessionLocal, TypologyModel

NEW_TYPOLOGIES = [
    ("Porcelanato", "50x100"),
    ("Super Prime", "33x66"),
    ("Porcelanato", "16x101"),
    ("Porcelanato", "24.5x101"),
]

with SessionLocal() as session:
    for category, dimension in NEW_TYPOLOGIES:
        exists = session.query(TypologyModel).filter_by(category=category, dimension=dimension).first()
        if exists:
            print(f"Já existe: {category} / {dimension}")
            continue
        session.add(TypologyModel(category=category, dimension=dimension))
        print(f"Inserido: {category} / {dimension}")
    session.commit()    