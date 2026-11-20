"""Inspect existing DB schema vs models and apply missing column migrations."""
import sqlite3
import sys
sys.path.insert(0, 'backend')

conn = sqlite3.connect('sentinelops.db')
tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print("=== EXISTING TABLES ===")
for (tbl,) in sorted(tables):
    cols = [row[1] for row in conn.execute(f'PRAGMA table_info({tbl})').fetchall()]
    print(f"  {tbl}: {cols}")

print()
print("=== CHECKING REQUIRED COLUMNS ===")

# Column: metrics.data_source
cols = [r[1] for r in conn.execute("PRAGMA table_info(metrics)").fetchall()]
if 'data_source' not in cols:
    print("  MISSING: metrics.data_source  -> ADDING")
    conn.execute("ALTER TABLE metrics ADD COLUMN data_source TEXT DEFAULT 'live'")
    conn.commit()
    print("  ADDED: metrics.data_source")
else:
    print("  OK: metrics.data_source exists")

# Table: aiops_baselines
tables_list = [t[0] for t in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
if 'aiops_baselines' not in tables_list:
    print("  MISSING TABLE: aiops_baselines -> WILL BE CREATED BY init_db()")
else:
    print("  OK: aiops_baselines exists")

conn.close()
print()
print("Schema check complete.")
