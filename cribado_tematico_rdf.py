#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Cribado temático estricto - E05
Revisión sistemática PRISMA / PRISMA-S

Objetivo:
Seleccionar únicamente aquellas publicaciones en las que
la inteligencia artificial se aplica de forma sustancial
a una tarea concreta del análisis forense digital sobre
evidencia o artefactos digitales.

Para continuar automáticamente, el registro debe cumplir
simultáneamente cuatro requisitos:

1. IA central en la contribución.
2. Análisis forense digital central.
3. Existencia de evidencia o artefactos digitales
   como objeto de análisis.
4. Automatización o asistencia mediante IA de una
   tarea concreta del proceso forense.

Resultados posibles:
- INCLUIR_E05
- EXCLUIR_E05
- REVISION_MANUAL_E05

Principio metodológico:
La exclusión automática solo se realiza cuando existe
suficiente información bibliográfica para determinar
con claridad que no se cumplen los requisitos.

Los casos ambiguos se someten a revisión manual.
"""

from pathlib import Path
from collections import Counter
import csv
import re
import html
import unicodedata
import xml.etree.ElementTree as ET


# ==========================================================
# CONFIGURACIÓN
# ==========================================================

ARCHIVO_RDF_ENTRADA = Path(
    "TFM_PENDIENTES_CRIBA_5332.rdf"
)

DIRECTORIO_SALIDA = Path(
    "cribado_tematico_estricto"
)

ARCHIVO_RESULTADOS = (
    DIRECTORIO_SALIDA
    / "TFM_E05_resultados.csv"
)

ARCHIVO_INCLUIDOS = (
    DIRECTORIO_SALIDA
    / "TFM_E05_incluidos.csv"
)

ARCHIVO_EXCLUIDOS = (
    DIRECTORIO_SALIDA
    / "TFM_E05_excluidos.csv"
)

ARCHIVO_REVISION_MANUAL = (
    DIRECTORIO_SALIDA
    / "TFM_E05_revision_manual.csv"
)

ARCHIVO_RESUMEN = (
    DIRECTORIO_SALIDA
    / "TFM_E05_resumen.txt"
)

NUMERO_ESPERADO_REGISTROS = 5332


# ==========================================================
# PESOS DE LOS CAMPOS
# ==========================================================

PESO_TITULO = 5
PESO_PALABRAS_CLAVE = 4
PESO_ABSTRACT = 2


# ==========================================================
# UMBRALES
# ==========================================================

# IA y ámbito forense deben tener una presencia sustancial.
UMBRAL_CENTRAL = 5

# Evidencia y automatización pueden estar descritas
# principalmente en el abstract.
UMBRAL_EVIDENCIA = 2
UMBRAL_AUTOMATIZACION = 2

# Se exige un mínimo de información textual para
# permitir determinadas exclusiones automáticas.
NUMERO_MINIMO_PALABRAS_EXCLUSION = 100


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
# INDICADORES DE INTELIGENCIA ARTIFICIAL
# ==========================================================

PATRONES_IA = [

    # Conceptos generales
    (r"\bartificial intelligence\b", "artificial intelligence"),
    (r"\bmachine learning\b", "machine learning"),
    (r"\bdeep learning\b", "deep learning"),
    (r"\bcomputational intelligence\b", "computational intelligence"),

    # Redes neuronales
    (r"\bneural network", "neural networks"),
    (r"\bdeep neural network", "deep neural networks"),
    (r"\bconvolutional neural network", "CNN"),
    (r"\bcnn\b", "CNN"),
    (r"\brecurrent neural network", "RNN"),
    (r"\brnn\b", "RNN"),
    (r"\blstm\b", "LSTM"),
    (r"\bgru\b", "GRU"),
    (r"\bgraph neural network", "GNN"),
    (r"\bgnn\b", "GNN"),

    # Transformers / attention
    (r"\btransformer", "transformers"),
    (r"\bvision transformer", "Vision Transformer"),
    (r"\bvit\b", "ViT"),
    (r"\bself[- ]attention\b", "self-attention"),
    (r"\battention mechanism", "attention"),

    # Generativos
    (r"\bgenerative ai\b", "generative AI"),
    (r"\bgenerative artificial intelligence\b", "generative AI"),
    (r"\bgenerative adversarial network", "GAN"),
    (r"\bgans?\b", "GAN"),
    (r"\bdiffusion model", "diffusion model"),
    (r"\bautoencoder", "autoencoder"),
    (r"\bvariational autoencoder", "VAE"),
    (r"\bvae\b", "VAE"),

    # LLM / LMM / RAG / agentes
    (r"\blarge language model", "LLM"),
    (r"\bllms?\b", "LLM"),
    (r"\blarge multimodal model", "LMM"),
    (r"\blmms?\b", "LMM"),
    (r"\bretrieval[- ]augmented generation\b", "RAG"),
    (r"\brag\b", "RAG"),
    (r"\bai agent", "AI agents"),
    (r"\bagentic ai\b", "agentic AI"),

    # Modelos conocidos
    (r"\bbert\b", "BERT"),
    (r"\broberta\b", "RoBERTa"),
    (r"\bgpt[- ]?[2345]?\b", "GPT"),
    (r"\byolo\b", "YOLO"),
    (r"\bresnet\b", "ResNet"),
    (r"\befficientnet\b", "EfficientNet"),
    (r"\bmobilenet\b", "MobileNet"),
    (r"\bu[- ]net\b", "U-Net"),

    # Paradigmas
    (r"\btransfer learning\b", "transfer learning"),
    (r"\bself[- ]supervised learning\b", "self-supervised learning"),
    (r"\bsemi[- ]supervised learning\b", "semi-supervised learning"),
    (r"\bsupervised learning\b", "supervised learning"),
    (r"\bunsupervised learning\b", "unsupervised learning"),
    (r"\breinforcement learning\b", "reinforcement learning"),
    (r"\bcontrastive learning\b", "contrastive learning"),
    (r"\brepresentation learning\b", "representation learning"),
    (r"\bfew[- ]shot learning\b", "few-shot learning"),
    (r"\bzero[- ]shot learning\b", "zero-shot learning"),
    (r"\bfederated learning\b", "federated learning"),
    (r"\bmultimodal learning\b", "multimodal learning"),

    # ML clásico
    (r"\brandom forest", "random forest"),
    (r"\bsupport vector machine", "SVM"),
    (r"\bsvm\b", "SVM"),
    (r"\bxgboost\b", "XGBoost"),
    (r"\bgradient boosting\b", "gradient boosting"),
    (r"\bdecision tree", "decision trees"),
    (r"\bk[- ]?nearest neighbou?r", "KNN"),
    (r"\bknn\b", "KNN"),
    (r"\bk[- ]?means\b", "k-means"),
    (r"\bnaive bayes\b", "Naive Bayes"),
    (r"\bclustering\b", "clustering"),

    # XAI
    (r"\bexplainable artificial intelligence\b", "XAI"),
    (r"\bexplainable ai\b", "XAI"),
    (r"\bxai\b", "XAI"),
    (r"\binterpretable machine learning\b", "interpretable ML"),
    (r"\bshap\b", "SHAP"),
    (r"\blime\b", "LIME"),

    # Otras áreas
    (r"\bnatural language processing\b", "NLP"),
    (r"\bnlp\b", "NLP"),
    (r"\bcomputer vision\b", "computer vision"),
]


# ==========================================================
# INDICADORES DE ANÁLISIS FORENSE DIGITAL
# ==========================================================

PATRONES_FORENSES = [

    # Generales
    (r"\bdigital forensic", "digital forensics"),
    (r"\bdigital evidence\b", "digital evidence"),
    (r"\bdigital investigation", "digital investigation"),
    (r"\bcomputer forensic", "computer forensics"),
    (r"\bcyber forensic", "cyber forensics"),
    (r"\belectronic evidence\b", "electronic evidence"),

    # Proceso forense
    (r"\bforensic investigation\b", "forensic investigation"),
    (r"\bforensic examination\b", "forensic examination"),
    (r"\bforensic analysis\b", "forensic analysis"),
    (r"\bforensic triage\b", "forensic triage"),
    (r"\bforensic readiness\b", "forensic readiness"),
    (r"\bforensic[- ]ready\b", "forensic-ready"),
    (r"\bforensic timeline\b", "forensic timeline"),
    (r"\bevent reconstruction\b", "event reconstruction"),
    (r"\bincident reconstruction\b", "incident reconstruction"),
    (r"\bchain of custody\b", "chain of custody"),

    # Subdominios
    (r"\bnetwork forensic", "network forensics"),
    (r"\bmemory forensic", "memory forensics"),
    (r"\bmobile forensic", "mobile forensics"),
    (r"\bcloud forensic", "cloud forensics"),
    (r"\biot forensic", "IoT forensics"),
    (r"\bblockchain forensic", "blockchain forensics"),
    (r"\bmultimedia forensic", "multimedia forensics"),
    (r"\bmedia forensic", "media forensics"),
    (r"\bimage forensic", "image forensics"),
    (r"\bvideo forensic", "video forensics"),
    (r"\baudio forensic", "audio forensics"),
    (r"\bmalware forensic", "malware forensics"),
    (r"\bdrone forensic", "drone forensics"),
    (r"\bandroid forensic", "Android forensics"),
    (r"\bios forensic", "iOS forensics"),

    # Anti-forensics
    (r"\banti[- ]forensic", "anti-forensics"),

    # Manipulación/autenticidad
    (r"\bimage forgery\b", "image forgery"),
    (r"\bforgery detection\b", "forgery detection"),
    (r"\bforgery localization\b", "forgery localization"),
    (r"\bimage manipulation\b", "image manipulation"),
    (r"\bimage tampering\b", "image tampering"),
    (r"\btamper detection\b", "tamper detection"),
    (r"\btamper localization\b", "tamper localization"),
    (r"\bdigital authenticity\b", "digital authenticity"),
    (r"\bmedia authenticity\b", "media authenticity"),
    (r"\bsource camera identification\b", "source camera identification"),
    (r"\bcamera source identification\b", "camera source identification"),

    # Deepfake / contenido sintético
    (r"\bdeepfake\b", "deepfake"),
    (r"\bdeep fake\b", "deepfake"),
    (r"\bsynthetic media\b", "synthetic media"),
    (r"\bvoice cloning\b", "voice cloning"),
    (r"\baudio spoofing\b", "audio spoofing"),

    # Esteganografía
    (r"\bsteganalysis\b", "steganalysis"),
    (r"\bsteganograph", "steganography"),
]


# ==========================================================
# EVIDENCIA / ARTEFACTOS DIGITALES
# ==========================================================

PATRONES_EVIDENCIA_DIGITAL = [

    # Concepto general
    (r"\bdigital evidence\b", "digital evidence"),
    (r"\belectronic evidence\b", "electronic evidence"),
    (r"\bdigital artifact", "digital artifacts"),
    (r"\bdigital artefact", "digital artefacts"),

    # Archivos / almacenamiento
    (r"\bfile system\b", "file system"),
    (r"\bfilesystem\b", "file system"),
    (r"\bfile carving\b", "file carving"),
    (r"\bdata carving\b", "data carving"),
    (r"\bdeleted file", "deleted files"),
    (r"\bdeleted data\b", "deleted data"),
    (r"\bdisk image\b", "disk image"),
    (r"\bstorage device", "storage devices"),

    # Memoria
    (r"\bmemory dump\b", "memory dump"),
    (r"\bmemory image\b", "memory image"),
    (r"\bvolatile memory\b", "volatile memory"),
    (r"\bram dump\b", "RAM dump"),

    # Sistemas
    (r"\bwindows registry\b", "Windows Registry"),
    (r"\bregistry artifact", "registry artifacts"),
    (r"\bsystem log", "system logs"),
    (r"\bevent log", "event logs"),
    (r"\blog file", "log files"),

    # Redes
    (r"\bnetwork traffic\b", "network traffic"),
    (r"\bpacket capture\b", "packet capture"),
    (r"\bnetwork packet", "network packets"),
    (r"\bpcap\b", "PCAP"),

    # Móvil
    (r"\bmobile device", "mobile devices"),
    (r"\bsmartphone\b", "smartphones"),
    (r"\bandroid\b", "Android"),
    (r"\bios\b", "iOS"),
    (r"\bwhatsapp\b", "WhatsApp"),
    (r"\btext message", "text messages"),

    # Cloud / IoT
    (r"\bcloud log", "cloud logs"),
    (r"\bcloud artifact", "cloud artifacts"),
    (r"\biot device", "IoT devices"),
    (r"\biot log", "IoT logs"),

    # Malware
    (r"\bmalware sample", "malware samples"),
    (r"\bmalicious file", "malicious files"),

    # Multimedia
    (r"\bdigital image", "digital images"),
    (r"\bdigital video", "digital video"),
    (r"\bdigital audio", "digital audio"),
    (r"\bimage file", "image files"),
    (r"\bvideo file", "video files"),
    (r"\baudio file", "audio files"),
    (r"\bmetadata\b", "metadata"),
    (r"\bexif\b", "EXIF"),
    (r"\bdeepfake\b", "deepfake content"),
    (r"\bsynthetic media\b", "synthetic media"),

    # Navegadores / comunicaciones
    (r"\bbrowser history\b", "browser history"),
    (r"\bweb history\b", "web history"),
    (r"\bemail message", "email messages"),
    (r"\bchat message", "chat messages"),

    # Evidencia específica
    (r"\bevidence acquisition\b", "evidence acquisition"),
    (r"\bevidence collection\b", "evidence collection"),
    (r"\bevidence preservation\b", "evidence preservation"),
    (r"\bevidence provenance\b", "evidence provenance"),
]


# ==========================================================
# AUTOMATIZACIÓN / ASISTENCIA DEL PROCESO FORENSE
# ==========================================================

PATRONES_AUTOMATIZACION = [

    # Detección
    (r"\bdetection\b", "detection"),
    (r"\bdetecting\b", "detection"),
    (r"\bidentify\b", "identification"),
    (r"\bidentification\b", "identification"),

    # Clasificación
    (r"\bclassification\b", "classification"),
    (r"\bclassify\b", "classification"),
    (r"\bcategorization\b", "categorization"),

    # Extracción
    (r"\bextraction\b", "extraction"),
    (r"\bextracting\b", "extraction"),
    (r"\bartifact extraction\b", "artifact extraction"),

    # Filtrado / reducción
    (r"\bfiltering\b", "filtering"),
    (r"\btriage\b", "triage"),
    (r"\bprioriti[sz]", "prioritization"),
    (r"\branking\b", "ranking"),

    # Correlación / agrupación
    (r"\bcorrelation\b", "correlation"),
    (r"\bclustering\b", "clustering"),
    (r"\bgrouping\b", "grouping"),

    # Reconstrucción
    (r"\breconstruction\b", "reconstruction"),
    (r"\btimeline reconstruction\b", "timeline reconstruction"),

    # Recuperación
    (r"\brecovery\b", "recovery"),
    (r"\bdata recovery\b", "data recovery"),
    (r"\bfile recovery\b", "file recovery"),

    # Atribución
    (r"\battribution\b", "attribution"),
    (r"\bsource attribution\b", "source attribution"),
    (r"\bsource identification\b", "source identification"),

    # Autenticidad
    (r"\bauthentication\b", "authentication"),
    (r"\bverification\b", "verification"),
    (r"\bauthenticity\b", "authenticity verification"),

    # Localización / segmentación
    (r"\blocalization\b", "localization"),
    (r"\blocalisation\b", "localization"),
    (r"\bsegmentation\b", "segmentation"),

    # Análisis automatizado
    (r"\bautomated analysis\b", "automated analysis"),
    (r"\bautomatic analysis\b", "automatic analysis"),
    (r"\bautomated forensic", "forensic automation"),
    (r"\bautomatic forensic", "forensic automation"),
    (r"\bforensic automation\b", "forensic automation"),

    # Asistencia
    (r"\bdecision support\b", "decision support"),
    (r"\binvestigator support\b", "investigator support"),
    (r"\bforensic assistant\b", "forensic assistant"),
]


# ==========================================================
# DETECCIÓN DE REVISIONES PARA LA SIGUIENTE FASE
# ==========================================================

PATRONES_REVISION = [
    r"\bsystematic review\b",
    r"\bsystematic literature review\b",
    r"\bliterature review\b",
    r"\bscoping review\b",
    r"\bsurvey\b",
    r"\breview of\b",
    r"\bstate of the art\b",
]


# ==========================================================
# FUNCIONES AUXILIARES
# ==========================================================

def limpiar_texto(texto):
    """
    Elimina HTML y normaliza espacios.
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
    Normaliza el texto utilizado para el análisis.
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
    Obtiene el contenido textual de un elemento XML.
    """

    if elemento is None:
        return ""

    return limpiar_texto(
        "".join(
            elemento.itertext()
        )
    )


# ==========================================================
# TFM-ID
# ==========================================================

def obtener_tfm_id(elemento):
    """
    Recupera el TFM-ID almacenado en Adicional.
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
# METADATOS
# ==========================================================

