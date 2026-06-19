import sys
from pathlib import Path

import pyodbc
from sqlalchemy import create_engine

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from config.settings import SQLALCHEMY_URL, PYODBC_CONN_STR


def get_engine():
    return create_engine(SQLALCHEMY_URL)


def get_connection() -> pyodbc.Connection:
    return pyodbc.connect(PYODBC_CONN_STR)
