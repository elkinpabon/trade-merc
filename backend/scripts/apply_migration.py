import argparse
import os
import re
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.extensions import db


def main():
    parser = argparse.ArgumentParser(description='Apply one idempotent SQL migration')
    parser.add_argument('migration')
    args = parser.parse_args()

    migration_path = os.path.abspath(args.migration)
    if not os.path.isfile(migration_path):
        raise SystemExit(f'Migration not found: {migration_path}')

    with open(migration_path, 'r', encoding='utf-8') as migration_file:
        sql = re.sub(r'^\s*--.*$', '', migration_file.read(), flags=re.MULTILINE)
    statements = [statement.strip() for statement in sql.split(';') if statement.strip()]

    app = create_app()
    with app.app_context(), db.engine.begin() as connection:
        for statement in statements:
            connection.exec_driver_sql(statement)
    print({'migration': os.path.basename(migration_path), 'statements': len(statements), 'status': 'applied'})


if __name__ == '__main__':
    main()
