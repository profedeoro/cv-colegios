"""CLI: corre un módulo del pipeline.

Uso:
    python correr_modulo.py descubrir
    python correr_modulo.py descubrir --bd otra.db --csv-men otro.csv
    python correr_modulo.py enriquecer --max 30
    python correr_modulo.py generar --max 15
    python correr_modulo.py enviar_borradores --token config/gmail_token.json
"""
import argparse
import sys
from pathlib import Path

from modulos.cliente_claude import ClienteClaude
from modulos.config import cargar_config, validar_google_cse, validar_brave
from modulos.descubrir import ejecutar as descubrir_ejecutar
from modulos.enriquecer import ejecutar as enriquecer_ejecutar
from modulos.generar import ejecutar as generar_ejecutar
from modulos.enviar_borradores import ejecutar as enviar_borradores_ejecutar

RAIZ = Path(__file__).parent
DEFAULT_BD = RAIZ / "data" / "colegios.db"
DEFAULT_ENV = RAIZ / "config" / ".env"
DEFAULT_CSV_MEN = RAIZ / "data" / "raw" / "men_directorio.csv"
DEFAULT_QUERIES = RAIZ / "config" / "queries_google.json"
DEFAULT_TOKEN = RAIZ / "config" / "gmail_token.json"


def main() -> None:
    parser = argparse.ArgumentParser(description="CLI de cv-colegios")
    parser.add_argument(
        "modulo",
        choices=["descubrir", "enriquecer", "generar", "enviar_borradores"],
        help="Módulo a ejecutar",
    )
    parser.add_argument("--max", type=int, default=None,
                        help="Máximo de colegios a procesar (enriquecer: 30, generar: 15)")
    parser.add_argument("--bd", default=str(DEFAULT_BD))
    parser.add_argument("--env", default=str(DEFAULT_ENV))
    parser.add_argument("--csv-men", default=str(DEFAULT_CSV_MEN))
    parser.add_argument("--queries", default=str(DEFAULT_QUERIES))
    parser.add_argument("--token", default=str(DEFAULT_TOKEN),
                        help="Ruta al token OAuth de Gmail (solo enviar_borradores)")
    args = parser.parse_args()

    if args.modulo == "descubrir":
        config = cargar_config(args.env)
        try:
            validar_google_cse(config)
            api_key = config["GOOGLE_CSE_API_KEY"]
            engine_id = config["GOOGLE_CSE_ENGINE_ID"]
        except Exception as e:
            print(f"[!] Google CSE no disponible: {e}")
            print("    Se procederá sin Google CSE; otras fuentes seguirán.")
            api_key = None
            engine_id = None

        resumen = descubrir_ejecutar(
            ruta_bd=Path(args.bd),
            ruta_csv_men=Path(args.csv_men),
            queries_path=Path(args.queries),
            google_api_key=api_key,
            google_engine_id=engine_id,
        )
        total = sum(resumen.values())
        print(f"\nResumen de descubrimiento ({total} colegios nuevos):")
        for fuente, n in resumen.items():
            print(f"  {fuente}: +{n}")

    elif args.modulo == "enriquecer":
        config = cargar_config(args.env)
        validar_brave(config)
        cliente = ClienteClaude(api_key=config["ANTHROPIC_API_KEY"])
        max_n = args.max if args.max is not None else 30
        resultado = enriquecer_ejecutar(
            ruta_bd=Path(args.bd),
            cliente_claude=cliente,
            brave_api_key=config["BRAVE_SEARCH_API_KEY"],
            max_colegios=max_n,
        )
        r = resultado["resumen"]
        print(f"\nResumen de enriquecimiento:")
        print(f"  Enriquecidos: +{r.get('enriquecido', 0)}")
        print(f"  Sin correo:   +{r.get('sin_correo', 0)}")
        print(f"  Errores:      +{r.get('error', 0)}")
        print(f"  Costo: ${resultado['costo_usd']:.4f} USD")
        print(f"  Duracion: {resultado['duracion_seg']:.1f} seg")

    elif args.modulo == "generar":
        config = cargar_config(args.env)
        cliente = ClienteClaude(api_key=config["ANTHROPIC_API_KEY"])
        max_n = args.max if args.max is not None else 15
        resultado = generar_ejecutar(
            ruta_bd=Path(args.bd),
            cliente_claude=cliente,
            max_colegios=max_n,
        )
        r = resultado["resumen"]
        print(f"\nResumen de generación:")
        for clave, n in r.items():
            print(f"  {clave}: +{n}")
        print(f"  Costo: ${resultado['costo_usd']:.4f} USD")
        print(f"  Duracion: {resultado['duracion_seg']:.1f} seg")

    elif args.modulo == "enviar_borradores":
        # No se requiere ANTHROPIC_API_KEY; solo el token de Gmail.
        resumen = enviar_borradores_ejecutar(
            ruta_bd=Path(args.bd),
            ruta_token=args.token,
        )
        print(f"\nResumen de envío de borradores:")
        print(f"  Total:           {resumen['total']}")
        print(f"  Subidos:         +{resumen['subidos']}")
        print(f"  Correo inválido: +{resumen['correo_invalido']}")
        print(f"  Fallos:          +{resumen['fallos']}")


if __name__ == "__main__":
    main()
