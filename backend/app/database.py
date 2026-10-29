from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from .core import DATABASE_URL
args = {'check_same_thread': False} if DATABASE_URL.startswith('sqlite') else {}
engine = create_engine(DATABASE_URL, connect_args=args)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
class Base(DeclarativeBase): pass
def get_db():
    db=SessionLocal()
    try: yield db
    finally: db.close()

def initialize_database(Base):
    """Create missing tables and apply small backwards-compatible SQLite changes."""
    Base.metadata.create_all(engine)
    columns={c['name'] for c in inspect(engine).get_columns('posts')}
    with engine.begin() as connection:
        if 'likes' not in columns: connection.exec_driver_sql('ALTER TABLE posts ADD COLUMN likes INTEGER NOT NULL DEFAULT 0')
        if 'image_url' not in columns: connection.exec_driver_sql('ALTER TABLE posts ADD COLUMN image_url VARCHAR(500)')
        if inspect(engine).has_table('requirements'):
            requirement_columns={c['name'] for c in inspect(engine).get_columns('requirements')}
            if 'contact_phone' not in requirement_columns: connection.exec_driver_sql('ALTER TABLE requirements ADD COLUMN contact_phone VARCHAR(32)')
        if inspect(engine).has_table('place_coordinates'):
            coordinate_columns={c['name'] for c in inspect(engine).get_columns('place_coordinates')}
            if 'state' not in coordinate_columns: connection.exec_driver_sql('ALTER TABLE place_coordinates ADD COLUMN state VARCHAR(100)')
            if 'district' not in coordinate_columns: connection.exec_driver_sql('ALTER TABLE place_coordinates ADD COLUMN district VARCHAR(100)')
