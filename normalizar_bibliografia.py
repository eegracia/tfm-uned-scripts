#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Normalización, consolidación y deduplicación de registros RIS
Revisión sistemática PRISMA / PRISMA-S

Funciones principales:
1. Lee todos los .ris de una carpeta.
2. Normaliza DOI.
3. Normaliza internamente títulos para comparación.
4. Homogeneiza campos RIS.
5. Normaliza año y fecha.
6. Conserva la fuente de procedencia.
7. Detecta duplicados.
8. Fusiona metadatos de registros duplicados.
9. Genera:
   - un RIS normalizado por fuente;
   - un RIS maestro consolidado;
   - un informe CSV de duplicados;
   - un informe CSV resumen por fuente.
"""

from pathlib import Path
from collections import defaultdict
import csv
import re
import unicodedata
import hashlib


# ==========================================================
# CONFIGURACIÓN
# ==========================================================

DIRECTORIO_ENTRADA = Path("ris_originales")
DIRECTORIO_SALIDA = Path("ris_normalizados")

RIS_MAESTRO = DIRECTORIO_SALIDA / "TFM_bibliografia_consolidada.ris"
CSV_DUPLICADOS = DIRECTORIO_SALIDA / "TFM_duplicados.csv"
CSV_RESUMEN = DIRECTORIO_SALIDA / "TFM_resumen_normalizacion.csv"


# Permite identificar automáticamente la fuente a partir
# del nombre del fichero.
FUENTES = {
    "ieee": "IEEE Xplore",
    "springer": "Springer Nature Link",
    "acm": "ACM Digital Library",
    "sciencedirect": "ScienceDirect",
    "science_direct": "ScienceDirect",
    "wos": "Web of Science Core Collection",
    "web_of_science": "Web of Science Core Collection",
    "webofscience": "Web of Science Core Collection",
    "savedrecs": "Web of Science Core Collection",
    "scopus": "Scopus",
}


# ==========================================================
# LECTURA DE RIS
# ==========================================================

def analizar_ris(ruta):
    """
    Lee un fichero RIS y devuelve una lista de registros.
    Cada registro es un diccionario:
        etiqueta -> lista de valores
    """

    registros = []
    actual = defaultdict(list)

    ultima_etiqueta = None

    with ruta.open(
        "r",
        encoding="utf-8-sig",
        errors="replace"
    ) as archivo:

        for linea_bruta in archivo:
            linea = linea_bruta.rstrip("\r\n")

            coincidencia = re.match(
                r"^([A-Z0-9]{2})  - ?(.*)$",
                linea
            )

            if coincidencia:
                etiqueta = coincidencia.group(1)
                valor = coincidencia.group(2).strip()

                if etiqueta == "TY":
                    if actual:
                        registros.append(dict(actual))

                    actual = defaultdict(list)

                actual[etiqueta].append(valor)
                ultima_etiqueta = etiqueta

                if etiqueta == "ER":
                    registros.append(dict(actual))
                    actual = defaultdict(list)
                    ultima_etiqueta = None

            elif ultima_etiqueta and linea.strip():
                # Continuación de campo multilínea
                actual[ultima_etiqueta][-1] += (
                    " " + linea.strip()
                )

    if actual:
        registros.append(dict(actual))

    return registros


# ==========================================================
# FUNCIONES AUXILIARES
# ==========================================================

def primero(registro, *etiquetas):
    """Devuelve el primer valor existente entre varios tags."""

    for etiqueta in etiquetas:
        valores = registro.get(etiqueta, [])

        if valores:
            valor = valores[0].strip()

            if valor:
                return valor

    return ""


def limpiar_espacios(texto):
    """Elimina espacios redundantes."""

    if not texto:
        return ""

    return re.sub(
        r"\s+",
        " ",
        texto
    ).strip()


# ==========================================================
# NORMALIZACIÓN DE DOI
# ==========================================================

def normalizar_doi(doi):
    """
    Convierte DOI a formato uniforme.
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

    doi = doi.strip()

    # Elimina puntuación residual al final
    doi = doi.rstrip(" .;,)]}")

    return doi


# ==========================================================
# NORMALIZACIÓN DE TÍTULOS
# ==========================================================

