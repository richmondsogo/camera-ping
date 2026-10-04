import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from alembic import command
from app.config import BACKEND_DIR
from app.database import Base, create_db_engine, create_sessionmaker


def get_alembic_config(db_url: str) -> Config:
    alembic_ini_path = BACKEND_DIR / "alembic.ini"
    cfg = Config(str(alembic_ini_path))
    cfg.set_main_option("sqlalchemy.url", db_url)
    return cfg


def test_migration_upgrade_downgrade_cycle(tmp_path: Path) -> None:
    """Verify upgrade head -> downgrade base -> upgrade head cycle."""
    db_file = tmp_path / "cycle_test.db"
    db_url = f"sqlite:///{db_file.as_posix()}"
    cfg = get_alembic_config(db_url)

    # 1. Upgrade from empty DB to head
    command.upgrade(cfg, "head")

    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cursor.fetchall()}
    assert "cameras" in tables
    assert "monitoring_state" in tables
    assert "alembic_version" in tables

    # Verify initial monitoring_state seed row
    cursor.execute("SELECT id, running FROM monitoring_state")
    assert cursor.fetchall() == [(1, 0)]

    # 2. Downgrade to base
    command.downgrade(cfg, "base")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables_after_down = {row[0] for row in cursor.fetchall()}
    assert "cameras" not in tables_after_down
    assert "monitoring_state" not in tables_after_down
    assert "alembic_version" in tables_after_down

    # 3. Upgrade to head again
    command.upgrade(cfg, "head")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables_again = {row[0] for row in cursor.fetchall()}
    assert "cameras" in tables_again
    assert "monitoring_state" in tables_again

    conn.close()


def test_schema_drift(tmp_path: Path) -> None:
    """Verify zero schema drift between migrated database and Base.metadata.

    Also explicitly verifies SQLite CHECK and UNIQUE constraint names in sqlite_master.
    """
    db_file = tmp_path / "drift_test.db"
    db_url = f"sqlite:///{db_file.as_posix()}"
    cfg = get_alembic_config(db_url)

    command.upgrade(cfg, "head")

    engine = create_db_engine(db_url)
    with engine.connect() as connection:
        mc = MigrationContext.configure(
            connection,
            opts={"compare_type": True, "compare_server_default": True},
        )
        diff = compare_metadata(mc, Base.metadata)
        assert diff == [], f"Schema drift detected: {diff}"

    engine.dispose()

    # Verify SQLite schema directly in sqlite_master
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='cameras'"
    )
    create_cameras_sql = cursor.fetchone()[0]

    cursor.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='monitoring_state'"
    )
    create_monitoring_sql = cursor.fetchone()[0]
    conn.close()

    assert "CONSTRAINT uq_cameras_ip_address UNIQUE (ip_address)" in create_cameras_sql
    assert "CONSTRAINT ck_cameras_status CHECK" in create_cameras_sql
    assert "CONSTRAINT ck_cameras_consecutive_failures CHECK" in create_cameras_sql

    assert "CONSTRAINT ck_monitoring_state_id CHECK (id = 1)" in create_monitoring_sql


def test_database_enforces_constraints(tmp_path: Path) -> None:
    """Verify raw SQL operations enforce UNIQUE, status CHECK, and failures CHECK."""
    db_file = tmp_path / "constraints_test.db"
    db_url = f"sqlite:///{db_file.as_posix()}"
    cfg = get_alembic_config(db_url)
    command.upgrade(cfg, "head")

    engine = create_db_engine(db_url)
    session_factory = create_sessionmaker(engine)
    session = session_factory()

    now_iso = datetime.now(UTC).isoformat()

    insert_sql = text("""
        INSERT INTO cameras (
            camera_name, location, description, ip_address, status,
            consecutive_failures, created_at, updated_at
        ) VALUES (
            :name, :loc, :desc, :ip, :status, :failures, :created, :updated
        )
    """)

    # Valid initial insert
    session.execute(
        insert_sql,
        {
            "name": "Cam 1",
            "loc": "Gate",
            "desc": "Entrance",
            "ip": "192.0.2.10",
            "status": "unknown",
            "failures": 0,
            "created": now_iso,
            "updated": now_iso,
        },
    )
    session.commit()

    # 1. Duplicate IP must fail UNIQUE constraint
    with pytest.raises(IntegrityError, match="UNIQUE constraint failed"):
        session.execute(
            insert_sql,
            {
                "name": "Cam 2",
                "loc": "Dock",
                "desc": "Loading Dock",
                "ip": "192.0.2.10",
                "status": "unknown",
                "failures": 0,
                "created": now_iso,
                "updated": now_iso,
            },
        )
        session.commit()
    session.rollback()

    # 2. Invalid status must fail status CHECK constraint
    with pytest.raises(IntegrityError, match="CHECK constraint failed"):
        session.execute(
            insert_sql,
            {
                "name": "Cam 2",
                "loc": "Dock",
                "desc": "Loading Dock",
                "ip": "192.0.2.11",
                "status": "invalid_status",
                "failures": 0,
                "created": now_iso,
                "updated": now_iso,
            },
        )
        session.commit()
    session.rollback()

    # 3. Negative consecutive_failures must fail failures CHECK constraint
    with pytest.raises(IntegrityError, match="CHECK constraint failed"):
        session.execute(
            insert_sql,
            {
                "name": "Cam 2",
                "loc": "Dock",
                "desc": "Loading Dock",
                "ip": "192.0.2.12",
                "status": "offline",
                "failures": -1,
                "created": now_iso,
                "updated": now_iso,
            },
        )
        session.commit()
    session.rollback()

    session.close()
    engine.dispose()


def test_monitoring_state_constraints(tmp_path: Path) -> None:
    """Verify raw SQL operations enforce id = 1 CHECK and uniqueness."""
    db_file = tmp_path / "monitoring_constraints.db"
    db_url = f"sqlite:///{db_file.as_posix()}"
    cfg = get_alembic_config(db_url)
    command.upgrade(cfg, "head")

    engine = create_db_engine(db_url)
    session_factory = create_sessionmaker(engine)
    session = session_factory()

    # Initial row with id=1 was seeded by migration
    row = session.execute(text("SELECT id, running FROM monitoring_state")).fetchone()
    assert row == (1, 0)

    # 1. Attempt to insert row with id != 1 must fail CHECK constraint
    with pytest.raises(IntegrityError, match="CHECK constraint failed"):
        session.execute(
            text("INSERT INTO monitoring_state (id, running) VALUES (2, 0)")
        )
        session.commit()
    session.rollback()

    with pytest.raises(IntegrityError, match="CHECK constraint failed"):
        session.execute(
            text("INSERT INTO monitoring_state (id, running) VALUES (0, 0)")
        )
        session.commit()
    session.rollback()

    # 2. Attempt to insert a second row with id = 1 must fail PRIMARY KEY / UNIQUE
    with pytest.raises(IntegrityError, match="UNIQUE constraint failed"):
        session.execute(
            text("INSERT INTO monitoring_state (id, running) VALUES (1, 1)")
        )
        session.commit()
    session.rollback()

    # 3. Attempt to update id away from 1 must fail CHECK constraint
    with pytest.raises(IntegrityError, match="CHECK constraint failed"):
        session.execute(text("UPDATE monitoring_state SET id = 2 WHERE id = 1"))
        session.commit()
    session.rollback()

    session.close()
    engine.dispose()
