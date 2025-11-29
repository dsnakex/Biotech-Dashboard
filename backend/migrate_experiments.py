#!/usr/bin/env python3
"""
Migration script to add new columns to experiments table in PostgreSQL
"""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    print("❌ DATABASE_URL not found in .env file")
    print("Please uncomment the DATABASE_URL line in backend/.env")
    exit(1)

print("🔌 Connecting to PostgreSQL database...")
conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

print("📋 Adding new columns to experiments table...")

# List of columns to add
columns = [
    ("priority", "VARCHAR(50) DEFAULT 'medium'"),
    ("tags", "TEXT"),
    ("experiment_number", "VARCHAR(100)"),
    ("hypothesis", "TEXT"),
    ("objectives", "TEXT"),
    ("observations", "TEXT"),
    ("conclusion", "TEXT"),
    ("success_status", "VARCHAR(50)"),
    ("next_steps", "TEXT"),
    ("files_link", "VARCHAR(500)"),
    ("cost", "DECIMAL(10, 2)")
]

for col_name, col_type in columns:
    try:
        sql = f"ALTER TABLE experiments ADD COLUMN IF NOT EXISTS {col_name} {col_type}"
        cursor.execute(sql)
        print(f"  ✅ Added column: {col_name}")
    except Exception as e:
        print(f"  ⚠️  Column {col_name}: {e}")

conn.commit()
cursor.close()
conn.close()

print("\n✨ Migration completed successfully!")
print("You can now save experiments with the new fields in production.")