def normalizar_titulo(titulo):
    """
    Genera una versión normalizada del título SOLO
    para comparación y deduplicación.
    """

    if not titulo:
        return ""

    titulo = titulo.lower()

    # Unicode homogéneo
    titulo = unicodedata.normalize(
        "NFKD",
        titulo
    )

    titulo = "".join(
        caracter
        for caracter in titulo
        if not unicodedata.combining(caracter)
    )

    # Comillas tipográficas
    titulo = (
        titulo
        .replace("“", '"')
        .replace("”", '"')
        .replace("‘", "'")
        .replace("’", "'")
    )

    # Guiones
    titulo = re.sub(
        r"[‐-–—]",
        "-",
        titulo
    )

    # Signos de puntuación -> espacio
    titulo = re.sub(
        r"[^a-z0-9]+",
        " ",
        titulo
    )

    # Espacios múltiples
    titulo = re.sub(
        r"\s+",
        " ",
        titulo
    )

    return titulo.strip()


# ==========================================================
# NORMALIZACIÓN DE AUTORES
# ==========================================================

def normalizar_autor(autor):
    """
    Genera una versión sencilla del nombre para
    comparación.
    """

    if not autor:
        return ""

    autor = unicodedata.normalize(
        "NFKD",
        autor.lower()
    )

    autor = "".join(
        caracter
        for caracter in autor
        if not unicodedata.combining(caracter)
    )

    autor = re.sub(
        r"[^a-z0-9]+",
        " ",
        autor
    )

    return limpiar_espacios(autor)


def primer_autor(registro):

    autores = (
        registro.get("AU")
        or registro.get("A1")
        or []
    )

    if not autores:
        return ""

    return normalizar_autor(autores[0])


# ==========================================================
# AÑO Y FECHAS
# ==========================================================

def extraer_anio(registro):

    candidatos = [
        primero(registro, "PY"),
        primero(registro, "Y1"),
        primero(registro, "DA"),
    ]

    for valor in candidatos:

        coincidencia = re.search(
            r"\b(19|20)\d{2}\b",
            valor
        )

        if coincidencia:
            return coincidencia.group(0)

    return ""


def normalizar_fecha(valor_fecha):
    """
    Normaliza fechas sin inventar datos faltantes.

    Ejemplos:
        2025-03-15 -> 2025/03/15/
        2025/03/15 -> 2025/03/15/
        2025-03    -> 2025/03/
        2025       -> 2025/
    """

    if not valor_fecha:
        return ""

    valor_fecha = valor_fecha.strip()

    coincidencia = re.search(
        r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})",
        valor_fecha
    )

    if coincidencia:
        anio, mes, dia = coincidencia.groups()

        return (
            f"{anio}/"
            f"{int(mes):02d}/"
            f"{int(dia):02d}/"
        )

    coincidencia = re.search(
        r"(\d{4})[-/](\d{1,2})",
        valor_fecha
    )

    if coincidencia:
        anio, mes = coincidencia.groups()

        return (
            f"{anio}/"
            f"{int(mes):02d}/"
        )

    coincidencia = re.search(
        r"\b(\d{4})\b",
        valor_fecha
    )

    if coincidencia:
        return f"{coincidencia.group(1)}/"

    return valor_fecha


# ==========================================================
# IDENTIFICACIÓN DE LA FUENTE
# ==========================================================

def detectar_fuente(ruta):

    nombre = ruta.name.lower()

    for pista, fuente in FUENTES.items():

        if pista in nombre:
            return fuente

    return ruta.stem


# ==========================================================
# HOMOGENEIZACIÓN DE CAMPOS RIS
# ==========================================================