def obtener_titulo(elemento):

    return texto_elemento(
        elemento.find(
            "dc:title",
            ESPACIOS_NOMBRES
        )
    )


def obtener_abstract(elemento):

    return texto_elemento(
        elemento.find(
            "dcterms:abstract",
            ESPACIOS_NOMBRES
        )
    )


def obtener_fecha(elemento):

    return texto_elemento(
        elemento.find(
            "dc:date",
            ESPACIOS_NOMBRES
        )
    )


def obtener_tipo_documental(elemento):

    return texto_elemento(
        elemento.find(
            "z:itemType",
            ESPACIOS_NOMBRES
        )
    )


def obtener_palabras_clave(elemento):

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

def buscar_patrones(
    texto,
    patrones
):

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
# PUNTUACIÓN
# ==========================================================

def calcular_puntuacion(
    titulo,
    abstract,
    palabras_clave,
    patrones
):

    indicadores_titulo = buscar_patrones(
        titulo,
        patrones
    )

    indicadores_palabras = buscar_patrones(
        palabras_clave,
        patrones
    )

    indicadores_abstract = buscar_patrones(
        abstract,
        patrones
    )

    puntuacion = (
        len(indicadores_titulo)
        * PESO_TITULO

        + len(indicadores_palabras)
        * PESO_PALABRAS_CLAVE

        + len(indicadores_abstract)
        * PESO_ABSTRACT
    )

    indicadores_totales = []

    for conjunto in (
        indicadores_titulo,
        indicadores_palabras,
        indicadores_abstract
    ):

        for indicador in conjunto:

            if indicador not in indicadores_totales:

                indicadores_totales.append(
                    indicador
                )

    return {
        "puntuacion":
            puntuacion,

        "titulo":
            indicadores_titulo,

        "palabras_clave":
            indicadores_palabras,

        "abstract":
            indicadores_abstract,

        "total":
            indicadores_totales,
    }


