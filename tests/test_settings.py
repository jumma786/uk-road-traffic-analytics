import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.settings import (
    PROJECT_ROOT, DATA_RAW, DATA_PROCESSED, DATA_STAGING,
    SQLALCHEMY_URL, PYODBC_CONN_STR, AADF_FILE,
    RAW_COUNTS_FILE, COUNT_POINTS_FILE, CHUNK_SIZE, SQL_INSERT_BATCH,
)


def test_project_root_exists():
    assert PROJECT_ROOT.exists()


def test_data_directories_defined():
    assert DATA_RAW.name == "raw"
    assert DATA_PROCESSED.name == "processed"
    assert DATA_STAGING.name == "staging"


def test_sqlalchemy_url_format():
    assert "mssql+pyodbc://" in SQLALCHEMY_URL
    assert "UK_Road_Traffic_DW" in SQLALCHEMY_URL


def test_pyodbc_conn_str_format():
    assert "ODBC Driver" in PYODBC_CONN_STR
    assert "UK_Road_Traffic_DW" in PYODBC_CONN_STR


def test_file_paths_have_correct_extensions():
    assert AADF_FILE.suffix == ".csv"
    assert RAW_COUNTS_FILE.suffix == ".csv"
    assert COUNT_POINTS_FILE.suffix == ".csv"


def test_chunk_sizes_are_positive():
    assert CHUNK_SIZE > 0
    assert SQL_INSERT_BATCH > 0
