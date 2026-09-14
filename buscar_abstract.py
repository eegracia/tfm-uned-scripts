#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Enriquecimiento de metadatos bibliográficos
Revisión sistemática PRISMA / PRISMA-S

Funciones principales:
1. Lee el CSV de registros sin abstract.
2. Conserva todas las columnas originales.
3. Añade columnas de enriquecimiento.
4. Consulta cada referencia en OpenAlex y Crossref.
5. Prioriza la búsqueda por DOI.
6. Si falta el DOI, intenta localizar la referencia mediante
   título + año + primer autor con un criterio estricto.
7. Recupera, cuando estén disponibles:
   - abstract;
   - palabras clave de OpenAlex;
   - autores;
   - año;
   - fuente de publicación;
   - URL;
   - idioma;
   - DOI.
8. Conserva por separado los datos devueltos por OpenAlex
   y Crossref para mantener la trazabilidad.
9. Genera un CSV enriquecido sin sobrescribir el CSV original.
10. Guarda periódicamente el progreso para poder reanudar
    la ejecución en caso de interrupción.
"""

from pathlib import Path
import csv
import re
import time
import html
import unicodedata
from difflib import SequenceMatcher
from urllib.parse import quote

import requests


# ==========================================================
# CONFIGURACIÓN
# ==========================================================

ARCHIVO_ENTRADA = Path(
    "ris_normalizados/TFM_registros_sin_abstract.csv"
)

ARCHIVO_SALIDA = Path(
    "ris_normalizados/TFM_registros_sin_abstract_enriquecidos.csv"
)

# La clave de OpenAlex es opcional.
# Si no se dispone de ella, dejar la cadena vacía.
CLAVE_API_OPENALEX = ""

# Introducir un correo real para identificar las peticiones
# realizadas a Crossref.
CORREO_CROSSREF = "egracia69@alumno.uned.es"

TIEMPO_ESPERA_OPENALEX = 0.10
TIEMPO_ESPERA_CROSSREF = 0.15

MAXIMO_REINTENTOS = 4

# Guarda el CSV cada N registros procesados.
GUARDAR_CADA = 10

# Umbral mínimo para aceptar una coincidencia por título
# cuando el registro original carece de DOI.
UMBRAL_TITULO = 0.95


# ==========================================================
# COLUMNAS NUEVAS
# ==========================================================

COLUMNAS_NUEVAS = [
    "doi_consulta",
    "doi_recuperado",
    "metodo_localizacion_doi",

    "estado_openalex",
    "openalex_id",
    "doi_openalex",
    "titulo_openalex",
    "autores_openalex",
    "anio_openalex",
    "abstract_openalex",
    "palabras_clave_openalex",
    "fuente_publicacion_openalex",
    "url_openalex",
    "idioma_openalex",
    "similitud_titulo_openalex",

    "estado_crossref",
    "doi_crossref",
    "titulo_crossref",
    "autores_crossref",
    "anio_crossref",
    "abstract_crossref",
    "temas_crossref",
    "fuente_publicacion_crossref",
    "url_crossref",
    "similitud_titulo_crossref",

    "abstract_recuperado",
    "fuente_abstract_recuperado",
    "palabras_clave_recuperadas",
    "estado_enriquecimiento",
    "observaciones_enriquecimiento",
]


# ==========================================================
# NORMALIZACIÓN
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
    Calcula la similitud entre dos títulos normalizados.
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


def obtener_apellido_primer_autor(autores):
    """
    Obtiene una aproximación conservadora al apellido
    del primer autor.

    El CSV contiene los autores separados por punto y coma.
    Admite formatos habituales como:
        García, Juan
        Juan García
    """

    if not autores:
        return ""

    primer_autor = autores.split(";")[0].strip()

    if not primer_autor:
        return ""

    if "," in primer_autor:
        apellido = primer_autor.split(",")[0].strip()
    else:
        partes = primer_autor.split()
        apellido = partes[-1].strip() if partes else ""

    return normalizar_texto(apellido)


def coincidencia_bibliografica_segura(
    titulo_original,
    autores_originales,
    anio_original,
    titulo_candidato,
    autores_candidato,
    anio_candidato
):
    """
    Comprueba si una coincidencia sin DOI puede aceptarse
    automáticamente.

    Requiere:
    - similitud de título >= UMBRAL_TITULO;
    - mismo año, cuando ambos años están disponibles;
    - mismo apellido del primer autor, cuando ambos
      autores están disponibles.
    """

    similitud = similitud_titulos(
        titulo_original,
        titulo_candidato
    )

    if similitud < UMBRAL_TITULO:
        return False, similitud

    if (
        anio_original
        and anio_candidato
        and str(anio_original).strip()
        != str(anio_candidato).strip()
    ):
        return False, similitud

    apellido_original = obtener_apellido_primer_autor(
        autores_originales
    )

    apellido_candidato = obtener_apellido_primer_autor(
        autores_candidato
    )

    if (
        apellido_original
        and apellido_candidato
        and apellido_original != apellido_candidato
    ):
        return False, similitud

    return True, similitud


# ==========================================================
# LIMPIEZA DE ABSTRACT CROSSREF
# ==========================================================

def limpiar_xml(texto):
    """
    Elimina etiquetas XML/HTML que pueden aparecer
    en abstracts recuperados desde Crossref.
    """

    if not texto:
        return ""

    texto = re.sub(
        r"<[^>]+>",
        " ",
        texto
    )

    texto = html.unescape(texto)

    return re.sub(
        r"\s+",
        " ",
        texto
    ).strip()


# ==========================================================
# ABSTRACT OPENALEX
# ==========================================================

def reconstruir_abstract_openalex(indice_invertido):
    """
    Reconstruye el abstract de OpenAlex a partir
    de abstract_inverted_index.
    """

    if not indice_invertido:
        return ""

    posiciones = []

    for palabra, lista_posiciones in indice_invertido.items():

        for posicion in lista_posiciones:

            posiciones.append(
                (posicion, palabra)
            )

    posiciones.sort(
        key=lambda elemento: elemento[0]
    )

    return " ".join(
        palabra
        for _, palabra in posiciones
    )


# ==========================================================
# EXTRACCIÓN DE METADATOS
# ==========================================================

def extraer_anio_crossref(datos):
    """
    Obtiene el año de publicación de un registro Crossref.
    """

    for campo in (
        "published-print",
        "published-online",
        "published",
        "issued",
        "created"
    ):

        valor = datos.get(campo)

        if isinstance(valor, dict):

            partes = valor.get(
                "date-parts",
                []
            )

            if (
                partes
                and partes[0]
                and partes[0][0]
            ):
                return str(partes[0][0])

    return ""


def extraer_autores_crossref(datos):
    """
    Obtiene los autores de un registro Crossref.
    """

    autores = []

    for autor in datos.get("author", []) or []:

        nombre = " ".join(
            parte
            for parte in [
                autor.get("given", "").strip(),
                autor.get("family", "").strip()
            ]
            if parte
        ).strip()

        if nombre:
            autores.append(nombre)

    return "; ".join(autores)


def extraer_autores_openalex(datos):
    """
    Obtiene los autores de un registro OpenAlex.
    """

    autores = []

    for autoria in datos.get(
        "authorships",
        []
    ) or []:

        autor = autoria.get("author") or {}

        nombre = (
            autor.get("display_name")
            or ""
        ).strip()

        if nombre:
            autores.append(nombre)

    return "; ".join(autores)


# ==========================================================
# PETICIONES HTTP
# ==========================================================

def solicitar_json(
    sesion,
    url,
    parametros=None
):
    """
    Ejecuta una petición HTTP con varios reintentos.

    Los códigos 429 y los errores temporales del servidor
    provocan una espera exponencial antes de reintentar.
    """

    ultimo_error = ""

    for intento in range(
        1,
        MAXIMO_REINTENTOS + 1
    ):

        try:

            respuesta = sesion.get(
                url,
                params=parametros,
                timeout=30
            )

            if respuesta.status_code == 404:
                return None, "NO_ENCONTRADO"

            if respuesta.status_code == 200:
                return respuesta.json(), "OK"

            if respuesta.status_code in (
                429,
                500,
                502,
                503,
                504
            ):

                ultimo_error = (
                    f"HTTP {respuesta.status_code}"
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

            ultimo_error = str(excepcion)

            time.sleep(
                2 ** intento
            )

    return (
        None,
        f"ERROR: {ultimo_error}"
    )


# ==========================================================
# CONSULTAS OPENALEX
# ==========================================================

def consultar_openalex_por_doi(
    sesion,
    doi
):
    """
    Recupera un trabajo de OpenAlex mediante DOI.
    """

    parametros = {}

    if CLAVE_API_OPENALEX.strip():
        parametros["api_key"] = (
            CLAVE_API_OPENALEX.strip()
        )

    url = (
        "https://api.openalex.org/works/"
        f"doi:{quote(doi, safe='')}"
    )

    datos, estado = solicitar_json(
        sesion,
        url,
        parametros
    )

    time.sleep(
        TIEMPO_ESPERA_OPENALEX
    )

    if estado != "OK" or not datos:
        return None, estado

    return datos, "ENCONTRADO"


def buscar_openalex_por_titulo(
    sesion,
    titulo,
    autores,
    anio
):
    """
    Busca en OpenAlex por título cuando no existe DOI.

    Solo acepta automáticamente una coincidencia
    bibliográfica considerada segura.
    """

    parametros = {
        "search": titulo,
        "per_page": 5,
    }

    if CLAVE_API_OPENALEX.strip():
        parametros["api_key"] = (
            CLAVE_API_OPENALEX.strip()
        )

    datos, estado = solicitar_json(
        sesion,
        "https://api.openalex.org/works",
        parametros
    )

    time.sleep(
        TIEMPO_ESPERA_OPENALEX
    )

    if estado != "OK" or not datos:
        return None, estado

    mejor = None
    mejor_similitud = 0.0

    for candidato in datos.get(
        "results",
        []
    ):

        titulo_candidato = (
            candidato.get("title")
            or candidato.get("display_name")
            or ""
        )

        autores_candidato = (
            extraer_autores_openalex(
                candidato
            )
        )

        anio_candidato = str(
            candidato.get(
                "publication_year"
            )
            or ""
        )

        es_segura, similitud = (
            coincidencia_bibliografica_segura(
                titulo,
                autores,
                anio,
                titulo_candidato,
                autores_candidato,
                anio_candidato
            )
        )

        if (
            es_segura
            and similitud > mejor_similitud
        ):

            mejor = candidato
            mejor_similitud = similitud

    if mejor:

        mejor["_similitud_titulo"] = (
            mejor_similitud
        )

        return (
            mejor,
            "ENCONTRADO_POR_TITULO"
        )

    return (
        None,
        "NO_COINCIDENCIA_SEGURA"
    )


# ==========================================================
# CONSULTAS CROSSREF
# ==========================================================

def consultar_crossref_por_doi(
    sesion,
    doi
):
    """
    Recupera un trabajo de Crossref mediante DOI.
    """

    parametros = {}

    if CORREO_CROSSREF.strip():

        parametros["mailto"] = (
            CORREO_CROSSREF.strip()
        )

    url = (
        "https://api.crossref.org/works/"
        f"{quote(doi, safe='')}"
    )

    datos, estado = solicitar_json(
        sesion,
        url,
        parametros
    )

    time.sleep(
        TIEMPO_ESPERA_CROSSREF
    )

    if estado != "OK" or not datos:
        return None, estado

    mensaje = datos.get("message")

    if not isinstance(
        mensaje,
        dict
    ):
        return (
            None,
            "RESPUESTA_INVALIDA"
        )

    return mensaje, "ENCONTRADO"


def buscar_crossref_por_titulo(
    sesion,
    titulo,
    autores,
    anio
):
    """
    Busca en Crossref mediante datos bibliográficos
    cuando el registro carece de DOI.

    Solo acepta automáticamente una coincidencia
    bibliográfica considerada segura.
    """

    consulta_bibliografica = " ".join(
        elemento
        for elemento in [
            titulo,
            autores,
            anio
        ]
        if elemento
    )

    parametros = {
        "query.bibliographic":
            consulta_bibliografica,
        "rows": 5,
    }

    if CORREO_CROSSREF.strip():

        parametros["mailto"] = (
            CORREO_CROSSREF.strip()
        )

    datos, estado = solicitar_json(
        sesion,
        "https://api.crossref.org/works",
        parametros
    )

    time.sleep(
        TIEMPO_ESPERA_CROSSREF
    )

    if estado != "OK" or not datos:
        return None, estado

    elementos = (
        datos.get(
            "message",
            {}
        )
        .get(
            "items",
            []
        )
    )

    mejor = None
    mejor_similitud = 0.0

    for candidato in elementos:

        titulos = (
            candidato.get("title")
            or []
        )

        titulo_candidato = (
            titulos[0]
            if titulos
            else ""
        )

        autores_candidato = (
            extraer_autores_crossref(
                candidato
            )
        )

        anio_candidato = (
            extraer_anio_crossref(
                candidato
            )
        )

        es_segura, similitud = (
            coincidencia_bibliografica_segura(
                titulo,
                autores,
                anio,
                titulo_candidato,
                autores_candidato,
                anio_candidato
            )
        )

        if (
            es_segura
            and similitud > mejor_similitud
        ):

            mejor = candidato
            mejor_similitud = similitud

    if mejor:

        mejor["_similitud_titulo"] = (
            mejor_similitud
        )

        return (
            mejor,
            "ENCONTRADO_POR_TITULO"
        )

    return (
        None,
        "NO_COINCIDENCIA_SEGURA"
    )


# ==========================================================
# VOLCADO DE DATOS OPENALEX
# ==========================================================

def volcar_openalex(
    fila,
    datos,
    estado
):
    """
    Copia en la fila CSV los datos obtenidos de OpenAlex.
    """

    fila["estado_openalex"] = estado

    if not datos:
        return

    fila["openalex_id"] = (
        datos.get("id")
        or ""
    )

    fila["doi_openalex"] = normalizar_doi(
        datos.get("doi")
        or ""
    )

    fila["titulo_openalex"] = (
        datos.get("title")
        or datos.get("display_name")
        or ""
    )

    fila["autores_openalex"] = (
        extraer_autores_openalex(
            datos
        )
    )

    fila["anio_openalex"] = str(
        datos.get(
            "publication_year"
        )
        or ""
    )

    fila["abstract_openalex"] = (
        reconstruir_abstract_openalex(
            datos.get(
                "abstract_inverted_index"
            )
        )
    )

    palabras_clave = []

    for palabra in (
        datos.get("keywords", [])
        or []
    ):

        if isinstance(
            palabra,
            dict
        ):

            nombre = (
                palabra.get("display_name")
                or ""
            ).strip()

            if nombre:
                palabras_clave.append(nombre)

    fila["palabras_clave_openalex"] = (
        "; ".join(palabras_clave)
    )

    ubicacion = (
        datos.get("primary_location")
        or {}
    )

    fuente = (
        ubicacion.get("source")
        or {}
    )

    fila[
        "fuente_publicacion_openalex"
    ] = (
        fuente.get("display_name")
        or ""
    )

    fila["url_openalex"] = (
        ubicacion.get("landing_page_url")
        or datos.get("doi")
        or ""
    )

    fila["idioma_openalex"] = (
        datos.get("language")
        or ""
    )

    similitud = datos.get(
        "_similitud_titulo"
    )

    if similitud is None:

        similitud = similitud_titulos(
            fila.get("titulo", ""),
            fila["titulo_openalex"]
        )

    fila["similitud_titulo_openalex"] = (
        f"{similitud:.4f}"
    )


# ==========================================================
# VOLCADO DE DATOS CROSSREF
# ==========================================================

def volcar_crossref(
    fila,
    datos,
    estado
):
    """
    Copia en la fila CSV los datos obtenidos de Crossref.
    """

    fila["estado_crossref"] = estado

    if not datos:
        return

    fila["doi_crossref"] = (
        normalizar_doi(
            datos.get("DOI")
            or ""
        )
    )

    titulos = (
        datos.get("title")
        or []
    )

    fila["titulo_crossref"] = (
        titulos[0]
        if titulos
        else ""
    )

    fila["autores_crossref"] = (
        extraer_autores_crossref(
            datos
        )
    )

    fila["anio_crossref"] = (
        extraer_anio_crossref(
            datos
        )
    )

    fila["abstract_crossref"] = (
        limpiar_xml(
            datos.get("abstract")
            or ""
        )
    )

    # Crossref denomina "subject" a estas materias.
    # Se conservan separadas de las palabras clave de OpenAlex.
    fila["temas_crossref"] = (
        "; ".join(
            datos.get("subject")
            or []
        )
    )

    publicaciones = (
        datos.get("container-title")
        or []
    )

    fila[
        "fuente_publicacion_crossref"
    ] = (
        publicaciones[0]
        if publicaciones
        else ""
    )

    fila["url_crossref"] = (
        datos.get("URL")
        or ""
    )

    similitud = datos.get(
        "_similitud_titulo"
    )

    if similitud is None:

        similitud = similitud_titulos(
            fila.get("titulo", ""),
            fila["titulo_crossref"]
        )

    fila["similitud_titulo_crossref"] = (
        f"{similitud:.4f}"
    )


# ==========================================================
# SELECCIÓN DEL RESULTADO FINAL
# ==========================================================

def elegir_datos_finales(fila):
    """
    Selecciona los metadatos que se utilizarán como
    resultado del enriquecimiento.

    Los datos originales de OpenAlex y Crossref
    permanecen siempre en columnas independientes.
    """

    abstract_openalex = (
        fila.get(
            "abstract_openalex"
        )
        or ""
    ).strip()

    abstract_crossref = (
        fila.get(
            "abstract_crossref"
        )
        or ""
    ).strip()

    if (
        abstract_openalex
        and abstract_crossref
    ):

        # Si ambas fuentes aportan abstract, se conserva
        # como resultado el más completo por longitud.
        # Los dos originales permanecen en el CSV.
        if (
            len(abstract_openalex)
            >= len(abstract_crossref)
        ):

            fila["abstract_recuperado"] = (
                abstract_openalex
            )

            fila[
                "fuente_abstract_recuperado"
            ] = "OpenAlex"

        else:

            fila["abstract_recuperado"] = (
                abstract_crossref
            )

            fila[
                "fuente_abstract_recuperado"
            ] = "Crossref"

    elif abstract_openalex:

        fila["abstract_recuperado"] = (
            abstract_openalex
        )

        fila[
            "fuente_abstract_recuperado"
        ] = "OpenAlex"

    elif abstract_crossref:

        fila["abstract_recuperado"] = (
            abstract_crossref
        )

        fila[
            "fuente_abstract_recuperado"
        ] = "Crossref"

    else:

        fila["abstract_recuperado"] = ""

        fila[
            "fuente_abstract_recuperado"
        ] = ""

    # Las keywords de OpenAlex se conservan como
    # palabras clave recuperadas.
    # Los "subject" de Crossref se mantienen aparte
    # para no tratarlos como si fueran keywords.
    fila[
        "palabras_clave_recuperadas"
    ] = (
        fila.get(
            "palabras_clave_openalex"
        )
        or ""
    ).strip()

    if fila["abstract_recuperado"]:

        fila["estado_enriquecimiento"] = (
            "ABSTRACT_RECUPERADO"
        )

    elif (
        fila.get(
            "estado_openalex",
            ""
        ).startswith("ENCONTRADO")
        or
        fila.get(
            "estado_crossref",
            ""
        ).startswith("ENCONTRADO")
    ):

        fila["estado_enriquecimiento"] = (
            "ENCONTRADO_SIN_ABSTRACT"
        )

    else:

        fila["estado_enriquecimiento"] = (
            "PENDIENTE_REVISION_MANUAL"
        )


# ==========================================================
# GUARDADO DEL CSV
# ==========================================================

def guardar_csv(
    filas,
    columnas,
    ruta
):
    """
    Guarda el fichero CSV en UTF-8 con BOM para facilitar
    su apertura directa en Microsoft Excel bajo Windows.
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
    Si ya existe el fichero enriquecido, continúa trabajando
    sobre él para poder reanudar una ejecución interrumpida.

    En caso contrario, parte del CSV original.
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

    columnas = (
        columnas_originales[:]
    )

    for columna in COLUMNAS_NUEVAS:

        if columna not in columnas:
            columnas.append(columna)

    for fila in filas:

        for columna in COLUMNAS_NUEVAS:
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
# PROCESO PRINCIPAL
# ==========================================================