# ==========================================================
# CENTRALIDAD
# ==========================================================

def es_componente_central(
    resultado
):
    """
    Determina si IA o análisis forense digital
    constituyen un componente sustancial.

    Se considera central cuando:

    - alcanza el umbral y aparece en título
      o palabras clave;

    o

    - alcanza el umbral mediante al menos dos
      indicadores conceptuales diferentes.
    """

    if (
        resultado["puntuacion"]
        < UMBRAL_CENTRAL
    ):

        return False

    if (
        resultado["titulo"]
        or resultado["palabras_clave"]
    ):

        return True

    return (
        len(resultado["total"])
        >= 2
    )


# ==========================================================
# CUMPLIMIENTO DE EVIDENCIA / AUTOMATIZACIÓN
# ==========================================================

def cumple_evidencia(
    resultado
):
    """
    Comprueba si existe evidencia suficiente de que
    el objeto de análisis son artefactos digitales.
    """

    if (
        resultado["puntuacion"]
        < UMBRAL_EVIDENCIA
    ):

        return False

    if (
        resultado["titulo"]
        or resultado["palabras_clave"]
    ):

        return True

    return (
        len(resultado["total"])
        >= 1
    )


def cumple_automatizacion(
    resultado
):
    """
    Comprueba si se automatiza o asiste una tarea
    del proceso forense.
    """

    if (
        resultado["puntuacion"]
        < UMBRAL_AUTOMATIZACION
    ):

        return False

    if (
        resultado["titulo"]
        or resultado["palabras_clave"]
    ):

        return True

    return (
        len(resultado["total"])
        >= 1
    )


