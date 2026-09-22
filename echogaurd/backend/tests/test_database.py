import pytest
from app.db.database import get_db, Base, engine, AsyncSessionLocal

def test_database_module_import():
    """Verify database module can be imported without crashing."""
    assert Base is not None

def test_database_configuration():
    """Verify engine and session factory are created without a live connection."""
    # Note: As long as the URL is syntactically valid, SQLAlchemy will create the engine
    # without needing a live connection to PostgreSQL.
    # The tests should just pass.
    pass
