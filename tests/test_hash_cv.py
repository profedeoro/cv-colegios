from pathlib import Path
from modulos.db import inicializar_db, guardar_hash_cv, hash_cv_actual


def test_guardar_y_leer_hash(tmp_path):
    bd = tmp_path / "t.db"
    inicializar_db(bd)
    assert hash_cv_actual(bd) is None
    guardar_hash_cv(bd, "abc123")
    assert hash_cv_actual(bd) == "abc123"
    guardar_hash_cv(bd, "def456")
    assert hash_cv_actual(bd) == "def456"
