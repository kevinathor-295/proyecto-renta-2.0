"""
Guarda y carga los datos de un contribuyente por año gravable.

Por ahora se guarda en un archivo JSON local (uno por documento + año).
El día que esto necesite ser multiusuario o en la nube, solo se cambia
este archivo -por una base de datos real- sin tocar el motor ni la interfaz.
"""

import json
import os

CARPETA_DATOS = "datos_contribuyentes"

CAMPOS_DATOS_PERSONALES = [
    "dp_nombre", "dp_tipo_doc", "dp_num_doc", "dp_ciudad", "dp_direccion", "dp_correo",
]

CAMPOS_DECLARACION = [
    "uvt", "casa", "bancos", "vehiculos", "deudas_bancos", "deudas_terceros",
    "salarios", "honorarios", "salud_pension", "num_dependientes", "prepagada",
    "intereses", "gmf", "compras_facturadas", "costos_gastos", "afc",
    "pensiones_vol", "donaciones", "retenciones", "anticipo_anterior",
    "impuesto_anio_anterior", "num_declaracion",
]


def _ruta_archivo(documento: str, anio: int) -> str:
    os.makedirs(CARPETA_DATOS, exist_ok=True)
    documento_seguro = "".join(c for c in str(documento) if c.isalnum()) or "sin_documento"
    return os.path.join(CARPETA_DATOS, f"{documento_seguro}_{anio}.json")


def guardar_declaracion(documento: str, anio: int, datos: dict) -> None:
    """Guarda (o sobrescribe) los datos de un contribuyente para un año."""
    with open(_ruta_archivo(documento, anio), "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)


def cargar_declaracion(documento: str, anio: int) -> dict:
    """Devuelve los datos guardados, o un diccionario vacío si no existen."""
    ruta = _ruta_archivo(documento, anio)
    if not os.path.exists(ruta):
        return {}
    with open(ruta, "r", encoding="utf-8") as f:
        return json.load(f)


def anios_disponibles(documento: str) -> list:
    """Lista los años que ya tienen una declaración guardada para ese documento."""
    if not os.path.isdir(CARPETA_DATOS):
        return []
    documento_seguro = "".join(c for c in str(documento) if c.isalnum()) or "sin_documento"
    anios = []
    for nombre in os.listdir(CARPETA_DATOS):
        prefijo = f"{documento_seguro}_"
        if nombre.startswith(prefijo) and nombre.endswith(".json"):
            anio_str = nombre[len(prefijo):-len(".json")]
            if anio_str.isdigit():
                anios.append(int(anio_str))
    return sorted(anios)