# ==========================================================
# DETECCIÓN DE REVISIÓN
# ==========================================================

def detectar_revision(
    titulo
):

    titulo_normalizado = normalizar_texto(
        titulo
    )

    for patron in PATRONES_REVISION:

        if re.search(
            patron,
            titulo_normalizado,
            flags=re.IGNORECASE
        ):

            return True

    return False


# ==========================================================
# CLASIFICACIÓN E05
# ==========================================================

def clasificar_registro(
    elemento
):

    titulo_original = obtener_titulo(
        elemento
    )

    abstract_original = obtener_abstract(
        elemento
    )

    palabras_originales = obtener_palabras_clave(
        elemento
    )

    titulo = normalizar_texto(
        titulo_original
    )

    abstract = normalizar_texto(
        abstract_original
    )

    palabras_clave = normalizar_texto(
        palabras_originales
    )

    texto_total = limpiar_texto(
        f"{titulo_original}. "
        f"{abstract_original}. "
        f"{palabras_originales}"
    )

    numero_palabras = len(
        texto_total.split()
    )

    # ------------------------------------------------------
    # ANÁLISIS DE LOS CUATRO COMPONENTES
    # ------------------------------------------------------

    resultado_ia = calcular_puntuacion(
        titulo,
        abstract,
        palabras_clave,
        PATRONES_IA
    )

    resultado_forense = calcular_puntuacion(
        titulo,
        abstract,
        palabras_clave,
        PATRONES_FORENSES
    )

    resultado_evidencia = calcular_puntuacion(
        titulo,
        abstract,
        palabras_clave,
        PATRONES_EVIDENCIA_DIGITAL
    )

    resultado_automatizacion = calcular_puntuacion(
        titulo,
        abstract,
        palabras_clave,
        PATRONES_AUTOMATIZACION
    )

    # ------------------------------------------------------
    # CUMPLIMIENTO
    # ------------------------------------------------------

    cumple_ia = es_componente_central(
        resultado_ia
    )

    cumple_forense = es_componente_central(
        resultado_forense
    )

    cumple_objeto_evidencia = cumple_evidencia(
        resultado_evidencia
    )

    cumple_tarea_automatizada = cumple_automatizacion(
        resultado_automatizacion
    )

    criterios = {
        "IA_CENTRAL":
            cumple_ia,

        "FORENSE_DIGITAL_CENTRAL":
            cumple_forense,

        "EVIDENCIA_DIGITAL":
            cumple_objeto_evidencia,

        "AUTOMATIZACION_FORENSE":
            cumple_tarea_automatizada,
    }

    numero_criterios = sum(
        1
        for valor in criterios.values()
        if valor
    )

    criterios_incumplidos = [
        nombre
        for nombre, valor
        in criterios.items()
        if not valor
    ]

    # ------------------------------------------------------
    # INCLUSIÓN E05
    # ------------------------------------------------------

    if numero_criterios == 4:

        return {
            "decision":
                "INCLUIR_E05",

            "motivo":
                (
                    "El registro cumple simultáneamente "
                    "los cuatro requisitos temáticos: "
                    "IA central, análisis forense digital, "
                    "evidencia digital y automatización "
                    "o asistencia de una tarea forense."
                ),

            "prioridad":
                "",

            "criterios":
                criterios,

            "criterios_incumplidos":
                criterios_incumplidos,

            "numero_criterios":
                numero_criterios,

            "ia":
                resultado_ia,

            "forense":
                resultado_forense,

            "evidencia":
                resultado_evidencia,

            "automatizacion":
                resultado_automatizacion,

            "numero_palabras":
                numero_palabras,
        }

    # ------------------------------------------------------
    # EXCLUSIONES CLARAS
    # ------------------------------------------------------

    if (
        numero_palabras
        >= NUMERO_MINIMO_PALABRAS_EXCLUSION
    ):

        # Sin IA
        if (
            resultado_ia["puntuacion"] == 0
        ):

            return {
                "decision":
                    "EXCLUIR_E05",

                "motivo":
                    (
                        "No se ha identificado una "
                        "aplicación de inteligencia "
                        "artificial en el método "
                        "o solución descrita."
                    ),

                "prioridad":
                    "",

                "criterios":
                    criterios,

                "criterios_incumplidos":
                    criterios_incumplidos,

                "numero_criterios":
                    numero_criterios,

                "ia":
                    resultado_ia,

                "forense":
                    resultado_forense,

                "evidencia":
                    resultado_evidencia,

                "automatizacion":
                    resultado_automatizacion,

                "numero_palabras":
                    numero_palabras,
            }

        # Sin componente forense digital
        if (
            resultado_forense["puntuacion"] == 0
            and
            not cumple_objeto_evidencia
        ):

            return {
                "decision":
                    "EXCLUIR_E05",

                "motivo":
                    (
                        "La publicación utiliza IA, "
                        "pero no presenta una relación "
                        "sustancial con análisis forense "
                        "digital ni con el tratamiento "
                        "de evidencia digital."
                    ),

                "prioridad":
                    "",

                "criterios":
                    criterios,

                "criterios_incumplidos":
                    criterios_incumplidos,

                "numero_criterios":
                    numero_criterios,

                "ia":
                    resultado_ia,

                "forense":
                    resultado_forense,

                "evidencia":
                    resultado_evidencia,

                "automatizacion":
                    resultado_automatizacion,

                "numero_palabras":
                    numero_palabras,
            }

        # No evidencia ni tarea forense automatizada
        if (
            resultado_evidencia["puntuacion"] == 0
            and
            resultado_automatizacion["puntuacion"] == 0
        ):

            return {
                "decision":
                    "EXCLUIR_E05",

                "motivo":
                    (
                        "No se ha identificado tratamiento "
                        "de evidencia digital ni una tarea "
                        "forense concreta automatizada "
                        "o asistida mediante IA."
                    ),

                "prioridad":
                    "",

                "criterios":
                    criterios,

                "criterios_incumplidos":
                    criterios_incumplidos,

                "numero_criterios":
                    numero_criterios,

                "ia":
                    resultado_ia,

                "forense":
                    resultado_forense,

                "evidencia":
                    resultado_evidencia,

                "automatizacion":
                    resultado_automatizacion,

                "numero_palabras":
                    numero_palabras,
            }

        # Cumple como máximo uno de los cuatro requisitos
        if numero_criterios <= 1:

            return {
                "decision":
                    "EXCLUIR_E05",

                "motivo":
                    (
                        "Con la información disponible "
                        "el trabajo cumple como máximo "
                        "uno de los cuatro requisitos "
                        "temáticos establecidos."
                    ),

                "prioridad":
                    "",

                "criterios":
                    criterios,

                "criterios_incumplidos":
                    criterios_incumplidos,

                "numero_criterios":
                    numero_criterios,

                "ia":
                    resultado_ia,

                "forense":
                    resultado_forense,

                "evidencia":
                    resultado_evidencia,

                "automatizacion":
                    resultado_automatizacion,

                "numero_palabras":
                    numero_palabras,
            }

    # ------------------------------------------------------
    # REVISIÓN MANUAL
    # ------------------------------------------------------

    if numero_criterios == 3:

        prioridad = "ALTA"

    elif numero_criterios == 2:

        prioridad = "MEDIA"

    else:

        prioridad = "BAJA"

    return {
        "decision":
            "REVISION_MANUAL_E05",

        "motivo":
            (
                "La información bibliográfica no permite "
                "confirmar automáticamente el cumplimiento "
                "de los cuatro requisitos temáticos."
            ),

        "prioridad":
            prioridad,

        "criterios":
            criterios,

        "criterios_incumplidos":
            criterios_incumplidos,

        "numero_criterios":
            numero_criterios,

        "ia":
            resultado_ia,

        "forense":
            resultado_forense,

        "evidencia":
            resultado_evidencia,

        "automatizacion":
            resultado_automatizacion,

        "numero_palabras":
            numero_palabras,
    }


