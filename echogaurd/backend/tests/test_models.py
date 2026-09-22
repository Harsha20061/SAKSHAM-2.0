import pytest
from sqlalchemy import UniqueConstraint
from app.db.models import User, Contact, CallSession, CallStatus, RiskEvent, RiskLevel

def test_models_import_successfully():
    """Verify that all models can be imported from the central module."""
    assert User is not None
    assert Contact is not None
    assert CallSession is not None
    assert RiskEvent is not None

def test_table_names():
    """Verify that table names are correctly set."""
    assert User.__tablename__ == "users"
    assert Contact.__tablename__ == "contacts"
    assert CallSession.__tablename__ == "call_sessions"
    assert RiskEvent.__tablename__ == "risk_events"

def test_primary_keys():
    """Verify that each model has an 'id' primary key."""
    assert User.__table__.c.id.primary_key
    assert Contact.__table__.c.id.primary_key
    assert CallSession.__table__.c.id.primary_key
    assert RiskEvent.__table__.c.id.primary_key

def test_foreign_keys():
    """Verify foreign keys are correctly configured."""
    # Contact foreign keys
    assert len(Contact.__table__.c.user_id.foreign_keys) == 1
    assert len(Contact.__table__.c.contact_user_id.foreign_keys) == 1

    # CallSession foreign keys
    assert len(CallSession.__table__.c.caller_id.foreign_keys) == 1
    assert len(CallSession.__table__.c.receiver_id.foreign_keys) == 1

    # RiskEvent foreign keys
    assert len(RiskEvent.__table__.c.call_id.foreign_keys) == 1

def test_unique_constraint_user_contact():
    """Verify unique constraint exists for user/contact pair."""
    table = Contact.__table__
    unique_constraints = [c for c in table.constraints if isinstance(c, UniqueConstraint)]

    found = False
    for uc in unique_constraints:
        cols = [col.name for col in uc.columns]
        if "user_id" in cols and "contact_user_id" in cols:
            found = True
            break

    assert found, "Unique constraint on user_id and contact_user_id not found in Contact model"

def test_risk_level_enum():
    """Verify RiskLevel enum supports only LOW/SUSPICIOUS/HIGH."""
    expected_values = {"LOW", "SUSPICIOUS", "HIGH"}
    actual_values = {level.value for level in RiskLevel}
    assert actual_values == expected_values

def test_risk_event_speaker_similarity_is_nullable():
    assert RiskEvent.__table__.c.speaker_similarity.nullable is True

def test_call_status_enum():
    """Verify CallStatus enum supports expected values."""
    expected_values = {"RINGING", "ACTIVE", "ENDED", "FAILED"}
    actual_values = {status.value for status in CallStatus}
    assert actual_values == expected_values
