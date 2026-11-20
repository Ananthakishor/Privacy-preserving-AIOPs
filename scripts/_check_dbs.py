import sqlite3

for path in ['sentinelops.db', 'backend/sentinelops.db']:
    try:
        conn = sqlite3.connect(path)
        cols = [r[1] for r in conn.execute('PRAGMA table_info(metrics)').fetchall()]
        has_ds = 'data_source' in cols
        row_count = conn.execute('SELECT COUNT(*) FROM metrics').fetchone()[0]
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        print(f"{path}: metrics.data_source={has_ds}  rows={row_count}  tables={len(tables)}")
        print(f"  tables: {sorted(tables)}")
        conn.close()
    except Exception as e:
        print(f"{path}: ERROR {e}")
