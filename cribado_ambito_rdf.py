#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Cribado por ámbito de estudio a partir de Zotero RDF
Revisión sistemática PRISMA / PRISMA-S

Objetivo:
Comprobar que las publicaciones pertenecen al ámbito
de Computer Science / Engineering y detectar trabajos
de ciencias forenses no digitales.

Funciones principales:
1. Lee la colección pendiente de cribado exportada
   desde Zotero en formato RDF.
2. Ignora adjuntos y notas.
3. Recupera el TFM-ID del campo Adicional.
4. Analiza:
   - título;
   - abstract;
   - palabras clave.
5. Busca indicadores de:
   - análisis forense digital y ciberseguridad;
   - Computer Science / Engineering;
   - ciencias forenses no digitales.
6. Clasifica los registros como:
   - INCLUIR_AMBITO;
   - EXCLUIR_AMBITO;
   - REVISION_MANUAL_AMBITO.
7. Solo excluye automáticamente los casos
   inequívocamente pertenecientes a ámbitos
   forenses no digitales.
8. Genera ficheros CSV separados y un resumen.

Criterio metodológico:
La ausencia de términos tecnológicos no constituye
por sí misma un motivo de exclusión.

Los casos ambiguos se someten a revisión manual
para evitar falsos negativos.
"""

from pathlib import Path
import csv
import re
import html
import unicodedata
import xml.etree.ElementTree as ET


# ==========================================================
# CONFIGURACIÓN
# ==========================================================

ARCHIVO_RDF_ENTRADA = Path(
    "TFM_PENDIENTES_CRIBA_5440.rdf"
)

DIRECTORIO_SALIDA = Path(
    "cribado_ambito"
)

ARCHIVO_RESULTADOS = (
    DIRECTORIO_SALIDA
    / "TFM_cribado_ambito_resultados.csv"
)

ARCHIVO_INCLUIDOS = (
    DIRECTORIO_SALIDA
    / "TFM_cribado_ambito_incluidos.csv"
)

ARCHIVO_EXCLUIDOS = (
    DIRECTORIO_SALIDA
    / "TFM_cribado_ambito_excluidos.csv"
)

ARCHIVO_REVISION_MANUAL = (
    DIRECTORIO_SALIDA
    / "TFM_cribado_ambito_revision_manual.csv"
)

ARCHIVO_RESUMEN = (
    DIRECTORIO_SALIDA
    / "TFM_cribado_ambito_resumen.txt"
)

NUMERO_ESPERADO_REGISTROS = 5440


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
# INDICADORES DE ÁMBITO DIGITAL / TECNOLÓGICO
# ==========================================================

PATRONES_DIGITALES_FUERTES = [
    (r"\bdigital forensic", "digital forensics"),
    (r"\bdigital evidence\b", "digital evidence"),
    (r"\bdigital investigation", "digital investigation"),
    (r"\bcomputer forensic", "computer forensics"),
    (r"\bcyber forensic", "cyber forensics"),
    (r"\bnetwork forensic", "network forensics"),
    (r"\bmemory forensic", "memory forensics"),
    (r"\bmobile forensic", "mobile forensics"),
    (r"\bcloud forensic", "cloud forensics"),
    (r"\biot forensic", "IoT forensics"),
    (r"\bblockchain forensic", "blockchain forensics"),
    (r"\bmultimedia forensic", "multimedia forensics"),
    (r"\bimage forensic", "image forensics"),
    (r"\bvideo forensic", "video forensics"),
    (r"\baudio forensic", "audio forensics"),
    (r"\bcybersecurity\b", "cybersecurity"),
    (r"\bcyber security\b", "cybersecurity"),
    (r"\bcybercrime\b", "cybercrime"),
    (r"\bcyber crime\b", "cybercrime"),
    (r"\bmalware\b", "malware"),
    (r"\bransomware\b", "ransomware"),
    (r"\bphishing\b", "phishing"),
    (r"\bdeepfake", "deepfake"),
    (r"\bsteganalysis\b", "steganalysis"),
    (r"\bsteganograph", "steganography"),
    (r"\bfile system\b", "file system"),
    (r"\bdisk image\b", "disk image"),
    (r"\bmemory dump\b", "memory dump"),
    (r"\bincident response\b", "incident response"),
    (r"\bintrusion detection\b", "intrusion detection"),
    (r"\bnetwork traffic\b", "network traffic"),
    (r"\blog analysis\b", "log analysis"),
    (r"\bdigital artifact", "digital artifacts"),
    (r"\belectronic evidence\b", "electronic evidence"),
]


# ==========================================================
# INDICADORES COMPLEMENTARIOS DE COMPUTER SCIENCE /
# ENGINEERING
# ==========================================================

PATRONES_TECNOLOGICOS = [
    (r"\bartificial intelligence\b", "artificial intelligence"),
    (r"\bmachine learning\b", "machine learning"),
    (r"\bdeep learning\b", "deep learning"),
    (r"\bneural network", "neural networks"),
    (r"\blarge language model", "large language models"),
    (r"\bllm\b", "LLM"),
    (r"\bcomputer vision\b", "computer vision"),
    (r"\bnatural language processing\b", "NLP"),
    (r"\bsoftware\b", "software"),
    (r"\balgorithm", "algorithm"),
    (r"\bdatabase", "database"),
    (r"\bcomputer network", "computer networks"),
    (r"\binternet of things\b", "Internet of Things"),
    (r"\biot\b", "IoT"),
    (r"\bblockchain\b", "blockchain"),
    (r"\bcloud computing\b", "cloud computing"),
    (r"\bcryptograph", "cryptography"),
    (r"\bcomputer system", "computer systems"),
    (r"\binformation security\b", "information security"),
    (r"\bdata mining\b", "data mining"),
    (r"\bdata science\b", "data science"),
    (r"\bclassification\b", "classification"),
    (r"\banomaly detection\b", "anomaly detection"),
]


# ==========================================================
# CIENCIAS FORENSES NO DIGITALES INEQUÍVOCAS
# ==========================================================

PATRONES_FORENSES_NO_DIGITALES = [
    (r"\bforensic medicine\b", "forensic medicine"),
    (r"\bforensic pathology\b", "forensic pathology"),
    (r"\bforensic anthropology\b", "forensic anthropology"),
    (r"\bforensic odontology\b", "forensic odontology"),
    (r"\bforensic dentistry\b", "forensic dentistry"),
    (r"\bforensic toxicology\b", "forensic toxicology"),
    (r"\bforensic genetics\b", "forensic genetics"),
    (r"\bforensic genomics\b", "forensic genomics"),
    (r"\bforensic entomology\b", "forensic entomology"),
    (r"\bforensic archaeology\b", "forensic archaeology"),
    (r"\bforensic osteology\b", "forensic osteology"),
    (r"\bforensic radiology\b", "forensic radiology"),
    (r"\bforensic psychiatry\b", "forensic psychiatry"),
    (r"\bforensic psychology\b", "forensic psychology"),
    (r"\bforensic nursing\b", "forensic nursing"),
]


# ==========================================================
# INDICADORES BIOMÉDICOS COMPLEMENTARIOS
# ==========================================================

PATRONES_BIOMEDICOS = [
    (r"\bautopsy\b", "autopsy"),
    (r"\bpostmortem\b", "postmortem"),
    (r"\bpost-mortem\b", "post-mortem"),
    (r"\bcadaver", "cadaver"),
    (r"\bskeletal remains\b", "skeletal remains"),
    (r"\bbone age\b", "bone age"),
    (r"\bcause of death\b", "cause of death"),
    (r"\btoxicology\b", "toxicology"),
    (r"\bdna profiling\b", "DNA profiling"),
    (r"\bdna analysis\b", "DNA analysis"),
    (r"\bgenetic profile\b", "genetic profile"),
    (r"\bmetabolomics\b", "metabolomics"),
    (r"\bproteomics\b", "proteomics"),
    (r"\bhistopatholog", "histopathology"),
    (r"\bdental\b", "dental"),
    (r"\bcraniofacial\b", "craniofacial"),
    (r"\bbloodstain\b", "bloodstain"),
    (r"\bblood stain\b", "blood stain"),
    (r"\bpostmortem interval\b", "postmortem interval"),
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


def normalizar_texto(texto):
    """
    Normaliza texto para facilitar la detección
    de patrones.
    """

    texto = limpiar_texto(
        texto
    )

    texto = unicodedata.normalize(
        "NFKD",
        texto.lower()
    )

    texto = "".join(
        caracter
        for caracter in texto
        if not unicodedata.combining(
            caracter
        )
    )

    return texto


def texto_elemento(elemento):
    """
    Obtiene el texto completo de un nodo XML.
    """

    if elemento is None:
        return ""

    return limpiar_texto(
        "".join(
            elemento.itertext()
        )
    )


# ==========================================================
# IDENTIFICACIÓN TFM
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
    Recupera fecha o año.
    """

    return texto_elemento(
        elemento.find(
            "dc:date",
            ESPACIOS_NOMBRES
        )
    )


