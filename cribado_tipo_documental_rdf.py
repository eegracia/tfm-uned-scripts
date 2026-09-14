#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Cribado por tipo documental a partir de Zotero RDF
Revisión sistemática PRISMA / PRISMA-S

Funciones principales:
1. Lee la colección de referencias pendientes de cribado
   exportada desde Zotero en formato RDF.
2. Ignora adjuntos, notas y otros elementos que no
   constituyen referencias bibliográficas.
3. Recupera el TFM-ID almacenado en el campo Adicional.
4. Clasifica los registros según el tipo documental
   asignado por Zotero.
5. Detecta además títulos que pueden corresponder a:
   - editoriales;
   - correcciones;
   - erratas;
   - avisos de retractación;
   - entrevistas;
   - keynotes;
   - abstracts;
   - otros tipos documentales potencialmente no elegibles.
6. Genera tres resultados:
   - INCLUIR_TIPO_DOCUMENTAL;
   - EXCLUIR_TIPO_DOCUMENTAL;
   - REVISION_MANUAL_TIPO.
7. Los tipos ambiguos no se excluyen automáticamente.
8. Genera informes CSV y un resumen de la ejecución.

Criterio metodológico:
Solo se excluyen automáticamente aquellos tipos
documentales cuya incompatibilidad con los criterios
de inclusión sea inequívoca.

