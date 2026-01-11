#!/usr/bin/env python3
from src.core.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    result = conn.execute(text("SELECT indexname FROM pg_indexes WHERE tablename='sessions' ORDER BY indexname"))
    indexes = [row[0] for row in result]
    print("Indexes on sessions table:")
    for idx in indexes:
        print(f"  - {idx}")
    
    print(f"\nHas ix_sessions_gate_id: {'ix_sessions_gate_id' in indexes}")
    print(f"Has ix_sessions_stay_id: {'ix_sessions_stay_id' in indexes}")
    
    # Check columns
    result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='sessions' AND column_name IN ('gate_id', 'stay_id')"))
    cols = [row[0] for row in result]
    print(f"\nColumns in sessions:")
    print(f"  Has gate_id: {'gate_id' in cols}")
    print(f"  Has stay_id: {'stay_id' in cols}")
    
    # Check if gates table exists
    result = conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename IN ('gates', 'stays')"))
    tables = [row[0] for row in result]
    print(f"\nTables:")
    print(f"  Has gates: {'gates' in tables}")
    print(f"  Has stays: {'stays' in tables}")