def obtener_tipo_documental(elemento):
    """
    Recupera el tipo Zotero.
    """

    return texto_elemento(
        elemento.find(
            "z:itemType",
            ESPACIOS_NOMBRES
        )
    )


def obtener_palabras_clave(elemento):
    """
    Recupera los términos almacenados como
    dc:subject en Zotero RDF.
    """

    palabras = []

    for sujeto in elemento.findall(
        "dc:subject",
        ESPACIOS_NOMBRES
    ):

        valor = texto_elemento(
            sujeto
        )

        if (
            valor
            and valor not in palabras
        ):

            palabras.append(
                valor
            )

    return "; ".join(
        palabras
    )


def obtener_doi(elemento):
    """
    Recupera el DOI.
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
# ELEMENTOS BIBLIOGRÁFICOS
# ==========================================================

def es_elemento_bibliografico(elemento):
    """
    Excluye adjuntos y notas independientes.
    """

    tipo = obtener_tipo_documental(
        elemento
    )

    if not tipo:
        return False

    return (
        tipo.lower()
        not in {
            "attachment",
            "note"
        }
    )


# ==========================================================
# BÚSQUEDA DE INDICADORES
# ==========================================================

def buscar_indicadores(
    texto,
    patrones
):
    """
    Busca indicadores en el texto y devuelve
    las etiquetas encontradas sin duplicados.
    """

    encontrados = []

    for patron, etiqueta in patrones:

        if re.search(
            patron,
            texto,
            flags=re.IGNORECASE
        ):

            if etiqueta not in encontrados:

                encontrados.append(
                    etiqueta
                )

    return encontrados


# ==========================================================
# CLASIFICACIÓN DEL ÁMBITO
# ==========================================================

def clasificar_registro(elemento):
    """
    Clasifica el registro según su ámbito científico.

    Criterio conservador:
    - La ausencia de indicadores tecnológicos NO constituye
      motivo de exclusión.
    - Solo se envían a revisión manual los registros que
      presentan indicadores de ciencias forenses no digitales
      o de ámbitos biomédicos.
    - No se realizan exclusiones automáticas por ámbito.
    """

    titulo = obtener_titulo(
        elemento
    )

    abstract = obtener_abstract(
        elemento
    )

    palabras_clave = obtener_palabras_clave(
        elemento
    )

    texto = normalizar_texto(
        f"{titulo}. "
        f"{abstract}. "
        f"{palabras_clave}"
    )

    digitales = buscar_indicadores(
        texto,
        PATRONES_DIGITALES_FUERTES
    )

    tecnologicos = buscar_indicadores(
        texto,
        PATRONES_TECNOLOGICOS
    )

    forenses_no_digitales = (
        buscar_indicadores(
            texto,
            PATRONES_FORENSES_NO_DIGITALES
        )
    )

    biomedicos = buscar_indicadores(
        texto,
        PATRONES_BIOMEDICOS
    )

    # ------------------------------------------------------
    # POSIBLE ÁMBITO FORENSE NO DIGITAL / BIOMÉDICO
    # ------------------------------------------------------

    if (
        forenses_no_digitales
        or biomedicos
    ):

        return {
            "decision":
                "REVISION_MANUAL_AMBITO",

            "motivo":
                (
                    "Se han identificado indicadores "
                    "de ciencias forenses no digitales "
                    "o de un posible ámbito biomédico. "
                    "Se requiere revisión manual para "
                    "determinar si la contribución "
                    "pertenece realmente al ámbito "
                    "de la revisión."
                ),

            "digitales":
                digitales,

            "tecnologicos":
                tecnologicos,

            "forenses_no_digitales":
                forenses_no_digitales,

            "biomedicos":
                biomedicos,
        }

    # ------------------------------------------------------
    # RESTO DE REGISTROS
    # ------------------------------------------------------

    return {
        "decision":
            "INCLUIR_AMBITO",

        "motivo":
            (
                "No se han identificado indicadores "
                "de ciencias forenses no digitales "
                "ni de ámbitos biomédicos. "
                "El registro continúa a la siguiente "
                "fase de cribado."
            ),

        "digitales":
            digitales,

        "tecnologicos":
            tecnologicos,

        "forenses_no_digitales":
            forenses_no_digitales,

        "biomedicos":
            biomedicos,
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
    "indicadores_digitales",
    "indicadores_tecnologicos",
    "indicadores_forenses_no_digitales",
    "indicadores_biomedicos",
    "decision",
    "motivo",
    "extracto_abstract",
    "ambito_confirmado_manual",
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

        "tipo_documental":
            obtener_tipo_documental(
                elemento
            ),

        "indicadores_digitales":
            "; ".join(
                resultado[
                    "digitales"
                ]
            ),

        "indicadores_tecnologicos":
            "; ".join(
                resultado[
                    "tecnologicos"
                ]
            ),

        "indicadores_forenses_no_digitales":
            "; ".join(
                resultado[
                    "forenses_no_digitales"
                ]
            ),

        "indicadores_biomedicos":
            "; ".join(
                resultado[
                    "biomedicos"
                ]
            ),

        "decision":
            resultado[
                "decision"
            ],

        "motivo":
            resultado[
                "motivo"
            ],

        "extracto_abstract":
            abstract[:700],

        "ambito_confirmado_manual":
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
    Escribe un CSV compatible con Excel en Windows.
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
        "CRIBADO POR ÁMBITO - ZOTERO RDF"
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
        identificador
        for identificador
        in identificadores
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

    filas_incluidas = [
        fila
        for fila in filas
        if fila["decision"]
        == "INCLUIR_AMBITO"
    ]

    filas_excluidas = [
        fila
        for fila in filas
        if fila["decision"]
        == "EXCLUIR_AMBITO"
    ]

    filas_revision = [
        fila
        for fila in filas
        if fila["decision"]
        == "REVISION_MANUAL_AMBITO"
    ]

    # ------------------------------------------------------
    # ESCRITURA
    # ------------------------------------------------------

    escribir_csv(
        filas,
        ARCHIVO_RESULTADOS
    )

    escribir_csv(
        filas_incluidas,
        ARCHIVO_INCLUIDOS
    )

    escribir_csv(
        filas_excluidas,
        ARCHIVO_EXCLUIDOS
    )

    escribir_csv(
        filas_revision,
        ARCHIVO_REVISION_MANUAL
    )

    # ------------------------------------------------------
    # RESUMEN
    # ------------------------------------------------------

    resumen = (
        "CRIBADO POR ÁMBITO\n"
        "====================================\n\n"

        f"Registros analizados: "
        f"{len(elementos)}\n\n"

        f"Ámbito compatible automáticamente: "
        f"{len(filas_incluidas)}\n"

        f"Ámbito no elegible automáticamente: "
        f"{len(filas_excluidas)}\n"

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
        ARCHIVO_INCLUIDOS
    )

    print(
        ARCHIVO_EXCLUIDOS
    )

    print(
        ARCHIVO_REVISION_MANUAL
    )

    print(
        ARCHIVO_RESUMEN
    )


if __name__ == "__main__":
    principal()