def normalizar_registro(registro, fuente):
    """
    Genera un registro RIS homogéneo.
    """

    normalizado = defaultdict(list)

    # Tipo
    normalizado["TY"] = [
        primero(registro, "TY") or "GEN"
    ]

    # Título
    titulo = primero(
        registro,
        "TI",
        "T1",
        "CT"
    )

    if titulo:
        normalizado["TI"] = [
            limpiar_espacios(titulo)
        ]

    # Autores
    autores = (
        registro.get("AU")
        or registro.get("A1")
        or registro.get("A2")
        or []
    )

    for autor in autores:
        autor = limpiar_espacios(autor)

        if autor:
            normalizado["AU"].append(autor)

    # Año
    anio = extraer_anio(registro)

    if anio:
        normalizado["PY"] = [anio]

    # Fecha
    fecha = primero(
        registro,
        "DA",
        "Y1"
    )

    if fecha:
        normalizado["DA"] = [
            normalizar_fecha(fecha)
        ]

    # Abstract
    resumen = primero(
        registro,
        "AB",
        "N2"
    )

    if resumen:
        normalizado["AB"] = [
            limpiar_espacios(resumen)
        ]

    # Keywords
    palabras_clave = []

    for etiqueta in ("KW", "K1"):

        for palabra_clave in registro.get(
            etiqueta,
            []
        ):
            palabra_clave = limpiar_espacios(
                palabra_clave
            )

            if (
                palabra_clave
                and palabra_clave.lower()
                not in [
                    elemento.lower()
                    for elemento in palabras_clave
                ]
            ):
                palabras_clave.append(
                    palabra_clave
                )

    normalizado["KW"] = palabras_clave

    # DOI
    doi = primero(registro, "DO")

    # Algunos RIS incluyen DOI solo dentro de URL
    if not doi:

        for url in registro.get("UR", []):

            coincidencia = re.search(
                r"(10\.\d{4,9}/[-._;()/:a-zA-Z0-9]+)",
                url
            )

            if coincidencia:
                doi = coincidencia.group(1)
                break

    doi = normalizar_doi(doi)

    if doi:
        normalizado["DO"] = [doi]

    # Revista / publicación
    revista = primero(
        registro,
        "JO",
        "JF",
        "JA"
    )

    if revista:
        normalizado["JO"] = [
            limpiar_espacios(revista)
        ]

    # Congreso / libro / proceedings
    titulo_secundario = primero(
        registro,
        "T2",
        "BT"
    )

    if titulo_secundario:
        normalizado["T2"] = [
            limpiar_espacios(
                titulo_secundario
            )
        ]

    # Volumen
    valor = primero(registro, "VL")

    if valor:
        normalizado["VL"] = [valor]

    # Número
    valor = primero(registro, "IS")

    if valor:
        normalizado["IS"] = [valor]

    # Páginas
    valor = primero(registro, "SP")

    if valor:
        normalizado["SP"] = [valor]

    valor = primero(registro, "EP")

    if valor:
        normalizado["EP"] = [valor]

    # ISSN/ISBN
    for valor in registro.get("SN", []):
        if valor:
            normalizado["SN"].append(valor)

    # URL
    for valor in registro.get("UR", []):

        if (
            valor
            and valor not in normalizado["UR"]
        ):
            normalizado["UR"].append(valor)

    # Editorial
    valor = primero(registro, "PB")

    if valor:
        normalizado["PB"] = [
            limpiar_espacios(valor)
        ]

    # Idioma
    valor = primero(registro, "LA")

    if valor:
        normalizado["LA"] = [valor]

    # Fuente de procedencia
    normalizado["DB"] = [fuente]

    # Conservamos también la procedencia como nota,
    # útil al importar posteriormente a Zotero.
    normalizado["N1"].append(
        f"Fuente de información: {fuente}"
    )

    return dict(normalizado)


# ==========================================================
# CLAVE PARA DEDUPLICACIÓN
# ==========================================================

def claves_duplicado(registro):
    """
    Devuelve claves posibles para identificar un trabajo.

    Nivel 1: DOI
    Nivel 2: título + año + primer autor
    """

    doi = normalizar_doi(
        primero(registro, "DO")
    )

    titulo = normalizar_titulo(
        primero(
            registro,
            "TI",
            "T1"
        )
    )

    anio = extraer_anio(registro)

    autor = primer_autor(registro)

    clave_doi = None
    clave_bibliografica = None

    if doi:
        clave_doi = f"DOI::{doi}"

    if titulo and anio and autor:

        clave_bibliografica = (
            f"TITLE::{titulo}"
            f"::YEAR::{anio}"
            f"::AUTHOR::{autor}"
        )

    return clave_doi, clave_bibliografica


