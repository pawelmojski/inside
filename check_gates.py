#!/usr/bin/env python3
from src.core.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    result = conn.execute(text('SELECT name, hostname, status, api_token FROM gates'))
    gates = list(result)
    print(f'Gates in database: {len(gates)}')
    for g in gates:
        print(f'  - {g[0]} ({g[1]}) - {g[2]} - token: {g[3][:30]}...')