def principal():

    filas, columnas, ruta_lectura = (
        cargar_filas()
    )

    sesion_openalex = (
        requests.Session()
    )

    sesion_openalex.headers.update({
        "User-Agent":
            "TFM-UNED-Enriquecimiento/1.0"
    })

    sesion_crossref = (
        requests.Session()
    )

    sesion_crossref.headers.update({
        "User-Agent": (
            "TFM-UNED-Enriquecimiento/1.0 "
            f"(mailto:{CORREO_CROSSREF})"
        )
    })

    print()
    print(
        "ENRIQUECIMIENTO DE METADATOS"
    )
    print("=" * 70)

    print(
        f"Archivo de lectura: "
        f"{ruta_lectura}"
    )

    print(
        f"Registros: "
        f"{len(filas)}"
    )

    print()

    for numero, fila in enumerate(
        filas,
        start=1
    ):

        estado_openalex = (
            fila.get(
                "estado_openalex",
                ""
            )
        )

        estado_crossref = (
            fila.get(
                "estado_crossref",
                ""
            )
        )

        consulta_openalex_finalizada = (
            estado_openalex.startswith(
                "ENCONTRADO"
            )
            or estado_openalex in {
                "NO_ENCONTRADO",
                "NO_COINCIDENCIA_SEGURA",
                "SIN_DOI_NO_LOCALIZADO"
            }
        )

        consulta_crossref_finalizada = (
            estado_crossref.startswith(
                "ENCONTRADO"
            )
            or estado_crossref in {
                "NO_ENCONTRADO",
                "NO_COINCIDENCIA_SEGURA",
                "SIN_DOI_NO_LOCALIZADO"
            }
        )

        # Si ambas consultas ya finalizaron en una ejecución
        # anterior, no se repiten.
        if (
            consulta_openalex_finalizada
            and consulta_crossref_finalizada
        ):
            continue

        titulo = (
            fila.get("titulo")
            or ""
        ).strip()

        autores = (
            fila.get("autores")
            or ""
        ).strip()

        anio = (
            fila.get("anio")
            or ""
        ).strip()

        doi_original = normalizar_doi(
            fila.get("doi")
            or ""
        )

        doi_consulta = doi_original

        fila["doi_consulta"] = (
            doi_consulta
        )

        fila[
            "observaciones_enriquecimiento"
        ] = ""

        # --------------------------------------------------
        # REGISTROS SIN DOI
        # --------------------------------------------------

        # Si no existe DOI, primero se intenta localizar
        # mediante una búsqueda bibliográfica en Crossref.
        if (
            not doi_consulta
            and titulo
        ):

            (
                datos_crossref_busqueda,
                estado_busqueda_crossref
            ) = buscar_crossref_por_titulo(
                sesion_crossref,
                titulo,
                autores,
                anio
            )

            if datos_crossref_busqueda:

                doi_candidato = normalizar_doi(
                    datos_crossref_busqueda.get(
                        "DOI"
                    )
                    or ""
                )

                if doi_candidato:

                    doi_consulta = (
                        doi_candidato
                    )

                    fila[
                        "doi_recuperado"
                    ] = doi_candidato

                    fila[
                        "doi_consulta"
                    ] = doi_candidato

                    fila[
                        "metodo_localizacion_doi"
                    ] = (
                        "Crossref: título + año "
                        "+ primer autor"
                    )

                volcar_crossref(
                    fila,
                    datos_crossref_busqueda,
                    estado_busqueda_crossref
                )

        # Si Crossref no ha permitido obtener DOI,
        # se realiza la búsqueda bibliográfica en OpenAlex.
        if (
            not doi_consulta
            and titulo
        ):

            (
                datos_openalex_busqueda,
                estado_busqueda_openalex
            ) = buscar_openalex_por_titulo(
                sesion_openalex,
                titulo,
                autores,
                anio
            )

            if datos_openalex_busqueda:

                doi_candidato = normalizar_doi(
                    datos_openalex_busqueda.get(
                        "doi"
                    )
                    or ""
                )

                if doi_candidato:

                    doi_consulta = (
                        doi_candidato
                    )

                    fila[
                        "doi_recuperado"
                    ] = doi_candidato

                    fila[
                        "doi_consulta"
                    ] = doi_candidato

                    fila[
                        "metodo_localizacion_doi"
                    ] = (
                        "OpenAlex: título + año "
                        "+ primer autor"
                    )

                volcar_openalex(
                    fila,
                    datos_openalex_busqueda,
                    estado_busqueda_openalex
                )

        # --------------------------------------------------
        # CONSULTA POR DOI
        # --------------------------------------------------

        # Cuando se dispone de DOI, se consultan siempre
        # las dos fuentes para conservar ambos resultados.
        if doi_consulta:

            if not consulta_openalex_finalizada:

                (
                    datos_openalex,
                    estado_openalex
                ) = consultar_openalex_por_doi(
                    sesion_openalex,
                    doi_consulta
                )

                volcar_openalex(
                    fila,
                    datos_openalex,
                    estado_openalex
                )

            if not consulta_crossref_finalizada:

                (
                    datos_crossref,
                    estado_crossref
                ) = consultar_crossref_por_doi(
                    sesion_crossref,
                    doi_consulta
                )

                volcar_crossref(
                    fila,
                    datos_crossref,
                    estado_crossref
                )

        else:

            if not fila.get(
                "estado_openalex"
            ):

                fila[
                    "estado_openalex"
                ] = (
                    "SIN_DOI_NO_LOCALIZADO"
                )

            if not fila.get(
                "estado_crossref"
            ):

                fila[
                    "estado_crossref"
                ] = (
                    "SIN_DOI_NO_LOCALIZADO"
                )

        # --------------------------------------------------
        # RESULTADO CONSOLIDADO
        # --------------------------------------------------

        elegir_datos_finales(
            fila
        )

        print(
            f"[{numero:>3}/{len(filas)}] "
            f"{fila.get('identificador_interno', '')} | "
            f"{fila['estado_enriquecimiento']}"
        )

        # Guardado periódico para no perder el trabajo
        # si la ejecución se interrumpe.
        if (
            numero % GUARDAR_CADA
            == 0
        ):

            guardar_csv(
                filas,
                columnas,
                ARCHIVO_SALIDA
            )

    # Guardado final
    guardar_csv(
        filas,
        columnas,
        ARCHIVO_SALIDA
    )

    # ======================================================
    # RESUMEN FINAL
    # ======================================================

    total_abstract = sum(
        1
        for fila in filas
        if (
            fila.get(
                "abstract_recuperado"
            )
            or ""
        ).strip()
    )

    pendientes = sum(
        1
        for fila in filas
        if fila.get(
            "estado_enriquecimiento"
        )
        == "PENDIENTE_REVISION_MANUAL"
    )

    encontrados_sin_abstract = sum(
        1
        for fila in filas
        if fila.get(
            "estado_enriquecimiento"
        )
        == "ENCONTRADO_SIN_ABSTRACT"
    )

    print()
    print("RESULTADO FINAL")
    print("=" * 70)

    print(
        f"Registros procesados: "
        f"{len(filas)}"
    )

    print(
        f"Abstracts recuperados: "
        f"{total_abstract}"
    )

    print(
        "Registros localizados pero "
        "sin abstract: "
        f"{encontrados_sin_abstract}"
    )

    print(
        "Pendientes de revisión manual: "
        f"{pendientes}"
    )

    print(
        f"Archivo generado: "
        f"{ARCHIVO_SALIDA}"
    )


if __name__ == "__main__":
    principal()