Los tipos potencialmente ambiguos se someten a
revisión manual antes de tomar una decisión definitiva.
"""

from pathlib import Path
from collections import Counter
import csv
import re
import html
import xml.etree.ElementTree as ET


# ==========================================================
# CONFIGURACIÓN
# ==========================================================

ARCHIVO_RDF_ENTRADA = Path(
    "TFM_PENDIENTES_CRIBA_5452.rdf"
)

DIRECTORIO_SALIDA = Path(
    "cribado_tipo_documental"
)

ARCHIVO_RESULTADOS = (
    DIRECTORIO_SALIDA
    / "TFM_cribado_tipo_resultados.csv"
)

ARCHIVO_ELEGIBLES = (
    DIRECTORIO_SALIDA
    / "TFM_cribado_tipo_elegibles.csv"
)

ARCHIVO_EXCLUIDOS = (
    DIRECTORIO_SALIDA
    / "TFM_cribado_tipo_excluidos.csv"
)

ARCHIVO_REVISION_MANUAL = (
    DIRECTORIO_SALIDA
    / "TFM_cribado_tipo_revision_manual.csv"
)

ARCHIVO_DISTRIBUCION = (
    DIRECTORIO_SALIDA
    / "TFM_cribado_tipo_distribucion.csv"
)

ARCHIVO_RESUMEN = (
    DIRECTORIO_SALIDA
    / "TFM_cribado_tipo_resumen.txt"
)

NUMERO_ESPERADO_REGISTROS = 5452


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
# TIPOS DOCUMENTALES
# ==========================================================

# Tipos directamente compatibles con los criterios
# de inclusión establecidos para la revisión.
TIPOS_ELEGIBLES = {
    "journalarticle",
    "conferencepaper",
}


# Tipos inequívocamente incompatibles con los criterios
# documentales de la revisión.
TIPOS_EXCLUIDOS = {
    "book",
    "thesis",
    "report",
    "webpage",
    "magazinearticle",
    "newspaperarticle",
    "blogpost",
    "preprint",
    "manuscript",
    "presentation",
    "interview",
    "letter",
    "patent",
    "encyclopediaarticle",
    "dictionaryentry",
    "forumpost",
    "email",
    "instantmessage",
    "hearing",
    "case",
    "statute",
    "bill",
    "artwork",
    "audiorecording",
    "videorecording",
    "podcast",
    "radiobroadcast",
    "tvbroadcast",
    "map",
    "dataset",
    "standard",
}


# Tipos que pueden representar documentos elegibles
# dependiendo de cómo hayan sido importados desde
# la fuente bibliográfica.
TIPOS_AMBIGUOS = {
    "booksection",
    "document",
}


# ==========================================================
# PATRONES DE TÍTULO QUE REQUIEREN REVISIÓN
# ==========================================================

PATRONES_TITULO_DUDOSO = [
    (
        r"^\s*editorial\b",
        "Posible editorial"
    ),
    (
        r"^\s*guest editorial\b",
        "Posible editorial invitada"
    ),
    (
        r"^\s*special issue editorial\b",
        "Posible editorial de número especial"
    ),
    (
        r"^\s*correction\b",
        "Posible corrección"
    ),
    (
        r"^\s*corrigendum\b",
        "Posible corrigendum"
    ),
    (
        r"^\s*erratum\b",
        "Posible errata"
    ),
    (
        r"^\s*retraction notice\b",
        "Posible aviso de retractación"
    ),
    (
        r"^\s*retracted article\b",
        "Posible artículo retractado"
    ),
    (
        r"^\s*retracted\s*:",
        "Posible artículo retractado"
    ),
    (
        r"^\s*withdrawal notice\b",
        "Posible aviso de retirada"
    ),
    (
        r"^\s*withdrawn\b",
        "Posible publicación retirada"
    ),
    (
        r"^\s*expression of concern\b",
        "Posible expresión de preocupación editorial"
    ),
    (
        r"^\s*interview\b",
        "Posible entrevista"
    ),
    (
        r"^\s*preface\b",
        "Posible prefacio"
    ),
    (
        r"^\s*foreword\b",
        "Posible prólogo"
    ),
    (
        r"^\s*keynote\b",
        "Posible keynote"
    ),
    (
        r"\bkeynote address\b",
        "Posible keynote"
    ),
    (
        r"\bextended abstract\b",
        "Posible extended abstract"
    ),
    (
        r"\bconference abstract\b",
        "Posible abstract de congreso"
    ),
    (
        r"^\s*poster\b",
        "Posible póster"
    ),
    (
        r"^\s*book review\b",
        "Posible reseña de libro"
    ),
    (
        r"^\s*letter to the editor\b",
        "Posible carta al editor"
    ),
    (
        r"^\s*introduction to the special issue\b",
        "Posible introducción de número especial"
    ),
    (
        r"^\s*call for papers\b",
        "Posible convocatoria editorial"
    ),
]


# ==========================================================
# FUNCIONES AUXILIARES
# ==========================================================

def limpiar_texto(texto):
    """
    Elimina HTML, decodifica entidades y normaliza
    espacios.
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
    Obtiene el texto completo de un elemento XML.
    """

    if elemento is None:
        return ""

    return limpiar_texto(
        "".join(
            elemento.itertext()
        )
    )


# ==========================================================
# IDENTIFICADOR INTERNO
# ==========================================================

def obtener_tfm_id(elemento):
    """
    Recupera el TFM-ID almacenado en el campo
    Adicional de Zotero.

    Admite:

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
# EXTRACCIÓN DE METADATOS
# ==========================================================

def obtener_titulo(elemento):
    """
    Recupera el título de la referencia.
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


def obtener_tipo_documental(elemento):
    """
    Recupera el tipo documental asignado por Zotero.
    """

    return texto_elemento(
        elemento.find(
            "z:itemType",
            ESPACIOS_NOMBRES
        )
    )


def obtener_doi(elemento):
    """
    Recupera el DOI cuando está disponible.
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


# ==========================================================
# IDENTIFICACIÓN DE REFERENCIAS BIBLIOGRÁFICAS
# ==========================================================

def es_elemento_bibliografico(elemento):
    """
    Excluye adjuntos y notas independientes del RDF.
    """

    tipo = obtener_tipo_documental(
        elemento
    )

    if not tipo:
        return False

    if tipo.lower() in {
        "attachment",
        "note"
    }:
        return False

    return True


# ==========================================================
# ANÁLISIS DEL TÍTULO
# ==========================================================

