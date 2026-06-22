import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")
DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
DATA_STAGING = PROJECT_ROOT / "data" / "staging"
REPORTS_DIR = PROJECT_ROOT / "reports"

SQL_SERVER = os.environ.get("SQL_SERVER", "localhost")
SQL_DATABASE = os.environ.get("SQL_DATABASE", "UK_Road_Traffic_DW")
SQL_DRIVER = os.environ.get("SQL_DRIVER", "ODBC+Driver+17+for+SQL+Server")

SQLALCHEMY_URL = (
    f"mssql+pyodbc://{SQL_SERVER}/{SQL_DATABASE}"
    f"?driver={SQL_DRIVER}&trusted_connection=yes"
)

PYODBC_CONN_STR = (
    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
    f"SERVER={SQL_SERVER};DATABASE={SQL_DATABASE};Trusted_Connection=yes;"
)

AADF_FILE = DATA_RAW / "dft_traffic_counts_aadf_by_direction.csv"
RAW_COUNTS_FILE = DATA_RAW / "dft_traffic_counts_raw_counts.csv"
COUNT_POINTS_FILE = DATA_RAW / "count_points.csv"

CHUNK_SIZE = 10000
SQL_INSERT_BATCH = 1000
