from pathlib import Path
from modulos.backup import respaldar_bd, RETENCION_DIAS


def test_crea_archivo_bak(tmp_path):
    bd = tmp_path / "x.db"
    bd.write_bytes(b"contenido original")
    respaldar_bd(bd)
    assert (tmp_path / "x.db.bak.1").exists()
    assert (tmp_path / "x.db.bak.1").read_bytes() == b"contenido original"


def test_rota_backups_y_limita_retencion(tmp_path):
    bd = tmp_path / "x.db"
    for i in range(RETENCION_DIAS + 3):
        bd.write_bytes(f"v{i}".encode())
        respaldar_bd(bd)
    backups = sorted(tmp_path.glob("x.db.bak.*"))
    assert len(backups) == RETENCION_DIAS
    # El más reciente (.bak.1) tiene el contenido más nuevo
    assert (tmp_path / "x.db.bak.1").read_bytes() == f"v{RETENCION_DIAS + 2}".encode()


def test_no_falla_si_no_existe_bd(tmp_path):
    bd = tmp_path / "no_existe.db"
    respaldar_bd(bd)
    assert not (tmp_path / "no_existe.db.bak.1").exists()
