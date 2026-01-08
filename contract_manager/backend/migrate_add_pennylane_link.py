#!/usr/bin/env python3
"""
Migration script to add pennylane_customer_id column to customers table
"""
import sqlite3

db_path = "./contracts.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check if column already exists
cursor.execute("PRAGMA table_info(customers)")
columns = [row[1] for row in cursor.fetchall()]

if 'pennylane_customer_id' not in columns:
    print("Adding pennylane_customer_id column to customers table...")
    cursor.execute("ALTER TABLE customers ADD COLUMN pennylane_customer_id TEXT")
    cursor.execute("CREATE INDEX IF NOT EXISTS ix_customers_pennylane_customer_id ON customers (pennylane_customer_id)")
    conn.commit()
    print("Migration completed successfully!")
else:
    print("Column pennylane_customer_id already exists, skipping migration.")

conn.close()
