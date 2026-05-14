"""Script único: ejecuta el flujo OAuth de Gmail y guarda el token en disco.

Uso (manual, una sola vez):

    python autorizar_gmail.py

Abre el navegador, Daniel concede permiso, y se guarda `config/gmail_token.json`.
Si el token ya existe, no hace nada (no re-autoriza).
"""
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

from modulos.gmail_oauth import SCOPES


BASE = Path(__file__).parent
RUTA_CREDENCIALES = BASE / "config" / "credentials.json"
RUTA_TOKEN = BASE / "config" / "gmail_token.json"


def main() -> None:
    if RUTA_TOKEN.exists():
        print(f"Ya autorizado. Token: {RUTA_TOKEN}")
        return

    if not RUTA_CREDENCIALES.exists():
        raise FileNotFoundError(
            f"Falta {RUTA_CREDENCIALES}. Descárgalo desde Google Cloud Console."
        )

    flow = InstalledAppFlow.from_client_secrets_file(str(RUTA_CREDENCIALES), SCOPES)
    creds = flow.run_local_server(port=0)

    RUTA_TOKEN.parent.mkdir(parents=True, exist_ok=True)
    RUTA_TOKEN.write_text(creds.to_json(), encoding="utf-8")
    print(f"Autorización exitosa. Token guardado en {RUTA_TOKEN}")


if __name__ == "__main__":
    main()
