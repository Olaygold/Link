import psycopg2

conn = psycopg2.connect(
    dbname="liink_db",
    user="liink_db_user",
    password="bBozyyyaARlKGeElmudpAmcADsqFaths",
    host="dpg-d1dulomr433s73fr9da0-a",
    port=5432
)
cur = conn.cursor()

# Add the views column if it doesn't exist
cur.execute("""
    ALTER TABLE links ADD COLUMN IF NOT EXISTS views INTEGER DEFAULT 0;
""")

conn.commit()
cur.close()
conn.close()

print("✅ 'views' column added (if not exists).")