def detectar_patron_titulo(titulo):
    """
    Comprueba si el título contiene indicadores de
    un posible tipo documental no elegible.

    Devuelve el motivo detectado o cadena vacía.
    """

    if not titulo:
        return ""

    for patron, motivo in PATRONES_TITULO_DUDOSO:

        if re.search(
            patron,
            titulo,
            flags=re.IGNORECASE
        ):

            return motivo

    return ""


# ==========================================================
# CLASIFICACIÓN DEL TIPO DOCUMENTAL
# ==========================================================

def clasificar_registro(elemento):
    """
    Clasifica una referencia según su tipo documental.
    """

    tipo_original = obtener_tipo_documental(
        elemento
    )

    tipo = tipo_original.lower().strip()

    titulo = obtener_titulo(
        elemento
    )

    patron_dudoso = detectar_patron_titulo(
        titulo
    )

    # ------------------------------------------------------
    # TÍTULO POTENCIALMENTE NO ELEGIBLE
    # ------------------------------------------------------

    # Este control se realiza antes de aceptar un artículo
    # o conference paper porque Zotero puede clasificar,
    # por ejemplo, una corrección como journalArticle.
    if patron_dudoso:

        return {
            "decision":
                "REVISION_MANUAL_TIPO",

            "motivo":
                patron_dudoso,

            "criterio":
                "PATRON_TITULO"
        }

    # ------------------------------------------------------
    # TIPO ELEGIBLE
    # ------------------------------------------------------

    if tipo in TIPOS_ELEGIBLES:

        return {
            "decision":
                "INCLUIR_TIPO_DOCUMENTAL",

            "motivo":
                (
                    "Tipo documental compatible "
                    "con los criterios de inclusión."
                ),

            "criterio":
                "TIPO_ZOTERO"
        }

    # ------------------------------------------------------
    # TIPO EXCLUIDO
    # ------------------------------------------------------

    if tipo in TIPOS_EXCLUIDOS:

        return {
            "decision":
                "EXCLUIR_TIPO_DOCUMENTAL",

            "motivo":
                (
                    "Tipo documental no incluido "
                    "en los criterios de la revisión: "
                    f"{tipo_original}."
                ),

            "criterio":
                "TIPO_ZOTERO"
        }

    # ------------------------------------------------------
    # TIPO AMBIGUO
    # ------------------------------------------------------

    if tipo in TIPOS_AMBIGUOS:

        return {
            "decision":
                "REVISION_MANUAL_TIPO",

            "motivo":
                (
                    "Tipo documental ambiguo: "
                    f"{tipo_original}. "
                    "Debe verificarse si corresponde "
                    "a un trabajo completo de congreso "
                    "o a otro tipo de publicación."
                ),

            "criterio":
                "TIPO_ZOTERO_AMBIGUO"
        }

    # ------------------------------------------------------
    # TIPO NO PREVISTO
    # ------------------------------------------------------

    return {
        "decision":
            "REVISION_MANUAL_TIPO",

        "motivo":
            (
                "Tipo documental no contemplado "
                "explícitamente por el script: "
                f"{tipo_original}."
            ),

        "criterio":
            "TIPO_NO_PREVISTO"
    }


# ==========================================================
# GENERACIÓN DE FILA DE RESULTADO
# ==========================================================

COLUMNAS = [
    "tfm_id",
    "titulo",
    "anio",
    "doi",
    "tipo_documental_zotero",
    "criterio_decision",
    "decision",
    "motivo",
    "extracto_abstract",
    "tipo_confirmado_manual",
    "decision_manual",
    "observaciones_manual",
]


def generar_fila(elemento):
    """
    Genera una fila para los informes CSV.
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

        "tipo_documental_zotero":
            obtener_tipo_documental(
                elemento
            ),

        "criterio_decision":
            resultado[
                "criterio"
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

        "tipo_confirmado_manual":
            "",

        "decision_manual":
            "",

        "observaciones_manual":
            "",
    }


# ==========================================================
# ESCRITURA CSV
# ==========================================================

def escribir_csv(
    filas,
    ruta
):
    """
    Genera un CSV UTF-8 compatible con Excel.
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
# DISTRIBUCIÓN DE TIPOS
# ==========================================================