# ==========================================================
# FUSIÓN DE METADATOS
# ==========================================================

def fusionar_registros(base, entrante):
    """
    Fusiona dos registros que corresponden inequívocamente
    a la misma publicación.

    - conserva valores existentes;
    - añade valores ausentes;
    - conserva todos los autores;
    - conserva keywords;
    - conserva URL;
    - conserva todas las fuentes.
    """

    campos_multiples = {
        "AU",
        "KW",
        "UR",
        "SN",
    }

    for etiqueta, valores in entrante.items():

        if not valores:
            continue

        if etiqueta in campos_multiples:

            if etiqueta not in base:
                base[etiqueta] = []

            valores_existentes_minusculas = {
                elemento.lower()
                for elemento in base[etiqueta]
            }

            for valor in valores:

                if (
                    valor.lower()
                    not in valores_existentes_minusculas
                ):
                    base[etiqueta].append(valor)

                    valores_existentes_minusculas.add(
                        valor.lower()
                    )

        elif etiqueta == "AB":

            # Conservamos el abstract más completo
            existente = primero(
                base,
                "AB"
            )

            candidato = valores[0]

            if len(candidato) > len(existente):
                base["AB"] = [candidato]

        elif etiqueta == "DB":

            fuentes_existentes = set(
                primero(base, "DB").split("; ")
                if primero(base, "DB")
                else []
            )

            for valor in valores:
                fuentes_existentes.add(valor)

            base["DB"] = [
                "; ".join(
                    sorted(fuentes_existentes)
                )
            ]

        elif etiqueta == "N1":
            # Las notas de procedencia se regeneran
            # posteriormente.
            continue

        else:

            if not base.get(etiqueta):
                base[etiqueta] = valores[:]

    # Regenera nota de procedencia
    fuentes = primero(
        base,
        "DB"
    )

    base["N1"] = [
        f"Fuentes de información: {fuentes}"
    ]

    return base


# ==========================================================
# ID INTERNO ÚNICO
# ==========================================================

def identificador_interno(registro, contador):
    """
    Identificador interno para trazabilidad.
    """

    doi = normalizar_doi(
        primero(registro, "DO")
    )

    if doi:

        huella = hashlib.sha1(
            doi.encode("utf-8")
        ).hexdigest()[:10]

        return f"TFM-{huella.upper()}"

    return f"TFM-{contador:06d}"


# ==========================================================
# ESCRITURA RIS
# ==========================================================

ORDEN_RIS = [
    "TY",
    "ID",
    "TI",
    "AU",
    "PY",
    "DA",
    "JO",
    "T2",
    "VL",
    "IS",
    "SP",
    "EP",
    "SN",
    "DO",
    "UR",
    "LA",
    "KW",
    "AB",
    "PB",
    "DB",
    "N1",
]


def escribir_ris(registros, ruta):

    with ruta.open(
        "w",
        encoding="utf-8",
        newline="\n"
    ) as archivo:

        for registro in registros:

            etiquetas_escritas = set()

            for etiqueta in ORDEN_RIS:

                for valor in registro.get(
                    etiqueta,
                    []
                ):

                    if valor:
                        archivo.write(
                            f"{etiqueta}  - {valor}\n"
                        )

                etiquetas_escritas.add(
                    etiqueta
                )

            # Conserva campos adicionales no previstos
            for etiqueta, valores in registro.items():

                if (
                    etiqueta in etiquetas_escritas
                    or etiqueta == "ER"
                ):
                    continue

                for valor in valores:

                    if valor:
                        archivo.write(
                            f"{etiqueta}  - {valor}\n"
                        )

            archivo.write("ER  - \n\n")


# ==========================================================
# PROCESO PRINCIPAL
# ==========================================================

