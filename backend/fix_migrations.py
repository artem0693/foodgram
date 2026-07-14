import sqlite3

# Путь к твоей базе данных
db_path = 'db.sqlite3'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Удаляем только записи о миграциях 'recipes'
cursor.execute("DELETE FROM django_migrations WHERE app = 'recipes'")
conn.commit()
conn.close()

print("Миграции для 'recipes' успешно очищены.")