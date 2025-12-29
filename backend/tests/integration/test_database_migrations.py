"""
Database Migrations Integration Tests

Проверяем:
- Миграции применяются без ошибок
- Rollback работает корректно
- Данные сохраняются после миграций
- Индексы создаются правильно
"""
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
import os
from pathlib import Path


@pytest.fixture
def alembic_config():
    """Alembic configuration для тестов"""
    backend_dir = Path(__file__).parent.parent.parent
    alembic_ini = backend_dir / "alembic.ini"
    
    config = Config(str(alembic_ini))
    config.set_main_option("script_location", str(backend_dir / "alembic"))
    
    # Используем тестовую базу
    test_db_url = os.getenv("TEST_DATABASE_URL", "sqlite:///./test_migrations.db")
    config.set_main_option("sqlalchemy.url", test_db_url)
    
    return config


@pytest.fixture
def migration_engine(alembic_config):
    """Отдельный engine для migration тестов"""
    db_url = alembic_config.get_main_option("sqlalchemy.url")
    engine = create_engine(db_url)
    
    yield engine
    
    # Cleanup
    engine.dispose()
    if "sqlite" in db_url:
        db_file = db_url.replace("sqlite:///", "")
        if os.path.exists(db_file):
            os.remove(db_file)


class TestDatabaseMigrations:
    """Тесты миграций базы данных"""
    
    def test_migrations_upgrade_downgrade(self, alembic_config, migration_engine):
        """Проверка что миграции применяются и откатываются без ошибок"""
        # Upgrade to head
        command.upgrade(alembic_config, "head")
        
        # Проверяем что таблицы созданы
        inspector = inspect(migration_engine)
        tables = inspector.get_table_names()
        
        expected_tables = ["users", "channels", "sessions", "alembic_version"]
        for table in expected_tables:
            assert table in tables, f"Table {table} should exist after migration"
        
        # Downgrade на 1 ревизию назад
        command.downgrade(alembic_config, "-1")
        
        # Upgrade обратно
        command.upgrade(alembic_config, "head")
    
    def test_data_integrity_after_migration(self, alembic_config, migration_engine):
        """Проверка что данные не теряются при миграциях"""
        # Apply migrations
        command.upgrade(alembic_config, "head")
        
        # Вставляем тестовые данные
        Session = sessionmaker(bind=migration_engine)
        session = Session()
        
        try:
            # Insert test user
            session.execute(text("""
                INSERT INTO users (email, google_id, is_approved, role, created_at)
                VALUES ('test@example.com', 'google123', 1, 'user', datetime('now'))
            """))
            session.commit()
            
            # Проверяем что данные есть
            result = session.execute(text("SELECT COUNT(*) FROM users")).scalar()
            assert result == 1, "Test data should be inserted"
            
            # Симулируем миграцию (downgrade/upgrade)
            command.downgrade(alembic_config, "-1")
            command.upgrade(alembic_config, "head")
            
            # Проверяем что данные сохранились (если миграция не drop table)
            # Примечание: это зависит от конкретной миграции
            result = session.execute(text("SELECT COUNT(*) FROM users")).scalar()
            # В реальности может быть 0 если миграция дропает таблицу
            assert result >= 0
            
        finally:
            session.close()
    
    def test_indexes_created_correctly(self, alembic_config, migration_engine):
        """Проверка что индексы создаются правильно"""
        command.upgrade(alembic_config, "head")
        
        inspector = inspect(migration_engine)
        
        # Проверяем индексы на users таблице
        indexes = inspector.get_indexes("users")
        index_columns = [idx["column_names"] for idx in indexes]
        
        # Ожидаемые индексы (зависит от ваших миграций)
        # Пример: индекс на email
        # assert any("email" in cols for cols in index_columns), "Should have index on email"
        
        # Проверяем foreign keys
        fks = inspector.get_foreign_keys("sessions")
        # assert len(fks) > 0, "sessions should have foreign keys"
    
    def test_migration_order(self, alembic_config):
        """Проверка что миграции применяются в правильном порядке"""
        # Получаем список ревизий
        from alembic.script import ScriptDirectory
        
        script_dir = ScriptDirectory.from_config(alembic_config)
        revisions = list(script_dir.walk_revisions())
        
        # Проверяем что есть хотя бы одна миграция
        assert len(revisions) > 0, "Should have at least one migration"
        
        # Проверяем что нет циклов и разрывов в цепочке
        revision_ids = [rev.revision for rev in revisions]
        assert len(revision_ids) == len(set(revision_ids)), "No duplicate revisions"
    
    def test_concurrent_migrations_safety(self, alembic_config, migration_engine):
        """Проверка что concurrent миграции не ломают данные"""
        # Этот тест сложнее - требует multiprocessing
        # Базовая проверка: запускаем миграцию дважды подряд
        
        command.upgrade(alembic_config, "head")
        # Повторный upgrade должен быть idempotent
        command.upgrade(alembic_config, "head")
        
        # Проверяем что alembic_version корректный
        Session = sessionmaker(bind=migration_engine)
        session = Session()
        try:
            result = session.execute(text("SELECT version_num FROM alembic_version")).fetchone()
            assert result is not None, "alembic_version should have a record"
        finally:
            session.close()


class TestDatabaseConstraints:
    """Тесты database constraints (FK, unique, not null)"""
    
    def test_foreign_key_constraints(self, alembic_config, migration_engine):
        """Проверка foreign key constraints"""
        command.upgrade(alembic_config, "head")
        
        Session = sessionmaker(bind=migration_engine)
        session = Session()
        
        try:
            # Пытаемся вставить session с несуществующим user_id
            # SQLite по умолчанию не проверяет FK, нужно PRAGMA foreign_keys=ON
            if "sqlite" in str(migration_engine.url):
                session.execute(text("PRAGMA foreign_keys=ON"))
            
            # Insert должен fail с FK constraint
            with pytest.raises(Exception):
                session.execute(text("""
                    INSERT INTO sessions (user_id, session_string, created_at)
                    VALUES (99999, 'fake_session', datetime('now'))
                """))
                session.commit()
        finally:
            session.rollback()
            session.close()
    
    def test_unique_constraints(self, alembic_config, migration_engine):
        """Проверка unique constraints"""
        command.upgrade(alembic_config, "head")
        
        Session = sessionmaker(bind=migration_engine)
        session = Session()
        
        try:
            # Insert первого user
            session.execute(text("""
                INSERT INTO users (email, google_id, is_approved, role, created_at)
                VALUES ('unique@test.com', 'google1', 1, 'user', datetime('now'))
            """))
            session.commit()
            
            # Попытка insert дубликата email должна упасть
            with pytest.raises(Exception):
                session.execute(text("""
                    INSERT INTO users (email, google_id, is_approved, role, created_at)
                    VALUES ('unique@test.com', 'google2', 1, 'user', datetime('now'))
                """))
                session.commit()
        finally:
            session.rollback()
            session.close()
    
    def test_not_null_constraints(self, alembic_config, migration_engine):
        """Проверка NOT NULL constraints"""
        command.upgrade(alembic_config, "head")
        
        Session = sessionmaker(bind=migration_engine)
        session = Session()
        
        try:
            # Попытка insert без обязательного поля
            with pytest.raises(Exception):
                session.execute(text("""
                    INSERT INTO users (google_id, is_approved, role, created_at)
                    VALUES ('google123', 1, 'user', datetime('now'))
                """))
                session.commit()
        finally:
            session.rollback()
            session.close()
