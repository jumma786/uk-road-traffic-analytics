import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def test_get_engine_returns_engine():
    with patch("src.utils.db.create_engine") as mock_create:
        mock_create.return_value = MagicMock()
        from src.utils.db import get_engine
        engine = get_engine()
        assert engine is not None


def test_get_connection_calls_pyodbc():
    with patch("src.utils.db.pyodbc") as mock_pyodbc:
        mock_pyodbc.connect.return_value = MagicMock()
        from src.utils.db import get_connection
        conn = get_connection()
        assert conn is not None
