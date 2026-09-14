#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Enriquecimiento de metadatos mediante Springer Nature API
Revisión sistemática PRISMA / PRISMA-S

Funciones principales:
1. Lee el CSV previamente enriquecido mediante OpenAlex y Crossref.
2. Selecciona únicamente los registros procedentes de
   Springer Nature Link que siguen sin abstract.
3. Consulta Springer Nature Meta API v2 mediante DOI.
4. Recupera, cuando estén disponibles:
   - abstract;
   - título;
   - autores;
   - año;
   - DOI;
   - palabras clave;
   - publicación;
   - URL;
   - idioma.
5. Comprueba que el DOI recuperado corresponde al DOI consultado.
6. Conserva los metadatos de Springer Nature en columnas específicas.
7. Incorpora el abstract recuperado al campo consolidado
   abstract_recuperado.
8. Guarda periódicamente los resultados para poder reanudar
   una ejecución interrumpida.
9. No modifica el fichero de entrada.
"""

from pathlib import Path
import csv
import re
import time
import html
import unicodedata
from difflib import SequenceMatcher

import requests


# ==========================================================
# CONFIGURACIÓN
# ==========================================================

ARCHIVO_ENTRADA = Path(
    "ris_normalizados/TFM_registros_sin_abstract_enriquecidos.csv"
)

ARCHIVO_SALIDA = Path(
    "ris_normalizados/"
    "TFM_registros_sin_abstract_enriquecidos_springer.csv"
)

# Introducir aquí la API Key obtenida en Springer Nature.
CLAVE_API_SPRINGER = "1f61f555aa391bc15fa35be1fff2aaf9"

URL_API_SPRINGER = (
    "https://api.springernature.com/meta/v2/json"
)

# El plan Basic dispone de un límite diario.
# Se utilizan 450 consultas por ejecución para dejar margen.
# Si se dispone de un plan superior puede modificarse.
MAXIMO_CONSULTAS_EJECUCION = 450

# Pausa entre peticiones para no superar el límite
# de peticiones por minuto.
TIEMPO_ESPERA = 0.8

MAXIMO_REINTENTOS = 4

# Guarda el fichero cada N consultas.
GUARDAR_CADA = 10


# ==========================================================
# COLUMNAS NUEVAS
# ==========================================================

COLUMNAS_SPRINGER = [
    "estado_springer",
    "doi_springer",
    "titulo_springer",
    "autores_springer",
    "anio_springer",
    "abstract_springer",
    "palabras_clave_springer",
    "fuente_publicacion_springer",
    "url_springer",
    "idioma_springer",
    "similitud_titulo_springer",
    "observaciones_springer",
]


# ==========================================================
# FUNCIONES DE NORMALIZACIÓN
# ==========================================================

def normalizar_doi(doi):
    """
    Convierte el DOI a un formato uniforme.
    """

    if not doi:
        return ""

    doi = doi.strip().lower()

    doi = re.sub(
        r"^https?://(?:dx\.)?doi\.org/",
        "",
        doi
    )

    doi = re.sub(
        r"^doi:\s*",
        "",
        doi
    )

    return doi.rstrip(" .;,)]}")


def normalizar_texto(texto):
    """
    Genera una versión normalizada de un texto
    para realizar comparaciones.
    """

    if not texto:
        return ""

    texto = html.unescape(texto)

    texto = unicodedata.normalize(
        "NFKD",
        texto.lower()
    )

    texto = "".join(
        caracter
        for caracter in texto
        if not unicodedata.combining(caracter)
    )

    texto = re.sub(
        r"[^a-z0-9]+",
        " ",
        texto
    )

    return re.sub(
        r"\s+",
        " ",
        texto
    ).strip()


def similitud_titulos(titulo_1, titulo_2):
    """
    Calcula la similitud entre dos títulos.
    """

    titulo_1 = normalizar_texto(titulo_1)
    titulo_2 = normalizar_texto(titulo_2)

    if not titulo_1 or not titulo_2:
        return 0.0

    return SequenceMatcher(
        None,
        titulo_1,
        titulo_2
    ).ratio()


def limpiar_texto(texto):
    """
    Elimina etiquetas HTML/XML y espacios redundantes.
    """

    if not texto:
        return ""

    texto = re.sub(
        r"<[^>]+>",
        " ",
        str(texto)
    )

    texto = html.unescape(texto)

    return re.sub(
        r"\s+",
        " ",
        texto
    ).strip()


# ==========================================================
# EXTRACCIÓN DE METADATOS SPRINGER
# ==========================================================

def obtener_autores_springer(registro):
    """
    Extrae los autores del registro devuelto por Springer.
    """

    autores = []

    for creador in registro.get(
        "creators",
        []
    ) or []:

        if isinstance(creador, dict):

            nombre = (
                creador.get("creator")
                or ""
            ).strip()

        else:

            nombre = str(creador).strip()

        if nombre:
            autores.append(nombre)

    return "; ".join(autores)


def obtener_palabras_clave_springer(registro):
    """
    Extrae las palabras clave cuando están disponibles.

    Se contemplan distintas denominaciones utilizadas
    en las respuestas de metadatos.
    """

    palabras = []

    for campo in (
        "keyword",
        "keywords"
    ):

        valores = registro.get(campo)

        if not valores:
            continue

        if isinstance(valores, str):

            valores = re.split(
                r"[;,]",
                valores
            )

        elif not isinstance(
            valores,
            list
        ):

            valores = [valores]

        for valor in valores:

            if isinstance(valor, dict):

                texto = (
                    valor.get("keyword")
                    or valor.get("value")
                    or valor.get("name")
                    or ""
                )

            else:

                texto = str(valor)

            texto = limpiar_texto(texto)

            if (
                texto
                and texto.lower()
                not in {
                    palabra.lower()
                    for palabra in palabras
                }
            ):

                palabras.append(texto)

    return "; ".join(palabras)


def obtener_url_springer(registro):
    """
    Obtiene preferentemente la URL HTML del registro.
    """

    urls = registro.get(
        "url",
        []
    ) or []

    if isinstance(urls, dict):
        urls = [urls]

    if isinstance(urls, str):
        return urls

    # Preferencia por URL HTML
    for elemento in urls:

        if not isinstance(
            elemento,
            dict
        ):
            continue

        formato = str(
            elemento.get("format")
            or ""
        ).lower()

        valor = (
            elemento.get("value")
            or elemento.get("url")
            or ""
        )

        if (
            valor
            and "html" in formato
        ):
            return valor

    # Si no existe HTML, utiliza la primera URL
    for elemento in urls:

        if isinstance(
            elemento,
            dict
        ):

            valor = (
                elemento.get("value")
                or elemento.get("url")
                or ""
            )

        else:

            valor = str(elemento)

        if valor:
            return valor

    return ""


# ==========================================================
# CONSULTA SPRINGER NATURE API
# ==========================================================

def consultar_springer_por_doi(
    sesion,
    doi
):
    """
    Consulta Springer Nature Meta API v2 mediante DOI.
    """

    parametros = {
        "api_key": CLAVE_API_SPRINGER,
        "q": f"doi:{doi}",
        "p": 1,
        "s": 1,
    }

    ultimo_error = ""

    for intento in range(
        1,
        MAXIMO_REINTENTOS + 1
    ):

        try:

            respuesta = sesion.get(
                URL_API_SPRINGER,
                params=parametros,
                timeout=30
            )

            # ----------------------------------------------
            # RESPUESTA CORRECTA
            # ----------------------------------------------

            if respuesta.status_code == 200:

                datos = respuesta.json()

                registros = datos.get(
                    "records",
                    []
                ) or []

                if not registros:

                    return (
                        None,
                        "NO_ENCONTRADO"
                    )

                return (
                    registros[0],
                    "ENCONTRADO"
                )

            # ----------------------------------------------
            # LÍMITE DE PETICIONES
            # ----------------------------------------------

            if respuesta.status_code == 429:

                return (
                    None,
                    "LIMITE_API"
                )

            # ----------------------------------------------
            # CLAVE INCORRECTA
            # ----------------------------------------------

            if respuesta.status_code in (
                401,
                403
            ):

                return (
                    None,
                    "ERROR_CLAVE_API"
                )

            # ----------------------------------------------
            # OTROS ERRORES TEMPORALES
            # ----------------------------------------------

            if respuesta.status_code in (
                500,
                502,
                503,
                504
            ):

                ultimo_error = (
                    f"HTTP "
                    f"{respuesta.status_code}"
                )

                time.sleep(
                    2 ** intento
                )

                continue

            return (
                None,
                f"HTTP_{respuesta.status_code}"
            )

        except requests.RequestException as excepcion:

            ultimo_error = str(
                excepcion
            )

            time.sleep(
                2 ** intento
            )

    return (
        None,
        f"ERROR: {ultimo_error}"
    )


# ==========================================================
# VOLCADO DE LOS DATOS SPRINGER
# ==========================================================

def volcar_datos_springer(
    fila,
    registro_springer,
    estado
):
    """
    Incorpora a la fila los metadatos recuperados
    desde Springer Nature.
    """

    fila["estado_springer"] = estado

    if not registro_springer:
        return

    doi_original = normalizar_doi(
        fila.get("doi")
        or fila.get("doi_consulta")
        or ""
    )

    doi_springer = normalizar_doi(
        registro_springer.get("doi")
        or ""
    )

    fila["doi_springer"] = (
        doi_springer
    )

    # Verificación adicional de seguridad
    if (
        doi_original
        and doi_springer
        and doi_original != doi_springer
    ):

        fila["estado_springer"] = (
            "DOI_NO_COINCIDENTE"
        )

        fila[
            "observaciones_springer"
        ] = (
            "El DOI devuelto por Springer "
            "no coincide con el DOI original."
        )

        return

    titulo = limpiar_texto(
        registro_springer.get("title")
        or ""
    )

    fila["titulo_springer"] = titulo

    fila["autores_springer"] = (
        obtener_autores_springer(
            registro_springer
        )
    )

    fila["anio_springer"] = str(
        registro_springer.get(
            "publicationDate"
        )
        or ""
    )[:4]

    fila["abstract_springer"] = (
        limpiar_texto(
            registro_springer.get(
                "abstract"
            )
            or ""
        )
    )

    fila[
        "palabras_clave_springer"
    ] = (
        obtener_palabras_clave_springer(
            registro_springer
        )
    )

    fila[
        "fuente_publicacion_springer"
    ] = limpiar_texto(
        registro_springer.get(
            "publicationName"
        )
        or ""
    )

    fila["url_springer"] = (
        obtener_url_springer(
            registro_springer
        )
    )

    fila["idioma_springer"] = (
        registro_springer.get(
            "language"
        )
        or ""
    )

    similitud = similitud_titulos(
        fila.get("titulo", ""),
        titulo
    )

    fila[
        "similitud_titulo_springer"
    ] = f"{similitud:.4f}"

    # ------------------------------------------------------
    # INCORPORACIÓN AL RESULTADO CONSOLIDADO
    # ------------------------------------------------------

    abstract_springer = (
        fila.get(
            "abstract_springer"
        )
        or ""
    ).strip()

    if abstract_springer:

        # Solo se sustituye si todavía no existe abstract.
        if not (
            fila.get(
                "abstract_recuperado"
            )
            or ""
        ).strip():

            fila[
                "abstract_recuperado"
            ] = abstract_springer

            fila[
                "fuente_abstract_recuperado"
            ] = (
                "Springer Nature API"
            )

        fila[
            "estado_enriquecimiento"
        ] = "ABSTRACT_RECUPERADO"

    else:

        fila[
            "estado_enriquecimiento"
        ] = "ENCONTRADO_SIN_ABSTRACT"


# ==========================================================
# GUARDADO DEL CSV
# ==========================================================

def guardar_csv(
    filas,
    columnas,
    ruta
):
    """
    Guarda el CSV en UTF-8 con BOM para facilitar
    su apertura directa mediante Excel en Windows.
    """

    ruta.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with ruta.open(
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as archivo:

        escritor = csv.DictWriter(
            archivo,
            fieldnames=columnas,
            extrasaction="ignore"
        )

        escritor.writeheader()

        escritor.writerows(
            filas
        )


# ==========================================================
# CARGA DEL CSV Y REANUDACIÓN
# ==========================================================

def cargar_filas():
    """
    Si existe el fichero de salida, continúa trabajando
    sobre él para poder reanudar la ejecución.

    En caso contrario, parte del fichero enriquecido
    mediante OpenAlex y Crossref.
    """

    ruta_lectura = (
        ARCHIVO_SALIDA
        if ARCHIVO_SALIDA.exists()
        else ARCHIVO_ENTRADA
    )

    if not ruta_lectura.exists():

        raise FileNotFoundError(
            "No se encuentra el archivo: "
            f"{ruta_lectura.resolve()}"
        )

    with ruta_lectura.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as archivo:

        lector = csv.DictReader(
            archivo
        )

        columnas_originales = (
            lector.fieldnames
            or []
        )

        filas = list(lector)

    columnas = columnas_originales[:]

    for columna in COLUMNAS_SPRINGER:

        if columna not in columnas:
            columnas.append(columna)

    for fila in filas:

        for columna in COLUMNAS_SPRINGER:

            fila.setdefault(
                columna,
                ""
            )

    return (
        filas,
        columnas,
        ruta_lectura
    )


# ==========================================================
# DETERMINACIÓN DE REGISTROS A CONSULTAR
# ==========================================================

def requiere_consulta_springer(fila):
    """
    Determina si un registro debe consultarse
    en Springer Nature API.
    """

    fuente = (
        fila.get(
            "fuente_procedencia"
        )
        or ""
    ).lower()

    abstract_actual = (
        fila.get(
            "abstract_recuperado"
        )
        or ""
    ).strip()

    estado_enriquecimiento = (
        fila.get(
            "estado_enriquecimiento"
        )
        or ""
    )

    estado_springer = (
        fila.get(
            "estado_springer"
        )
        or ""
    )

    # Solo registros de Springer Nature Link
    if (
        "springer nature link"
        not in fuente
    ):
        return False

    # Si ya existe abstract, no hace falta consultar.
    if abstract_actual:
        return False

    # Solo los localizados anteriormente sin abstract.
    if (
        estado_enriquecimiento
        != "ENCONTRADO_SIN_ABSTRACT"
    ):
        return False

    # No repetir consultas ya finalizadas.
    if estado_springer in {
        "ENCONTRADO",
        "NO_ENCONTRADO",
        "DOI_NO_COINCIDENTE",
    }:
        return False

    return True


# ==========================================================
# PROCESO PRINCIPAL
# ==========================================================

def principal():

    if (
        not CLAVE_API_SPRINGER
        or CLAVE_API_SPRINGER
        == "TU_API_KEY"
    ):

        print()
        print(
            "ERROR: Debes introducir tu API Key "
            "de Springer Nature."
        )

        return

    (
        filas,
        columnas,
        ruta_lectura
    ) = cargar_filas()

    pendientes_iniciales = [
        fila
        for fila in filas
        if requiere_consulta_springer(
            fila
        )
    ]

    print()
    print(
        "ENRIQUECIMIENTO MEDIANTE SPRINGER NATURE API"
    )
    print("=" * 70)

    print(
        f"Archivo de lectura: "
        f"{ruta_lectura}"
    )

    print(
        f"Registros totales del CSV: "
        f"{len(filas)}"
    )

    print(
        f"Registros Springer pendientes: "
        f"{len(pendientes_iniciales)}"
    )

    print(
        f"Máximo de consultas en esta ejecución: "
        f"{MAXIMO_CONSULTAS_EJECUCION}"
    )

    print()

    sesion = requests.Session()

    sesion.headers.update({
        "User-Agent":
            "TFM-UNED-Enriquecimiento-Springer/1.0"
    })

    consultas_realizadas = 0
    abstracts_recuperados_ejecucion = 0
    limite_api_alcanzado = False

    for numero, fila in enumerate(
        filas,
        start=1
    ):

        if not requiere_consulta_springer(
            fila
        ):
            continue

        # --------------------------------------------------
        # LÍMITE DE CONSULTAS DE ESTA EJECUCIÓN
        # --------------------------------------------------

        if (
            consultas_realizadas
            >= MAXIMO_CONSULTAS_EJECUCION
        ):

            print()
            print(
                "Se ha alcanzado el máximo "
                "de consultas configurado."
            )

            break

        doi = normalizar_doi(
            fila.get("doi")
            or fila.get(
                "doi_consulta"
            )
            or ""
        )

        if not doi:

            fila["estado_springer"] = (
                "SIN_DOI"
            )

            fila[
                "observaciones_springer"
            ] = (
                "No es posible realizar "
                "la consulta automática por DOI."
            )

            continue

        consultas_realizadas += 1

        registro_springer, estado = (
            consultar_springer_por_doi(
                sesion,
                doi
            )
        )

        # --------------------------------------------------
        # LÍMITE DE API
        # --------------------------------------------------

        if estado == "LIMITE_API":

            print()
            print(
                "Springer Nature ha indicado que "
                "se ha alcanzado el límite de la API."
            )

            print(
                "El progreso se guardará. "
                "Vuelve a ejecutar el script cuando "
                "se haya restablecido la cuota."
            )

            limite_api_alcanzado = True

            # No se marca como finalizado para que
            # vuelva a intentarse en otra ejecución.
            fila["estado_springer"] = (
                "LIMITE_API"
            )

            guardar_csv(
                filas,
                columnas,
                ARCHIVO_SALIDA
            )

            break

        # --------------------------------------------------
        # ERROR DE CLAVE API
        # --------------------------------------------------

        if estado == "ERROR_CLAVE_API":

            print()
            print(
                "ERROR: Springer Nature ha rechazado "
                "la API Key."
            )

            fila["estado_springer"] = estado

            guardar_csv(
                filas,
                columnas,
                ARCHIVO_SALIDA
            )

            break

        # --------------------------------------------------
        # VOLCADO DEL RESULTADO
        # --------------------------------------------------

        volcar_datos_springer(
            fila,
            registro_springer,
            estado
        )

        if (
            fila.get(
                "abstract_springer"
            )
            or ""
        ).strip():

            abstracts_recuperados_ejecucion += 1

        print(
            f"[{consultas_realizadas:>3}/"
            f"{min(len(pendientes_iniciales), MAXIMO_CONSULTAS_EJECUCION)}] "
            f"{fila.get('identificador_interno', '')} | "
            f"{fila.get('estado_springer', '')} | "
            f"{'ABSTRACT' if fila.get('abstract_springer') else 'SIN ABSTRACT'}"
        )

        # --------------------------------------------------
        # GUARDADO PERIÓDICO
        # --------------------------------------------------

        if (
            consultas_realizadas
            % GUARDAR_CADA
            == 0
        ):

            guardar_csv(
                filas,
                columnas,
                ARCHIVO_SALIDA
            )

        time.sleep(
            TIEMPO_ESPERA
        )

    # ======================================================
    # GUARDADO FINAL
    # ======================================================

    guardar_csv(
        filas,
        columnas,
        ARCHIVO_SALIDA
    )

    # ======================================================
    # RESUMEN GLOBAL
    # ======================================================

    abstracts_springer_totales = sum(
        1
        for fila in filas
        if (
            fila.get(
                "abstract_springer"
            )
            or ""
        ).strip()
    )

    pendientes_finales = sum(
        1
        for fila in filas
        if requiere_consulta_springer(
            fila
        )
    )

    total_abstracts_recuperados = sum(
        1
        for fila in filas
        if (
            fila.get(
                "abstract_recuperado"
            )
            or ""
        ).strip()
    )

    print()
    print("RESULTADO DE LA EJECUCIÓN")
    print("=" * 70)

    print(
        f"Consultas realizadas: "
        f"{consultas_realizadas}"
    )

    print(
        f"Abstracts recuperados en esta ejecución: "
        f"{abstracts_recuperados_ejecucion}"
    )

    print(
        f"Abstracts recuperados desde Springer "
        f"acumulados: "
        f"{abstracts_springer_totales}"
    )

    print(
        f"Abstracts recuperados en total "
        f"(todas las fuentes): "
        f"{total_abstracts_recuperados}"
    )

    print(
        f"Registros Springer todavía pendientes: "
        f"{pendientes_finales}"
    )

    print(
        f"Archivo generado: "
        f"{ARCHIVO_SALIDA}"
    )

    if limite_api_alcanzado:

        print()
        print(
            "La ejecución puede reanudarse "
            "posteriormente sin repetir las "
            "consultas ya completadas."
        )


if __name__ == "__main__":
    principal()