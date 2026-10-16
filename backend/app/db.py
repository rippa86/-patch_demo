import os
from collections.abc import Generator

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session, sessionmaker

from app.models import Base, Product

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "mysql+pymysql://webstore:webstore@mariadb:3306/webstore"
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=120,
    pool_size=10,
)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

SEED_PRODUCTS = [
    {
        "sku": "CEDAR-MUG",
        "name": "Cedar travel mug",
        "description": "Double-wall steel mug, 350 ml. One of three items in the lab catalog.",
        "price_cents": 2400,
        "stock": 50,
    },
    {
        "sku": "CANVAS-TOTE",
        "name": "Canvas tote",
        "description": "Heavy canvas tote with a short strap. Second of three catalog items.",
        "price_cents": 1800,
        "stock": 50,
    },
    {
        "sku": "FIELD-NOTE",
        "name": "Field notebook",
        "description": "A6 ruled notebook, 96 pages. Third of three catalog items.",
        "price_cents": 900,
        "stock": 50,
    },
]


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def galera_status(db: Session) -> dict[str, str]:
    rows = db.execute(text("SHOW STATUS LIKE 'wsrep%'")).all()
    return {name: value for name, value in rows}


def galera_synced(status: dict[str, str]) -> bool:
    return (
        status.get("wsrep_ready") == "ON"
        and status.get("wsrep_cluster_status") == "Primary"
        and status.get("wsrep_local_state_comment") == "Synced"
    )


def init_schema() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        count = db.scalar(select(Product.id).limit(1))
        if count is None:
            for item in SEED_PRODUCTS:
                db.add(Product(**item))
            db.commit()
