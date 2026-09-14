#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Cribado por idioma de referencias bibliográficas
a partir de una exportación Zotero RDF.

Revisión sistemática PRISMA / PRISMA-S

Funciones principales:
1. Lee el fichero RDF exportado desde Zotero.
2. Ignora adjuntos y otros elementos no bibliográficos.
3. Recupera el TFM-ID almacenado en el campo Adicional.
4. Utiliza el idioma explícito de Zotero cuando existe.
5. Para los registros sin idioma:
   - analiza título + abstract;
   - detecta automáticamente el idioma;
   - calcula la confianza.
6. Clasifica los registros como:
   - INCLUIR_INGLES;
   - EXCLUIR_NO_INGLES;
   - REVISION_MANUAL.
7. Genera CSV independientes para cada resultado.
8. Genera un resumen final de la ejecución.

Criterio metodológico:
La detección automática se utiliza como apoyo.
Un registro sin metadato explícito que parezca estar
escrito en un idioma distinto del inglés no se excluye
automáticamente: pasa a revisión manual.
"""

from pathlib import Path
import csv
import re
import html
import xml.etree.ElementTree as ET

from langdetect import detect_langs
from langdetect import DetectorFactory
from langdetect.lang_detect_exception import LangDetectException


# ==========================================================
# CONFIGURACIÓN
# ==========================================================

ARCHIVO_RDF_ENTRADA = Path(
    "TFM_PENDIENTES_CRIBA_5453.rdf"
)

DIRECTORIO_SALIDA = Path(
    "cribado_idioma"
)

ARCHIVO_RESULTADOS = (
    DIRECTORIO_SALIDA
    / "TFM_cribado_idioma_resultados.csv"
)

ARCHIVO_INGLES = (
    DIRECTORIO_SALIDA
    / "TFM_cribado_idioma_ingles.csv"
)

ARCHIVO_NO_INGLES = (
    DIRECTORIO_SALIDA
    / "TFM_cribado_idioma_no_ingles.csv"
)

ARCHIVO_REVISION_MANUAL = (
    DIRECTORIO_SALIDA
    / "TFM_cribado_idioma_revision_manual.csv"
)

ARCHIVO_RESUMEN = (
    DIRECTORIO_SALIDA
    / "TFM_cribado_idioma_resumen.txt"
)

NUMERO_ESPERADO_REGISTROS = 5453

# Probabilidad mínima para aceptar automáticamente
# que un texto está redactado en inglés.
UMBRAL_INGLES = 0.95

# Número mínimo de palabras para aceptar una
# detección automática basada en título + abstract.
NUMERO_MINIMO_PALABRAS = 40

# Hace reproducibles los resultados de langdetect.
DetectorFactory.seed = 0


# ==========================================================
# ESPACIOS DE NOMBRES RDF
# ==========================================================

ESPACIOS_NOMBRES = {
    "rdf":
        "http://www.w3.org/1999/02/22-rdf-syntax-ns#",

    "dc":
        "http://purl.org/dc/elements/1.1/",

    "dcterms":
        "http://purl.org/dc/terms/",

    "z":
        "http://www.zotero.org/namespaces/export#",

    "bib":
        "http://purl.org/net/biblio#",
}


# ==========================================================
# FUNCIONES AUXILIARES
# ==========================================================

def limpiar_texto(texto):
    """
    Elimina etiquetas HTML y espacios redundantes.
    """

    if not texto:
        return ""

    texto = str(texto)

    texto = re.sub(
        r"<[^>]+>",
        " ",
        texto
    )

    texto = html.unescape(
        texto
    )

    return re.sub(
        r"\s+",
        " ",
        texto
    ).strip()


def texto_elemento(elemento):
    """
    Obtiene el texto limpio de un elemento XML.
    """

    if elemento is None:
        return ""

    return limpiar_texto(
        "".join(
            elemento.itertext()
        )
    )


# ==========================================================
# IDENTIFICACIÓN DEL TFM-ID
# ==========================================================

def obtener_tfm_id(elemento):
    """
    Recupera el identificador interno almacenado
    en el campo Adicional de Zotero.

    Admite los dos formatos existentes:

        TFM-ID: TFM-XXXXXXXXXX

    y:

        TFM-XXXXXXXXXX
    """

    descripciones = elemento.findall(
        "dc:description",
        ESPACIOS_NOMBRES
    )

    for descripcion in descripciones:

        texto = texto_elemento(
            descripcion
        )

        coincidencia = re.search(
            r"TFM-ID:\s*(TFM-[A-Z0-9]+)",
            texto,
            re.IGNORECASE
        )

        if coincidencia:

            return coincidencia.group(
                1
            ).upper()

        coincidencia = re.fullmatch(
            r"\s*(TFM-[A-Z0-9]+)\s*",
            texto,
            re.IGNORECASE
        )

        if coincidencia:

            return coincidencia.group(
                1
            ).upper()

    return ""


# ==========================================================
# EXTRACCIÓN DE CAMPOS RDF
# ==========================================================

def obtener_titulo(elemento):
    """
    Recupera el título.
    """

    return texto_elemento(
        elemento.find(
            "dc:title",
            ESPACIOS_NOMBRES
        )
    )


def obtener_abstract(elemento):
    """
    Recupera el abstract.
    """

    return texto_elemento(
        elemento.find(
            "dcterms:abstract",
            ESPACIOS_NOMBRES
        )
    )


def obtener_fecha(elemento):
    """
    Recupera la fecha o año.
    """

    return texto_elemento(
        elemento.find(
            "dc:date",
            ESPACIOS_NOMBRES
        )
    )


def obtener_idioma(elemento):
    """
    Recupera el idioma explícito.
    """

    return texto_elemento(
        elemento.find(
            "z:language",
            ESPACIOS_NOMBRES
        )
    )


def obtener_doi(elemento):
    """
    Recupera el DOI de los identificadores RDF.
    """

    identificadores = elemento.findall(
        "dc:identifier",
        ESPACIOS_NOMBRES
    )

    for identificador in identificadores:

        texto = texto_elemento(
            identificador
        )

        coincidencia = re.search(
            r"(?:DOI\s*)?"
            r"(10\.\d{4,9}/\S+)",
            texto,
            re.IGNORECASE
        )

        if coincidencia:

            return coincidencia.group(
                1
            ).rstrip(
                " .;,)]}"
            ).lower()

    return ""


def obtener_tipo_documental(elemento):
    """
    Recupera el tipo documental definido por Zotero.
    """

    return texto_elemento(
        elemento.find(
            "z:itemType",
            ESPACIOS_NOMBRES
        )
    )


# ==========================================================
# SELECCIÓN DE ELEMENTOS BIBLIOGRÁFICOS
# ==========================================================

def es_elemento_bibliografico(elemento):
    """
    Determina si el nodo RDF representa una
    referencia bibliográfica.

    Se excluyen adjuntos y notas.
    """

    tipo = obtener_tipo_documental(
        elemento
    )

    if not tipo:

        return False

    tipos_excluidos = {
        "attachment",
        "note"
    }

    return (
        tipo.lower()
        not in tipos_excluidos
    )


# ==========================================================
# DETECCIÓN AUTOMÁTICA
# ==========================================================

def detectar_idioma(texto):
    """
    Detecta el idioma mediante langdetect.

    Devuelve:
    - idioma principal;
    - confianza;
    - probabilidad de inglés;
    - detalle completo.
    """

    if not texto:

        return (
            "",
            0.0,
            0.0,
            ""
        )

    try:

        resultados = detect_langs(
            texto
        )

    except LangDetectException:

        return (
            "",
            0.0,
            0.0,
            ""
        )

    if not resultados:

        return (
            "",
            0.0,
            0.0,
            ""
        )

    idioma_principal = (
        resultados[0].lang
    )

    confianza_principal = (
        resultados[0].prob
    )

    probabilidad_ingles = 0.0

    for resultado in resultados:

        if resultado.lang == "en":

            probabilidad_ingles = (
                resultado.prob
            )

            break

    detalle = "; ".join(
        f"{resultado.lang}:"
        f"{resultado.prob:.4f}"
        for resultado in resultados
    )

    return (
        idioma_principal,
        confianza_principal,
        probabilidad_ingles,
        detalle
    )


# ==========================================================
# INTERPRETACIÓN DEL IDIOMA EXPLÍCITO
# ==========================================================

def interpretar_idioma_explicito(
    idioma
):
    """
    Normaliza los valores habituales de idioma.
    """

    if not idioma:

        return "SIN_METADATO"

    idioma_normalizado = (
        idioma.strip().lower()
    )

    equivalentes_ingles = {
        "english",
        "eng",
        "en"
    }

    if (
        idioma_normalizado
        in equivalentes_ingles
    ):

        return "INGLES"

    return "NO_INGLES"


# ==========================================================
# CLASIFICACIÓN
# ==========================================================

def clasificar_registro(elemento):
    """
    Aplica el criterio de idioma.
    """

    idioma_explicito = (
        obtener_idioma(
            elemento
        )
    )

    interpretacion = (
        interpretar_idioma_explicito(
            idioma_explicito
        )
    )

    # ------------------------------------------------------
    # IDIOMA EXPLÍCITO EN INGLÉS
    # ------------------------------------------------------

    if interpretacion == "INGLES":

        return {
            "decision":
                "INCLUIR_INGLES",

            "metodo":
                "METADATO_ZOTERO",

            "idioma_detectado":
                "en",

            "confianza":
                "1.0000",

            "probabilidad_ingles":
                "1.0000",

            "detalle":
                "",

            "numero_palabras":
                "",

            "motivo":
                (
                    "Zotero contiene "
                    "explícitamente el idioma English."
                )
        }

    # ------------------------------------------------------
    # IDIOMA EXPLÍCITO DISTINTO DEL INGLÉS
    # ------------------------------------------------------

    if interpretacion == "NO_INGLES":

        return {
            "decision":
                "EXCLUIR_NO_INGLES",

            "metodo":
                "METADATO_ZOTERO",

            "idioma_detectado":
                idioma_explicito,

            "confianza":
                "1.0000",

            "probabilidad_ingles":
                "0.0000",

            "detalle":
                "",

            "numero_palabras":
                "",

            "motivo":
                (
                    "Zotero contiene explícitamente "
                    "un idioma distinto del inglés."
                )
        }

    # ------------------------------------------------------
    # SIN METADATO DE IDIOMA
    # ------------------------------------------------------

    titulo = obtener_titulo(
        elemento
    )

    abstract = obtener_abstract(
        elemento
    )

    texto_analisis = limpiar_texto(
        f"{titulo}. {abstract}"
    )

    numero_palabras = len(
        texto_analisis.split()
    )

    if (
        numero_palabras
        < NUMERO_MINIMO_PALABRAS
    ):

        return {
            "decision":
                "REVISION_MANUAL",

            "metodo":
                "TEXTO_INSUFICIENTE",

            "idioma_detectado":
                "",

            "confianza":
                "",

            "probabilidad_ingles":
                "",

            "detalle":
                "",

            "numero_palabras":
                numero_palabras,

            "motivo":
                (
                    "No existe metadato de idioma "
                    "y el texto disponible es "
                    "insuficiente para una decisión "
                    "automática fiable."
                )
        }

    (
        idioma_detectado,
        confianza,
        probabilidad_ingles,
        detalle
    ) = detectar_idioma(
        texto_analisis
    )

    if not idioma_detectado:

        return {
            "decision":
                "REVISION_MANUAL",

            "metodo":
                "DETECCION_FALLIDA",

            "idioma_detectado":
                "",

            "confianza":
                "",

            "probabilidad_ingles":
                "",

            "detalle":
                "",

            "numero_palabras":
                numero_palabras,

            "motivo":
                (
                    "No ha sido posible determinar "
                    "automáticamente el idioma."
                )
        }

    # ------------------------------------------------------
    # INGLÉS CON CONFIANZA SUFICIENTE
    # ------------------------------------------------------

    if (
        idioma_detectado == "en"
        and probabilidad_ingles
        >= UMBRAL_INGLES
    ):

        return {
            "decision":
                "INCLUIR_INGLES",

            "metodo":
                "DETECCION_AUTOMATICA",

            "idioma_detectado":
                idioma_detectado,

            "confianza":
                f"{confianza:.4f}",

            "probabilidad_ingles":
                f"{probabilidad_ingles:.4f}",

            "detalle":
                detalle,

            "numero_palabras":
                numero_palabras,

            "motivo":
                (
                    "Sin metadato explícito. "
                    "Título y abstract han sido "
                    "detectados como inglés con "
                    "alta confianza."
                )
        }

    # ------------------------------------------------------
    # CUALQUIER OTRO RESULTADO
    # ------------------------------------------------------

    return {
        "decision":
            "REVISION_MANUAL",

        "metodo":
            (
                "POSIBLE_NO_INGLES"
                if idioma_detectado != "en"
                else "DETECCION_DUDOSA"
            ),

        "idioma_detectado":
            idioma_detectado,

        "confianza":
            f"{confianza:.4f}",

        "probabilidad_ingles":
            f"{probabilidad_ingles:.4f}",

        "detalle":
            detalle,

        "numero_palabras":
            numero_palabras,

        "motivo":
            (
                "La detección automática no "
                "permite confirmar con suficiente "
                "seguridad que la publicación "
                "esté escrita en inglés. "
                "Se requiere revisión manual."
            )
    }


# ==========================================================
# GENERACIÓN DE RESULTADOS
# ==========================================================

COLUMNAS = [
    "tfm_id",
    "titulo",
    "anio",
    "doi",
    "tipo_documental",
    "idioma_zotero",
    "idioma_detectado",
    "confianza",
    "probabilidad_ingles",
    "detalle_probabilidades",
    "numero_palabras_analizadas",
    "metodo_decision",
    "decision",
    "motivo",
    "extracto_abstract",
    "idioma_confirmado_manual",
    "decision_manual",
    "observaciones_manual",
]


def generar_fila(elemento):
    """
    Genera una fila de resultados.
    """

    resultado = clasificar_registro(
        elemento
    )

    abstract = obtener_abstract(
        elemento
    )

    return {
        "tfm_id":
            obtener_tfm_id(
                elemento
            ),

        "titulo":
            obtener_titulo(
                elemento
            ),

        "anio":
            obtener_fecha(
                elemento
            ),

        "doi":
            obtener_doi(
                elemento
            ),

        "tipo_documental":
            obtener_tipo_documental(
                elemento
            ),

        "idioma_zotero":
            obtener_idioma(
                elemento
            ),

        "idioma_detectado":
            resultado[
                "idioma_detectado"
            ],

        "confianza":
            resultado[
                "confianza"
            ],

        "probabilidad_ingles":
            resultado[
                "probabilidad_ingles"
            ],

        "detalle_probabilidades":
            resultado[
                "detalle"
            ],

        "numero_palabras_analizadas":
            resultado[
                "numero_palabras"
            ],

        "metodo_decision":
            resultado[
                "metodo"
            ],

        "decision":
            resultado[
                "decision"
            ],

        "motivo":
            resultado[
                "motivo"
            ],

        "extracto_abstract":
            abstract[:500],

        "idioma_confirmado_manual":
            "",

        "decision_manual":
            "",

        "observaciones_manual":
            "",
    }


# ==========================================================
# ESCRITURA DE CSV
# ==========================================================

def escribir_csv(
    filas,
    ruta
):
    """
    Escribe un CSV UTF-8 compatible con Excel.
    """

    with ruta.open(
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as archivo:

        escritor = csv.DictWriter(
            archivo,
            fieldnames=COLUMNAS
        )

        escritor.writeheader()

        escritor.writerows(
            filas
        )


# ==========================================================
# PROCESO PRINCIPAL
# ==========================================================

def principal():

    print()
    print(
        "CRIBADO POR IDIOMA - ZOTERO RDF"
    )
    print("=" * 70)

    if not ARCHIVO_RDF_ENTRADA.exists():

        print(
            "ERROR: No se encuentra:"
        )

        print(
            ARCHIVO_RDF_ENTRADA.resolve()
        )

        return

    DIRECTORIO_SALIDA.mkdir(
        parents=True,
        exist_ok=True
    )

    arbol = ET.parse(
        ARCHIVO_RDF_ENTRADA
    )

    raiz = arbol.getroot()

    elementos = [
        elemento
        for elemento in raiz
        if es_elemento_bibliografico(
            elemento
        )
    ]

    print(
        f"Referencias bibliográficas: "
        f"{len(elementos)}"
    )

    if (
        len(elementos)
        != NUMERO_ESPERADO_REGISTROS
    ):

        raise ValueError(
            "El RDF no contiene el número "
            "esperado de referencias. "
            f"Esperadas: "
            f"{NUMERO_ESPERADO_REGISTROS}. "
            f"Encontradas: "
            f"{len(elementos)}."
        )

    # ------------------------------------------------------
    # CONTROL DE TFM-ID
    # ------------------------------------------------------

    identificadores = [
        obtener_tfm_id(
            elemento
        )
        for elemento in elementos
    ]

    sin_identificador = [
        elemento
        for elemento, identificador
        in zip(
            elementos,
            identificadores
        )
        if not identificador
    ]

    if sin_identificador:

        raise ValueError(
            "Existen referencias sin TFM-ID: "
            f"{len(sin_identificador)}"
        )

    if (
        len(set(identificadores))
        != len(identificadores)
    ):

        raise ValueError(
            "Existen TFM-ID duplicados."
        )

    print(
        "TFM-ID válidos y únicos: "
        f"{len(identificadores)}"
    )

    # ------------------------------------------------------
    # CLASIFICACIÓN
    # ------------------------------------------------------

    filas = [
        generar_fila(
            elemento
        )
        for elemento in elementos
    ]

    filas_ingles = [
        fila
        for fila in filas
        if fila["decision"]
        == "INCLUIR_INGLES"
    ]

    filas_no_ingles = [
        fila
        for fila in filas
        if fila["decision"]
        == "EXCLUIR_NO_INGLES"
    ]

    filas_revision = [
        fila
        for fila in filas
        if fila["decision"]
        == "REVISION_MANUAL"
    ]

    # ------------------------------------------------------
    # ESCRITURA
    # ------------------------------------------------------

    escribir_csv(
        filas,
        ARCHIVO_RESULTADOS
    )

    escribir_csv(
        filas_ingles,
        ARCHIVO_INGLES
    )

    escribir_csv(
        filas_no_ingles,
        ARCHIVO_NO_INGLES
    )

    escribir_csv(
        filas_revision,
        ARCHIVO_REVISION_MANUAL
    )

    # ------------------------------------------------------
    # RESUMEN
    # ------------------------------------------------------

    con_idioma_explicito = sum(
        1
        for elemento in elementos
        if obtener_idioma(
            elemento
        )
    )

    sin_idioma_explicito = (
        len(elementos)
        - con_idioma_explicito
    )

    resumen = (
        "CRIBADO POR IDIOMA\n"
        "====================================\n\n"

        f"Registros analizados: "
        f"{len(elementos)}\n"

        f"Con idioma explícito: "
        f"{con_idioma_explicito}\n"

        f"Sin idioma explícito: "
        f"{sin_idioma_explicito}\n\n"

        f"Clasificados como inglés: "
        f"{len(filas_ingles)}\n"

        f"Exclusiones confirmadas "
        f"por metadato: "
        f"{len(filas_no_ingles)}\n"

        f"Pendientes de revisión manual: "
        f"{len(filas_revision)}\n"
    )

    ARCHIVO_RESUMEN.write_text(
        resumen,
        encoding="utf-8"
    )

    print()
    print(resumen)

    print(
        "ARCHIVOS GENERADOS"
    )
    print("=" * 70)

    print(
        ARCHIVO_RESULTADOS
    )

    print(
        ARCHIVO_INGLES
    )

    print(
        ARCHIVO_NO_INGLES
    )

    print(
        ARCHIVO_REVISION_MANUAL
    )

    print(
        ARCHIVO_RESUMEN
    )


if __name__ == "__main__":
    principal()