def principal():

    DIRECTORIO_SALIDA.mkdir(
        parents=True,
        exist_ok=True
    )

    archivos = sorted(
        DIRECTORIO_ENTRADA.glob("*.ris")
    )

    if not archivos:

        print(
            f"No se han encontrado RIS en: "
            f"{DIRECTORIO_ENTRADA.resolve()}"
        )

        return

    todos_registros = []

    resumen_fuentes = []

    print("\nNORMALIZACIÓN POR FUENTE")
    print("=" * 60)

    for ruta in archivos:

        fuente = detectar_fuente(ruta)

        registros = analizar_ris(ruta)

        registros_normalizados = []

        for registro in registros:

            normalizado = normalizar_registro(
                registro,
                fuente
            )

            registros_normalizados.append(
                normalizado
            )

            todos_registros.append(
                normalizado
            )

        archivo_salida = (
            DIRECTORIO_SALIDA
            / f"{ruta.stem}_NORMALIZADO.ris"
        )

        escribir_ris(
            registros_normalizados,
            archivo_salida
        )

        resumen_fuentes.append({
            "fuente": fuente,
            "archivo": ruta.name,
            "registros": len(registros),
            "archivo_normalizado":
                archivo_salida.name,
        })

        print(
            f"{fuente:35}"
            f"{len(registros):6} registros"
        )

    print("\nCONSOLIDACIÓN GLOBAL")
    print("=" * 60)

    # Índices
    indice_doi = {}
    indice_bibliografico = {}

    consolidados = []

    informe_duplicados = []

    for registro in todos_registros:

        clave_doi, clave_bibliografica = (
            claves_duplicado(registro)
        )

        indice_existente = None
        motivo_duplicado = None

        # 1. DOI
        if (
            clave_doi
            and clave_doi in indice_doi
        ):

            indice_existente = indice_doi[
                clave_doi
            ]

            motivo_duplicado = "DOI"

        # 2. título + año + autor
        elif (
            clave_bibliografica
            and clave_bibliografica
            in indice_bibliografico
        ):

            indice_existente = (
                indice_bibliografico[
                    clave_bibliografica
                ]
            )

            motivo_duplicado = (
                "Título + año + primer autor"
            )

        if indice_existente is not None:

            base = consolidados[
                indice_existente
            ]

            fuentes_anteriores = primero(
                base,
                "DB"
            )

            fuente_nueva = primero(
                registro,
                "DB"
            )

            fusionar_registros(
                base,
                registro
            )

            informe_duplicados.append({
                "motivo":
                    motivo_duplicado,
                "titulo":
                    primero(
                        registro,
                        "TI"
                    ),
                "doi":
                    primero(
                        registro,
                        "DO"
                    ),
                "fuente_existente":
                    fuentes_anteriores,
                "fuente_duplicada":
                    fuente_nueva,
            })

        else:

            indice = len(consolidados)

            consolidados.append(registro)

            if clave_doi:
                indice_doi[
                    clave_doi
                ] = indice

            if clave_bibliografica:
                indice_bibliografico[
                    clave_bibliografica
                ] = indice

    # Asignación de IDs internos
    for numero, registro in enumerate(
        consolidados,
        start=1
    ):

        registro["ID"] = [
            identificador_interno(
                registro,
                numero
            )
        ]

    # RIS maestro
    escribir_ris(
        consolidados,
        RIS_MAESTRO
    )

    # Informe de duplicados
    with CSV_DUPLICADOS.open(
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as archivo:

        campos = [
            "motivo",
            "titulo",
            "doi",
            "fuente_existente",
            "fuente_duplicada",
        ]

        escritor = csv.DictWriter(
            archivo,
            fieldnames=campos
        )

        escritor.writeheader()

        escritor.writerows(
            informe_duplicados
        )

    # Resumen por fuente
    with CSV_RESUMEN.open(
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as archivo:

        campos = [
            "fuente",
            "archivo",
            "registros",
            "archivo_normalizado",
        ]

        escritor = csv.DictWriter(
            archivo,
            fieldnames=campos
        )

        escritor.writeheader()

        escritor.writerows(
            resumen_fuentes
        )

    print(
        f"Registros iniciales: "
        f"{len(todos_registros)}"
    )

    print(
        f"Duplicados detectados: "
        f"{len(informe_duplicados)}"
    )

    print(
        f"Registros únicos: "
        f"{len(consolidados)}"
    )

    print("\nARCHIVOS GENERADOS")
    print("=" * 60)

    print(RIS_MAESTRO)
    print(CSV_DUPLICADOS)
    print(CSV_RESUMEN)


if __name__ == "__main__":
    principal()