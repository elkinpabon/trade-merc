"""Additive schema upgrade supported by both MySQL 8 and TiDB."""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from sqlalchemy import create_engine, inspect, text
from app.config import Config


def main():
    engine = create_engine(Config.SQLALCHEMY_DATABASE_URI, **Config.SQLALCHEMY_ENGINE_OPTIONS)
    with engine.begin() as connection:
        columns = {column['name'] for column in inspect(connection).get_columns('bot_configs')}
        if 'strategy_key' not in columns:
            connection.execute(text("ALTER TABLE bot_configs ADD COLUMN strategy_key VARCHAR(40) NOT NULL DEFAULT 'baseline-v1'"))
    engine.dispose()
    print('Strategy schema ready (historical data preserved)')


if __name__ == '__main__':
    main()
