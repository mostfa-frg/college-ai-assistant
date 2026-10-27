
from college_assistant.config import DATABASE_PATH
from college_assistant.storage.database import get_connection

print(f"Database: {DATABASE_PATH}")
print(f"Exists: {DATABASE_PATH.exists()}")

with get_connection() as connection:
    tables = connection.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        ORDER BY name
    """).fetchall()

    print("\nTables:")
    for table in tables:
        print(f"- {table['name']}")

    columns = connection.execute(
        "PRAGMA table_info(materials)"
    ).fetchall()

    print("\nMaterials columns:")
    for column in columns:
        print(f"- {column['name']}: {column['type']}")

        
from college_assistant.storage.repositories import list_materials

print("\nMaterial statuses:")

for material in list_materials("1326"):
    print(f"{material['status']:12} {material['title']}")