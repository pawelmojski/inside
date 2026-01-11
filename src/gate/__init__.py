"""
Gate Client Library

Gate always communicates with Tower via REST API.
Never touches PostgreSQL directly.

Config:
  TOWER_URL = https://localhost:5000  (all-in-one)
  TOWER_URL = https://tower.firma.pl  (distributed)
  GATE_TOKEN = secret-token-123
"""

__version__ = "1.9.0"