# ==========================================================
# COLUMNAS DE SALIDA
# ==========================================================

COLUMNAS = [
    "tfm_id",
    "titulo",
    "anio",
    "doi",
    "tipo_documental",

    "puntuacion_ia",
    "puntuacion_forense",
    "puntuacion_evidencia",
    "puntuacion_automatizacion",

    "cumple_ia_central",
    "cumple_forense_digital",
    "cumple_evidencia_digital",
    "cumple_automatizacion_forense",

    "numero_criterios_cumplidos",
    "criterios_incumplidos",

    "indicadores_ia",
    "indicadores_forenses",
    "indicadores_evidencia",
    "indicadores_automatizacion",

    "numero_palabras_analizadas",

    "posible_revision_secundaria",

    "decision",
    "prioridad_revision",
    "motivo",

    "palabras_clave",
    "extracto_abstract",

    "decision_manual",
    "motivo_manual",
    "observaciones_manual",
]


# ==========================================================
# GENERACIÓN DE FILA
# ==========================================================

def generar_fila(
    elemento
):

    resultado = clasificar_registro(
        elemento
    )

    criterios = resultado[
        "criterios"
    ]

    titulo = obtener_titulo(
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
            titulo,

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

        "puntuacion_ia":
            resultado[
                "ia"
            ][
                "puntuacion"
            ],

        "puntuacion_forense":
            resultado[
                "forense"
            ][
                "puntuacion"
            ],

        "puntuacion_evidencia":
            resultado[
                "evidencia"
            ][
                "puntuacion"
            ],

        "puntuacion_automatizacion":
            resultado[
                "automatizacion"
            ][
                "puntuacion"
            ],

        "cumple_ia_central":
            criterios[
                "IA_CENTRAL"
            ],

        "cumple_forense_digital":
            criterios[
                "FORENSE_DIGITAL_CENTRAL"
            ],

        "cumple_evidencia_digital":
            criterios[
                "EVIDENCIA_DIGITAL"
            ],

        "cumple_automatizacion_forense":
            criterios[
                "AUTOMATIZACION_FORENSE"
            ],

        "numero_criterios_cumplidos":
            resultado[
                "numero_criterios"
            ],

        "criterios_incumplidos":
            "; ".join(
                resultado[
                    "criterios_incumplidos"
                ]
            ),

        "indicadores_ia":
            "; ".join(
                resultado[
                    "ia"
                ][
                    "total"
                ]
            ),

        "indicadores_forenses":
            "; ".join(
                resultado[
                    "forense"
                ][
                    "total"
                ]
            ),

        "indicadores_evidencia":
            "; ".join(
                resultado[
                    "evidencia"
                ][
                    "total"
                ]
            ),

        "indicadores_automatizacion":
            "; ".join(
                resultado[
                    "automatizacion"
                ][
                    "total"
                ]
            ),

        "numero_palabras_analizadas":
            resultado[
                "numero_palabras"
            ],

        "posible_revision_secundaria":
            detectar_revision(
                titulo
            ),

        "decision":
            resultado[
                "decision"
            ],

        "prioridad_revision":
            resultado[
                "prioridad"
            ],

        "motivo":
            resultado[
                "motivo"
            ],

        "palabras_clave":
            obtener_palabras_clave(
                elemento
            ),

        "extracto_abstract":
            abstract[:1500],

        "decision_manual":
            "",

        "motivo_manual":
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
        "E05 - CRIBADO TEMÁTICO ESTRICTO"
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
    # CONTROL DEL TFM-ID
    # ------------------------------------------------------

    identificadores = [
        obtener_tfm_id(
            elemento
        )
        for elemento in elementos
    ]

    if any(
        not identificador
        for identificador
        in identificadores
    ):

        raise ValueError(
            "Existen referencias sin TFM-ID."
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
        == "INCLUIR_E05"
    ]

    filas_excluidas = [
        fila
        for fila in filas
        if fila["decision"]
        == "EXCLUIR_E05"
    ]

    filas_revision = [
        fila
        for fila in filas
        if fila["decision"]
        == "REVISION_MANUAL_E05"
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
    # RESÚMENES
    # ------------------------------------------------------

    contador_criterios = Counter(
        fila[
            "numero_criterios_cumplidos"
        ]
        for fila in filas
    )

    contador_prioridades = Counter(
        fila[
            "prioridad_revision"
        ]
        for fila in filas_revision
    )

    revisiones_secundarias = sum(
        1
        for fila in filas
        if fila[
            "posible_revision_secundaria"
        ]
    )

    resumen = (
        "E05 - CRIBADO TEMÁTICO ESTRICTO\n"
        "========================================\n\n"

        f"Registros analizados: "
        f"{len(elementos)}\n\n"

        f"Incluidos automáticamente: "
        f"{len(filas_incluidas)}\n"

        f"Excluidos automáticamente: "
        f"{len(filas_excluidas)}\n"

        f"Pendientes de revisión manual: "
        f"{len(filas_revision)}\n\n"

        "Número de criterios cumplidos:\n"

        f"  4 criterios: "
        f"{contador_criterios.get(4, 0)}\n"

        f"  3 criterios: "
        f"{contador_criterios.get(3, 0)}\n"

        f"  2 criterios: "
        f"{contador_criterios.get(2, 0)}\n"

        f"  1 criterio: "
        f"{contador_criterios.get(1, 0)}\n"

        f"  0 criterios: "
        f"{contador_criterios.get(0, 0)}\n\n"

        "Prioridad de revisión manual:\n"

        f"  ALTA: "
        f"{contador_prioridades.get('ALTA', 0)}\n"

        f"  MEDIA: "
        f"{contador_prioridades.get('MEDIA', 0)}\n"

        f"  BAJA: "
        f"{contador_prioridades.get('BAJA', 0)}\n\n"

        f"Posibles revisiones/surveys detectados: "
        f"{revisiones_secundarias}\n"
    )

    ARCHIVO_RESUMEN.write_text(
        resumen,
        encoding="utf-8"
    )

    print()
    print(
        resumen
    )

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