def escribir_distribucion(
    elementos,
    ruta
):
    """
    Genera un CSV con el número de registros de
    cada tipo Zotero encontrado.
    """

    contador = Counter(
        obtener_tipo_documental(
            elemento
        )
        for elemento in elementos
    )

    with ruta.open(
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as archivo:

        escritor = csv.writer(
            archivo
        )

        escritor.writerow([
            "tipo_documental_zotero",
            "numero_registros"
        ])

        for tipo, numero in sorted(
            contador.items(),
            key=lambda elemento:
                (-elemento[1], elemento[0])
        ):

            escritor.writerow([
                tipo,
                numero
            ])


# ==========================================================
# PROCESO PRINCIPAL
# ==========================================================

def principal():

    print()
    print(
        "CRIBADO POR TIPO DOCUMENTAL - ZOTERO RDF"
    )
    print("=" * 70)

    if not ARCHIVO_RDF_ENTRADA.exists():

        print(
            "ERROR: No se encuentra el fichero:"
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
            "El RDF no contiene el número esperado "
            "de referencias. "
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
        identificador
        for identificador in identificadores
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
        f"TFM-ID válidos y únicos: "
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

    filas_elegibles = [
        fila
        for fila in filas
        if fila["decision"]
        == "INCLUIR_TIPO_DOCUMENTAL"
    ]

    filas_excluidas = [
        fila
        for fila in filas
        if fila["decision"]
        == "EXCLUIR_TIPO_DOCUMENTAL"
    ]

    filas_revision = [
        fila
        for fila in filas
        if fila["decision"]
        == "REVISION_MANUAL_TIPO"
    ]

    # ------------------------------------------------------
    # ESCRITURA
    # ------------------------------------------------------

    escribir_csv(
        filas,
        ARCHIVO_RESULTADOS
    )

    escribir_csv(
        filas_elegibles,
        ARCHIVO_ELEGIBLES
    )

    escribir_csv(
        filas_excluidas,
        ARCHIVO_EXCLUIDOS
    )

    escribir_csv(
        filas_revision,
        ARCHIVO_REVISION_MANUAL
    )

    escribir_distribucion(
        elementos,
        ARCHIVO_DISTRIBUCION
    )

    # ------------------------------------------------------
    # DISTRIBUCIÓN
    # ------------------------------------------------------

    contador_tipos = Counter(
        obtener_tipo_documental(
            elemento
        )
        for elemento in elementos
    )

    lineas_tipos = []

    for tipo, numero in sorted(
        contador_tipos.items(),
        key=lambda elemento:
            (-elemento[1], elemento[0])
    ):

        lineas_tipos.append(
            f"  {tipo}: {numero}"
        )

    texto_tipos = "\n".join(
        lineas_tipos
    )

    # ------------------------------------------------------
    # RESUMEN
    # ------------------------------------------------------

    resumen = (
        "CRIBADO POR TIPO DOCUMENTAL\n"
        "====================================\n\n"

        f"Registros analizados: "
        f"{len(elementos)}\n\n"

        f"Tipo documental elegible: "
        f"{len(filas_elegibles)}\n"

        f"Tipo documental no elegible: "
        f"{len(filas_excluidas)}\n"

        f"Pendientes de revisión manual: "
        f"{len(filas_revision)}\n\n"

        "Distribución de tipos Zotero:\n"
        f"{texto_tipos}\n"
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
        ARCHIVO_ELEGIBLES
    )

    print(
        ARCHIVO_EXCLUIDOS
    )

    print(
        ARCHIVO_REVISION_MANUAL
    )

    print(
        ARCHIVO_DISTRIBUCION
    )

    print(
        ARCHIVO_RESUMEN
    )


if __name__ == "__main__":
    principal()