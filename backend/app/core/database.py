from sqlmodel import create_engine, SQLModel, Session
from app.core.config import settings

# Create database engine
# connect_args for SQLite compatibility (not needed for PostgreSQL, but harmless)
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,  # Log SQL queries in debug mode
    pool_pre_ping=True,   # Verify connections before using them
)


def create_db_and_tables():
    """
    Create all tables in the database.
    Call this on application startup.
    """
    SQLModel.metadata.create_all(engine)


def get_session():
    """
    Dependency function to get database session.
    Use with FastAPI's Depends().

    Example:
        @app.get("/items")
        def get_items(session: Session = Depends(get_session)):
            return session.query(Item).all()
    """
    with Session(engine) as session:
        yield session
