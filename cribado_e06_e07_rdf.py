#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
E06 + E07 - Cribado corregido previo a texto completo
Revisión sistemática PRISMA / PRISMA-S

E06:
    Separación de literatura secundaria.

E07:
    Pertinencia temática-operativa estricta.

Objetivo:
Seleccionar publicaciones candidatas a evaluación
a texto completo cuando exista evidencia suficiente de:

1. IA central en la contribución.
2. Contexto de análisis forense digital.
3. Evidencia o artefactos digitales como objeto de análisis.
4. Automatización o asistencia de una tarea concreta:
   - detección;
   - identificación / atribución;
   - clasificación;
   - filtrado / triage;
   - priorización / ranking.

IMPORTANTE:
- No se exige que las métricas aparezcan en el abstract.
- No se exige que la evidencia digital aparezca en el título.
- No se utiliza la ausencia de métricas como exclusión.
- No se intenta obtener un número predeterminado de artículos.
- Las exclusiones automáticas se limitan a situaciones
  en las que la información bibliográfica disponible
  permite adoptar una decisión con alta confianza.
- Los casos ambiguos pasan a revisión manual.
"""

from pathlib import Path
from collections import Counter
import csv
import re
import html
import random
import unicodedata
import xml.etree.ElementTree as ET


# ==========================================================
# CONFIGURACIÓN
# ==========================================================

ARCHIVO_RDF_ENTRADA = Path(
    "TFM_PENDIENTES_CRIBA_5332.rdf"
)

DIRECTORIO_SALIDA = Path(
    "cribado_e06_e07_v2"
)

ARCHIVO_RESULTADOS = (
    DIRECTORIO_SALIDA
    / "TFM_E06_E07_resultados.csv"
)

ARCHIVO_CANDIDATOS = (
    DIRECTORIO_SALIDA
    / "TFM_E06_E07_candidatos_texto_completo.csv"
)

ARCHIVO_REVISION_MANUAL = (
    DIRECTORIO_SALIDA
    / "TFM_E06_E07_revision_manual.csv"
)

ARCHIVO_SECUNDARIA = (
    DIRECTORIO_SALIDA
    / "TFM_E06_literatura_secundaria.csv"
)

ARCHIVO_EXCLUIDOS = (
    DIRECTORIO_SALIDA
    / "TFM_E06_E07_excluidos.csv"
)

ARCHIVO_MUESTRA_CONTROL = (
    DIRECTORIO_SALIDA
    / "TFM_E06_E07_muestra_control_excluidos.csv"
)

ARCHIVO_RESUMEN = (
    DIRECTORIO_SALIDA
    / "TFM_E06_E07_resumen.txt"
)

NUMERO_ESPERADO_REGISTROS = 5332

# Para algunas exclusiones automáticas se exige
# disponer de una cantidad mínima de información.
MINIMO_PALABRAS_PARA_EXCLUIR = 80

# Muestra para comprobar falsos negativos.
TAMANO_MUESTRA_CONTROL = 50

# Semilla fija: la misma ejecución produce
# siempre la misma muestra de control.
SEMILLA_MUESTRA = 2026


# ==========================================================
# PESOS
# ==========================================================

PESO_TITULO = 5
PESO_PALABRAS_CLAVE = 4
PESO_ABSTRACT = 2


# ==========================================================
# UMBRALES
# ==========================================================

# Para que IA y contexto forense puedan considerarse
# centrales.
UMBRAL_CENTRAL = 5


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
# E06 - LITERATURA SECUNDARIA
# ==========================================================

# Solo expresiones suficientemente explícitas.
# No se utiliza "review" aislado.

PATRONES_LITERATURA_SECUNDARIA = [
    r"\bsystematic review\b",
    r"\bsystematic literature review\b",
    r"\bliterature review\b",
    r"\bscoping review\b",
    r"\bsystematic mapping(?: study)?\b",
    r"\bmapping study\b",
    r"\bbibliometric (?:analysis|review|study)\b",
    r"\bstate[- ]of[- ]the[- ]art review\b",
    r"\ba survey of\b",
    r"\ba survey on\b",
    r"\bsurvey of the\b",
    r"\bsurvey on the\b",
]


# ==========================================================
# IA
# ==========================================================

PATRONES_IA = [

    # ------------------------------------------------------
    # IA general
    # ------------------------------------------------------

    (r"\bartificial intelligence\b",
     "artificial intelligence"),

    (r"\bmachine learning\b",
     "machine learning"),

    (r"\bdeep learning\b",
     "deep learning"),

    (r"\bcomputational intelligence\b",
     "computational intelligence"),

    # ------------------------------------------------------
    # Redes neuronales
    # ------------------------------------------------------

    (r"\bneural network",
     "neural networks"),

    (r"\bdeep neural network",
     "deep neural networks"),

    (r"\bconvolutional neural network",
     "CNN"),

    (r"\bcnn\b",
     "CNN"),

    (r"\brecurrent neural network",
     "RNN"),

    (r"\brnn\b",
     "RNN"),

    (r"\blstm\b",
     "LSTM"),

    (r"\bgru\b",
     "GRU"),

    (r"\bgraph neural network",
     "GNN"),

    (r"\bgnn\b",
     "GNN"),

    # ------------------------------------------------------
    # Transformers / attention
    # ------------------------------------------------------

    (r"\btransformer",
     "transformers"),

    (r"\bvision transformer",
     "Vision Transformer"),

    (r"\bself[- ]attention\b",
     "self-attention"),

    (r"\battention mechanism",
     "attention"),

    # ------------------------------------------------------
    # Generativos
    # ------------------------------------------------------

    (r"\bgenerative ai\b",
     "generative AI"),

    (r"\bgenerative artificial intelligence\b",
     "generative AI"),

    (r"\bgenerative adversarial network",
     "GAN"),

    (r"\bgans?\b",
     "GAN"),

    (r"\bdiffusion model",
     "diffusion models"),

    (r"\bautoencoder",
     "autoencoder"),

    (r"\bvariational autoencoder",
     "VAE"),

    (r"\bvae\b",
     "VAE"),

    # ------------------------------------------------------
    # LLM / LMM / RAG / agentes
    # ------------------------------------------------------

    (r"\blarge language model",
     "LLM"),

    (r"\bllms?\b",
     "LLM"),

    (r"\blarge multimodal model",
     "LMM"),

    (r"\blmms?\b",
     "LMM"),

    (r"\bretrieval[- ]augmented generation\b",
     "RAG"),

    (r"\bai agent",
     "AI agents"),

    (r"\bagentic ai\b",
     "agentic AI"),

    # ------------------------------------------------------
    # Modelos concretos
    # ------------------------------------------------------

    (r"\bbert\b",
     "BERT"),

    (r"\broberta\b",
     "RoBERTa"),

    (r"\bgpt[- ]?[2345]?\b",
     "GPT"),

    (r"\byolo\b",
     "YOLO"),

    (r"\bresnet\b",
     "ResNet"),

    (r"\befficientnet\b",
     "EfficientNet"),

    (r"\bmobilenet\b",
     "MobileNet"),

    (r"\bu[- ]net\b",
     "U-Net"),

    (r"\bdensenet\b",
     "DenseNet"),

    # ------------------------------------------------------
    # Paradigmas de aprendizaje
    # ------------------------------------------------------

    (r"\btransfer learning\b",
     "transfer learning"),

    (r"\bself[- ]supervised learning\b",
     "self-supervised learning"),

    (r"\bsemi[- ]supervised learning\b",
     "semi-supervised learning"),

    (r"\bsupervised learning\b",
     "supervised learning"),

    (r"\bunsupervised learning\b",
     "unsupervised learning"),

    (r"\breinforcement learning\b",
     "reinforcement learning"),

    (r"\bcontrastive learning\b",
     "contrastive learning"),

    (r"\brepresentation learning\b",
     "representation learning"),

    (r"\bmetric learning\b",
     "metric learning"),

    (r"\bfew[- ]shot learning\b",
     "few-shot learning"),

    (r"\bzero[- ]shot learning\b",
     "zero-shot learning"),

    (r"\bfederated learning\b",
     "federated learning"),

    (r"\bmultimodal learning\b",
     "multimodal learning"),

    # ------------------------------------------------------
    # ML clásico
    # ------------------------------------------------------

    (r"\brandom forest",
     "random forest"),

    (r"\bsupport vector machine",
     "SVM"),

    (r"\bsvm\b",
     "SVM"),

    (r"\bxgboost\b",
     "XGBoost"),

    (r"\bgradient boosting\b",
     "gradient boosting"),

    (r"\bdecision tree",
     "decision trees"),

    (r"\bk[- ]?nearest neighbou?r",
     "KNN"),

    (r"\bknn\b",
     "KNN"),

    (r"\bk[- ]?means\b",
     "k-means"),

    (r"\bnaive bayes\b",
     "Naive Bayes"),

    (r"\bclustering\b",
     "clustering"),

    # ------------------------------------------------------
    # XAI
    # ------------------------------------------------------

    (r"\bexplainable artificial intelligence\b",
     "XAI"),

    (r"\bexplainable ai\b",
     "XAI"),

    (r"\bxai\b",
     "XAI"),

    (r"\binterpretable machine learning\b",
     "interpretable ML"),

    (r"\bshap\b",
     "SHAP"),

    (r"\blime\b",
     "LIME"),

    # ------------------------------------------------------
    # Áreas de IA
    # ------------------------------------------------------

    (r"\bnatural language processing\b",
     "NLP"),

    (r"\bnlp\b",
     "NLP"),

    (r"\bcomputer vision\b",
     "computer vision"),
]


# ==========================================================
# CONTEXTO FORENSE DIGITAL ESTRICTO
# ==========================================================

PATRONES_FORENSES = [

    # ------------------------------------------------------
    # Campo general
    # ------------------------------------------------------

    (r"\bdigital forensic",
     "digital forensics"),

    (r"\bdigital evidence\b",
     "digital evidence"),

    (r"\bdigital investigation",
     "digital investigation"),

    (r"\bcomputer forensic",
     "computer forensics"),

    (r"\bcyber forensic",
     "cyber forensics"),

    (r"\belectronic evidence\b",
     "electronic evidence"),

    # ------------------------------------------------------
    # Proceso forense
    # ------------------------------------------------------

    (r"\bforensic investigation\b",
     "forensic investigation"),

    (r"\bforensic examination\b",
     "forensic examination"),

    (r"\bforensic analysis\b",
     "forensic analysis"),

    (r"\bforensic triage\b",
     "forensic triage"),

    (r"\bforensic readiness\b",
     "forensic readiness"),

    (r"\bforensic[- ]ready\b",
     "forensic-ready"),

    (r"\bforensic timeline\b",
     "forensic timeline"),

    (r"\bevent reconstruction\b",
     "event reconstruction"),

    (r"\bchain of custody\b",
     "chain of custody"),

    # ------------------------------------------------------
    # Subdominios forenses digitales
    # ------------------------------------------------------

    (r"\bnetwork forensic",
     "network forensics"),

    (r"\bmemory forensic",
     "memory forensics"),

    (r"\bmobile forensic",
     "mobile forensics"),

    (r"\bcloud forensic",
     "cloud forensics"),

    (r"\biot forensic",
     "IoT forensics"),

    (r"\bblockchain forensic",
     "blockchain forensics"),

    (r"\bmultimedia forensic",
     "multimedia forensics"),

    (r"\bmedia forensic",
     "media forensics"),

    (r"\bimage forensic",
     "image forensics"),

    (r"\bvideo forensic",
     "video forensics"),

    (r"\baudio forensic",
     "audio forensics"),

    (r"\bmalware forensic",
     "malware forensics"),

    (r"\bandroid forensic",
     "Android forensics"),

    (r"\bios forensic",
     "iOS forensics"),

    # ------------------------------------------------------
    # Anti-forensics
    # ------------------------------------------------------

    (r"\banti[- ]forensic",
     "anti-forensics"),

    # ------------------------------------------------------
    # Procedencia / autenticidad forense
    # ------------------------------------------------------

    (r"\bsource camera identification\b",
     "source camera identification"),

    (r"\bcamera source identification\b",
     "camera source identification"),

    (r"\bmedia provenance\b",
     "media provenance"),

    (r"\bdigital provenance\b",
     "digital provenance"),

    (r"\bforensic authenticity\b",
     "forensic authenticity"),
]


# ==========================================================
# MULTIMEDIA POTENCIALMENTE FORENSE
# ==========================================================

# Estos términos NO bastan por sí solos para considerar
# que el trabajo pertenece a digital forensics.
# Se registran para análisis y revisión.

PATRONES_MULTIMEDIA = [

    (r"\bdeepfake\b",
     "deepfake"),

    (r"\bimage forgery\b",
     "image forgery"),

    (r"\bimage manipulation\b",
     "image manipulation"),

    (r"\bimage tampering\b",
     "image tampering"),

    (r"\btamper detection\b",
     "tamper detection"),

    (r"\bforgery detection\b",
     "forgery detection"),

    (r"\bforgery localization\b",
     "forgery localization"),

    (r"\bsynthetic media\b",
     "synthetic media"),

    (r"\bsteganalysis\b",
     "steganalysis"),

    (r"\bsteganograph",
     "steganography"),
]


# ==========================================================
# EVIDENCIA DIGITAL
# ==========================================================

PATRONES_EVIDENCIA = [

    # ------------------------------------------------------
    # General
    # ------------------------------------------------------

    (r"\bdigital evidence\b",
     "digital evidence"),

    (r"\belectronic evidence\b",
     "electronic evidence"),

    (r"\bdigital artifact",
     "digital artifacts"),

    (r"\bdigital artefact",
     "digital artefacts"),

    # ------------------------------------------------------
    # Ficheros y almacenamiento
    # ------------------------------------------------------

    (r"\bfile system\b",
     "file system"),

    (r"\bfilesystem\b",
     "file system"),

    (r"\bdisk image\b",
     "disk image"),

    (r"\bfile carving\b",
     "file carving"),

    (r"\bdata carving\b",
     "data carving"),

    (r"\bdeleted file",
     "deleted files"),

    (r"\bdeleted data\b",
     "deleted data"),

    (r"\bstorage device",
     "storage devices"),

    # ------------------------------------------------------
    # Memoria
    # ------------------------------------------------------

    (r"\bmemory dump",
     "memory dump"),

    (r"\bmemory image\b",
     "memory image"),

    (r"\bvolatile memory\b",
     "volatile memory"),

    (r"\bram dump\b",
     "RAM dump"),

    # ------------------------------------------------------
    # Registros y logs
    # ------------------------------------------------------

    (r"\bwindows registry\b",
     "Windows Registry"),

    (r"\bevent log",
     "event logs"),

    (r"\bsystem log",
     "system logs"),

    (r"\blog file",
     "log files"),

    # ------------------------------------------------------
    # Redes
    # ------------------------------------------------------

    (r"\bnetwork traffic\b",
     "network traffic"),

    (r"\bpacket capture\b",
     "packet capture"),

    (r"\bnetwork packet",
     "network packets"),

    (r"\bpcap\b",
     "PCAP"),

    # ------------------------------------------------------
    # Móvil
    # ------------------------------------------------------

    (r"\bmobile device",
     "mobile devices"),

    (r"\bsmartphone",
     "smartphones"),

    (r"\bandroid\b",
     "Android"),

    (r"\bios\b",
     "iOS"),

    (r"\bwhatsapp\b",
     "WhatsApp"),

    (r"\bchat message",
     "chat messages"),

    (r"\btext message",
     "text messages"),

    # ------------------------------------------------------
    # Cloud / IoT
    # ------------------------------------------------------

    (r"\bcloud log",
     "cloud logs"),

    (r"\bcloud artifact",
     "cloud artifacts"),

    (r"\biot device",
     "IoT devices"),

    (r"\biot log",
     "IoT logs"),

    # ------------------------------------------------------
    # Malware
    # ------------------------------------------------------

    (r"\bmalware sample",
     "malware samples"),

    (r"\bmalicious file",
     "malicious files"),

    # ------------------------------------------------------
    # Navegador / correo
    # ------------------------------------------------------

    (r"\bbrowser history\b",
     "browser history"),

    (r"\bweb history\b",
     "web history"),

    (r"\bemail message",
     "email messages"),

    # ------------------------------------------------------
    # Multimedia en contexto digital
    # ------------------------------------------------------

    (r"\bdigital image",
     "digital images"),

    (r"\bdigital video",
     "digital video"),

    (r"\bdigital audio",
     "digital audio"),

    (r"\bimage file",
     "image files"),

    (r"\bvideo file",
     "video files"),

    (r"\baudio file",
     "audio files"),

    (r"\bexif\b",
     "EXIF"),
]


# ==========================================================
# TAREAS OPERATIVAS OBJETIVO
# ==========================================================

PATRONES_TAREAS = {

    "DETECCION": (
        r"\bdetect(?:ion|ing|ed|s)?\b"
    ),

    "IDENTIFICACION_ATRIBUCION": (
        r"\bidentif(?:y|ies|ied|ication)\b|"
        r"\battribution\b|"
        r"\bsource attribution\b|"
        r"\bsource identification\b"
    ),

    "CLASIFICACION": (
        r"\bclassif(?:y|ies|ied|ication)\b|"
        r"\bcategor(?:y|ize|ized|ization|isation)\b"
    ),

    "FILTRADO_TRIAGE": (
        r"\bfilter(?:ing|ed)?\b|"
        r"\btriage\b"
    ),

    "PRIORIZACION_RANKING": (
        r"\bprioriti[sz]"
        r"(?:e|ed|es|ing|ation)\b|"
        r"\branking\b|"
        r"\brelevance ranking\b"
    ),
}


# ==========================================================
# CIBERSEGURIDAD PREVENTIVA NO FORENSE
# ==========================================================

PATRONES_CIBERSEGURIDAD_PREVENTIVA = {

    "INTRUSION_DETECTION": (
        r"\bintrusion detection\b|"
        r"\bintrusion detection system\b|"
        r"\bids\b"
    ),

    "PHISHING": (
        r"\bphishing detection\b"
    ),

    "DDOS": (
        r"\bddos\b|"
        r"\bdenial of service\b"
    ),

    "VULNERABILIDADES": (
        r"\bvulnerability detection\b|"
        r"\bvulnerability assessment\b"
    ),

    "BOTNET": (
        r"\bbotnet detection\b"
    ),

    "SPAM": (
        r"\bspam detection\b"
    ),

    "ATAQUES": (
        r"\bcyberattack detection\b|"
        r"\bcyber attack detection\b"
    ),

    "AUTENTICACION": (
        r"\bauthentication system\b|"
        r"\baccess control\b"
    ),
}


# ==========================================================
# FUNCIONES AUXILIARES
# ==========================================================

def limpiar_texto(texto):
    """
    Elimina HTML y normaliza los espacios.
    """

    if not texto:
        return ""

    texto = re.sub(
        r"<[^>]+>",
        " ",
        str(texto)
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
    Normaliza el texto para las búsquedas.
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
    Obtiene el texto de un elemento RDF.
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
    Recupera el TFM-ID del campo Adicional.
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
# METADATOS RDF
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
# REFERENCIAS BIBLIOGRÁFICAS
# ==========================================================

def es_elemento_bibliografico(elemento):

    tipo = obtener_tipo_documental(
        elemento
    )

    if not tipo:
        return False

    return tipo.lower() not in {
        "attachment",
        "note"
    }


# ==========================================================
# BÚSQUEDA DE INDICADORES
# ==========================================================

def buscar_indicadores(
    texto,
    patrones
):
    """
    Devuelve las etiquetas encontradas.
    """

    encontrados = []

    for patron, etiqueta in patrones:

        if re.search(
            patron,
            texto,
            re.IGNORECASE
        ):

            if etiqueta not in encontrados:

                encontrados.append(
                    etiqueta
                )

    return encontrados


def buscar_grupos(
    texto,
    patrones
):
    """
    Devuelve los grupos conceptuales encontrados.
    """

    encontrados = []

    for nombre, patron in patrones.items():

        if re.search(
            patron,
            texto,
            re.IGNORECASE
        ):

            encontrados.append(
                nombre
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
    """
    Calcula puntuación ponderada.

    Título = 5
    Palabras clave = 4
    Abstract = 2
    """

    encontrados_titulo = buscar_indicadores(
        titulo,
        patrones
    )

    encontrados_palabras = buscar_indicadores(
        palabras_clave,
        patrones
    )

    encontrados_abstract = buscar_indicadores(
        abstract,
        patrones
    )

    puntuacion = (
        len(encontrados_titulo)
        * PESO_TITULO

        + len(encontrados_palabras)
        * PESO_PALABRAS_CLAVE

        + len(encontrados_abstract)
        * PESO_ABSTRACT
    )

    encontrados_totales = []

    for conjunto in (
        encontrados_titulo,
        encontrados_palabras,
        encontrados_abstract
    ):

        for indicador in conjunto:

            if indicador not in encontrados_totales:

                encontrados_totales.append(
                    indicador
                )

    return {
        "puntuacion":
            puntuacion,

        "titulo":
            encontrados_titulo,

        "palabras_clave":
            encontrados_palabras,

        "abstract":
            encontrados_abstract,

        "total":
            encontrados_totales,
    }


# ==========================================================
# CENTRALIDAD
# ==========================================================

def componente_central(resultado):
    """
    Considera central el componente si:

    - alcanza el umbral;
    y
    - aparece en título o palabras clave;

    o bien contiene varios indicadores diferentes.
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
# LITERATURA SECUNDARIA
# ==========================================================

def detectar_literatura_secundaria(
    titulo
):
    """
    Detecta únicamente expresiones explícitas
    de literatura secundaria.
    """

    texto = normalizar_texto(
        titulo
    )

    for patron in (
        PATRONES_LITERATURA_SECUNDARIA
    ):

        if re.search(
            patron,
            texto,
            re.IGNORECASE
        ):

            return True

    return False


# ==========================================================
# CLASIFICACIÓN
# ==========================================================

def clasificar_registro(elemento):

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
    # E06 - SECUNDARIA
    # ------------------------------------------------------

    es_secundaria = (
        detectar_literatura_secundaria(
            titulo_original
        )
    )

    # ------------------------------------------------------
    # IA
    # ------------------------------------------------------

    resultado_ia = calcular_puntuacion(
        titulo,
        abstract,
        palabras_clave,
        PATRONES_IA
    )

    ia_central = componente_central(
        resultado_ia
    )

    # ------------------------------------------------------
    # FORENSE DIGITAL
    # ------------------------------------------------------

    resultado_forense = calcular_puntuacion(
        titulo,
        abstract,
        palabras_clave,
        PATRONES_FORENSES
    )

    forense_central = componente_central(
        resultado_forense
    )

    # ------------------------------------------------------
    # MULTIMEDIA
    # ------------------------------------------------------

    resultado_multimedia = calcular_puntuacion(
        titulo,
        abstract,
        palabras_clave,
        PATRONES_MULTIMEDIA
    )

    # ------------------------------------------------------
    # EVIDENCIA DIGITAL
    # ------------------------------------------------------

    resultado_evidencia = calcular_puntuacion(
        titulo,
        abstract,
        palabras_clave,
        PATRONES_EVIDENCIA
    )

    hay_evidencia = (
        resultado_evidencia[
            "puntuacion"
        ] > 0
    )

    # Un subdominio forense digital explícito
    # constituye también una señal directa del
    # objeto digital de la investigación.
    contexto_digital_suficiente = (
        hay_evidencia
        or forense_central
    )

    # ------------------------------------------------------
    # TAREAS
    # ------------------------------------------------------

    tareas_titulo = buscar_grupos(
        titulo,
        PATRONES_TAREAS
    )

    tareas_palabras = buscar_grupos(
        palabras_clave,
        PATRONES_TAREAS
    )

    tareas_abstract = buscar_grupos(
        abstract,
        PATRONES_TAREAS
    )

    hay_tarea = bool(
        tareas_titulo
        or tareas_palabras
        or tareas_abstract
    )

    tarea_central = bool(
        tareas_titulo
        or tareas_palabras
    )

    # ------------------------------------------------------
    # CIBERSEGURIDAD PREVENTIVA
    # ------------------------------------------------------

    ciber_titulo = buscar_grupos(
        titulo,
        PATRONES_CIBERSEGURIDAD_PREVENTIVA
    )

    ciber_palabras = buscar_grupos(
        palabras_clave,
        PATRONES_CIBERSEGURIDAD_PREVENTIVA
    )

    ciber_abstract = buscar_grupos(
        abstract,
        PATRONES_CIBERSEGURIDAD_PREVENTIVA
    )

    ciber_preventiva_central = bool(
        ciber_titulo
        or ciber_palabras
    )

    # ======================================================
    # DECISIÓN 1 - LITERATURA SECUNDARIA
    # ======================================================

    if es_secundaria:

        return {
            "decision":
                "SECUNDARIA_CONSERVAR",

            "motivo":
                (
                    "El título identifica explícitamente "
                    "una revisión, survey, mapping study "
                    "o publicación secundaria. "
                    "Se conserva como literatura secundaria "
                    "y no se incorpora al corpus primario."
                ),

            "ia":
                resultado_ia,

            "forense":
                resultado_forense,

            "multimedia":
                resultado_multimedia,

            "evidencia":
                resultado_evidencia,

            "ia_central":
                ia_central,

            "forense_central":
                forense_central,

            "contexto_digital":
                contexto_digital_suficiente,

            "tareas_titulo":
                tareas_titulo,

            "tareas_palabras":
                tareas_palabras,

            "tareas_abstract":
                tareas_abstract,

            "tarea_central":
                tarea_central,

            "ciber_titulo":
                ciber_titulo,

            "ciber_palabras":
                ciber_palabras,

            "ciber_abstract":
                ciber_abstract,

            "numero_palabras":
                numero_palabras,
        }

    # ======================================================
    # DECISIÓN 2 - CANDIDATO DIRECTO
    # ======================================================

    if (
        ia_central
        and forense_central
        and contexto_digital_suficiente
        and tarea_central
    ):

        return {
            "decision":
                "CANDIDATO_TEXTO_COMPLETO",

            "motivo":
                (
                    "La IA constituye un componente central, "
                    "el contexto forense digital es explícito, "
                    "existe un objeto digital de análisis "
                    "y una tarea de detección, identificación, "
                    "clasificación, filtrado o priorización "
                    "es central en el trabajo."
                ),

            "ia":
                resultado_ia,

            "forense":
                resultado_forense,

            "multimedia":
                resultado_multimedia,

            "evidencia":
                resultado_evidencia,

            "ia_central":
                ia_central,

            "forense_central":
                forense_central,

            "contexto_digital":
                contexto_digital_suficiente,

            "tareas_titulo":
                tareas_titulo,

            "tareas_palabras":
                tareas_palabras,

            "tareas_abstract":
                tareas_abstract,

            "tarea_central":
                tarea_central,

            "ciber_titulo":
                ciber_titulo,

            "ciber_palabras":
                ciber_palabras,

            "ciber_abstract":
                ciber_abstract,

            "numero_palabras":
                numero_palabras,
        }

    # ======================================================
    # DECISIÓN 3 - CIBERSEGURIDAD PREVENTIVA CLARA
    # ======================================================

    if (
        ia_central
        and ciber_preventiva_central
        and not forense_central
        and not hay_evidencia
        and numero_palabras
        >= MINIMO_PALABRAS_PARA_EXCLUIR
    ):

        return {
            "decision":
                "EXCLUIR_ALTA_CONFIANZA",

            "motivo":
                (
                    "La publicación aplica IA a una tarea "
                    "de ciberseguridad preventiva identificada "
                    "en título o palabras clave, sin que se "
                    "haya identificado contexto forense digital "
                    "ni evidencia digital como objeto de análisis."
                ),

            "ia":
                resultado_ia,

            "forense":
                resultado_forense,

            "multimedia":
                resultado_multimedia,

            "evidencia":
                resultado_evidencia,

            "ia_central":
                ia_central,

            "forense_central":
                forense_central,

            "contexto_digital":
                contexto_digital_suficiente,

            "tareas_titulo":
                tareas_titulo,

            "tareas_palabras":
                tareas_palabras,

            "tareas_abstract":
                tareas_abstract,

            "tarea_central":
                tarea_central,

            "ciber_titulo":
                ciber_titulo,

            "ciber_palabras":
                ciber_palabras,

            "ciber_abstract":
                ciber_abstract,

            "numero_palabras":
                numero_palabras,
        }

    # ======================================================
    # DECISIÓN 4 - AUSENCIA EXPLÍCITA DE IA
    # ======================================================

    if (
        resultado_ia[
            "puntuacion"
        ] == 0

        and numero_palabras
        >= MINIMO_PALABRAS_PARA_EXCLUIR
    ):

        return {
            "decision":
                "EXCLUIR_ALTA_CONFIANZA",

            "motivo":
                (
                    "En título, palabras clave y abstract "
                    "no se ha identificado ningún indicador "
                    "de una técnica de inteligencia artificial."
                ),

            "ia":
                resultado_ia,

            "forense":
                resultado_forense,

            "multimedia":
                resultado_multimedia,

            "evidencia":
                resultado_evidencia,

            "ia_central":
                ia_central,

            "forense_central":
                forense_central,

            "contexto_digital":
                contexto_digital_suficiente,

            "tareas_titulo":
                tareas_titulo,

            "tareas_palabras":
                tareas_palabras,

            "tareas_abstract":
                tareas_abstract,

            "tarea_central":
                tarea_central,

            "ciber_titulo":
                ciber_titulo,

            "ciber_palabras":
                ciber_palabras,

            "ciber_abstract":
                ciber_abstract,

            "numero_palabras":
                numero_palabras,
        }

    # ======================================================
    # DECISIÓN 5 - SIN CONTEXTO FORENSE NI EVIDENCIA
    # ======================================================

    if (
        resultado_forense[
            "puntuacion"
        ] == 0

        and resultado_evidencia[
            "puntuacion"
        ] == 0

        and numero_palabras
        >= MINIMO_PALABRAS_PARA_EXCLUIR
    ):

        return {
            "decision":
                "EXCLUIR_ALTA_CONFIANZA",

            "motivo":
                (
                    "En título, palabras clave y abstract "
                    "no se ha identificado contexto de "
                    "análisis forense digital ni evidencia "
                    "digital como objeto de análisis."
                ),

            "ia":
                resultado_ia,

            "forense":
                resultado_forense,

            "multimedia":
                resultado_multimedia,

            "evidencia":
                resultado_evidencia,

            "ia_central":
                ia_central,

            "forense_central":
                forense_central,

            "contexto_digital":
                contexto_digital_suficiente,

            "tareas_titulo":
                tareas_titulo,

            "tareas_palabras":
                tareas_palabras,

            "tareas_abstract":
                tareas_abstract,

            "tarea_central":
                tarea_central,

            "ciber_titulo":
                ciber_titulo,

            "ciber_palabras":
                ciber_palabras,

            "ciber_abstract":
                ciber_abstract,

            "numero_palabras":
                numero_palabras,
        }

    # ======================================================
    # DECISIÓN 6 - SIN TAREA OBJETIVO
    # ======================================================

    if (
        not hay_tarea

        and numero_palabras
        >= MINIMO_PALABRAS_PARA_EXCLUIR
    ):

        return {
            "decision":
                "EXCLUIR_ALTA_CONFIANZA",

            "motivo":
                (
                    "No se ha identificado ninguna tarea "
                    "de detección, identificación, atribución, "
                    "clasificación, filtrado, triage, "
                    "priorización o ranking en título, "
                    "palabras clave o abstract."
                ),

            "ia":
                resultado_ia,

            "forense":
                resultado_forense,

            "multimedia":
                resultado_multimedia,

            "evidencia":
                resultado_evidencia,

            "ia_central":
                ia_central,

            "forense_central":
                forense_central,

            "contexto_digital":
                contexto_digital_suficiente,

            "tareas_titulo":
                tareas_titulo,

            "tareas_palabras":
                tareas_palabras,

            "tareas_abstract":
                tareas_abstract,

            "tarea_central":
                tarea_central,

            "ciber_titulo":
                ciber_titulo,

            "ciber_palabras":
                ciber_palabras,

            "ciber_abstract":
                ciber_abstract,

            "numero_palabras":
                numero_palabras,
        }

    # ======================================================
    # DECISIÓN 7 - REVISIÓN MANUAL
    # ======================================================

    motivos_revision = []

    if not ia_central:
        motivos_revision.append(
            "IA no confirmada como componente central"
        )

    if not forense_central:
        motivos_revision.append(
            "contexto forense digital no confirmado "
            "como central"
        )

    if not contexto_digital_suficiente:
        motivos_revision.append(
            "objeto de evidencia digital no confirmado"
        )

    if not tarea_central:

        if tareas_abstract:

            motivos_revision.append(
                "la tarea objetivo aparece solo "
                "en el abstract"
            )

        else:

            motivos_revision.append(
                "centralidad de la tarea objetivo "
                "no confirmada"
            )

    if resultado_multimedia["puntuacion"] > 0:
        motivos_revision.append(
            "contenido multimedia que requiere "
            "confirmar contexto forense"
        )

    return {
        "decision":
            "REVISION_MANUAL_E06_E07",

        "motivo":
            "; ".join(
                motivos_revision
            ),

        "ia":
            resultado_ia,

        "forense":
            resultado_forense,

        "multimedia":
            resultado_multimedia,

        "evidencia":
            resultado_evidencia,

        "ia_central":
            ia_central,

        "forense_central":
            forense_central,

        "contexto_digital":
            contexto_digital_suficiente,

        "tareas_titulo":
            tareas_titulo,

        "tareas_palabras":
            tareas_palabras,

        "tareas_abstract":
            tareas_abstract,

        "tarea_central":
            tarea_central,

        "ciber_titulo":
            ciber_titulo,

        "ciber_palabras":
            ciber_palabras,

        "ciber_abstract":
            ciber_abstract,

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

    "decision",
    "motivo",

    "puntuacion_ia",
    "ia_central",
    "indicadores_ia",

    "puntuacion_forense",
    "forense_central",
    "indicadores_forenses",

    "puntuacion_multimedia",
    "indicadores_multimedia",

    "puntuacion_evidencia",
    "contexto_digital_suficiente",
    "indicadores_evidencia",

    "tareas_titulo",
    "tareas_palabras_clave",
    "tareas_abstract",
    "tarea_objetivo_central",

    "ciberseguridad_titulo",
    "ciberseguridad_palabras_clave",
    "ciberseguridad_abstract",

    "numero_palabras_analizadas",

    "palabras_clave",
    "abstract",

    "decision_manual",
    "motivo_manual",
    "observaciones_manual",
]


# ==========================================================
# GENERACIÓN DE FILA
# ==========================================================

def generar_fila(elemento):

    resultado = clasificar_registro(
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

        "decision":
            resultado[
                "decision"
            ],

        "motivo":
            resultado[
                "motivo"
            ],

        "puntuacion_ia":
            resultado[
                "ia"
            ][
                "puntuacion"
            ],

        "ia_central":
            resultado[
                "ia_central"
            ],

        "indicadores_ia":
            "; ".join(
                resultado[
                    "ia"
                ][
                    "total"
                ]
            ),

        "puntuacion_forense":
            resultado[
                "forense"
            ][
                "puntuacion"
            ],

        "forense_central":
            resultado[
                "forense_central"
            ],

        "indicadores_forenses":
            "; ".join(
                resultado[
                    "forense"
                ][
                    "total"
                ]
            ),

        "puntuacion_multimedia":
            resultado[
                "multimedia"
            ][
                "puntuacion"
            ],

        "indicadores_multimedia":
            "; ".join(
                resultado[
                    "multimedia"
                ][
                    "total"
                ]
            ),

        "puntuacion_evidencia":
            resultado[
                "evidencia"
            ][
                "puntuacion"
            ],

        "contexto_digital_suficiente":
            resultado[
                "contexto_digital"
            ],

        "indicadores_evidencia":
            "; ".join(
                resultado[
                    "evidencia"
                ][
                    "total"
                ]
            ),

        "tareas_titulo":
            "; ".join(
                resultado[
                    "tareas_titulo"
                ]
            ),

        "tareas_palabras_clave":
            "; ".join(
                resultado[
                    "tareas_palabras"
                ]
            ),

        "tareas_abstract":
            "; ".join(
                resultado[
                    "tareas_abstract"
                ]
            ),

        "tarea_objetivo_central":
            resultado[
                "tarea_central"
            ],

        "ciberseguridad_titulo":
            "; ".join(
                resultado[
                    "ciber_titulo"
                ]
            ),

        "ciberseguridad_palabras_clave":
            "; ".join(
                resultado[
                    "ciber_palabras"
                ]
            ),

        "ciberseguridad_abstract":
            "; ".join(
                resultado[
                    "ciber_abstract"
                ]
            ),

        "numero_palabras_analizadas":
            resultado[
                "numero_palabras"
            ],

        "palabras_clave":
            obtener_palabras_clave(
                elemento
            ),

        "abstract":
            obtener_abstract(
                elemento
            ),

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
        "E06 + E07 - CRIBADO CORREGIDO "
        "PREVIO A TEXTO COMPLETO"
    )

    print("=" * 70)

    if not ARCHIVO_RDF_ENTRADA.exists():

        raise FileNotFoundError(
            "No se encuentra el fichero: "
            f"{ARCHIVO_RDF_ENTRADA}"
        )

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
    # CONTROL TFM-ID
    # ------------------------------------------------------

    identificadores = [
        obtener_tfm_id(
            elemento
        )
        for elemento in elementos
    ]

    if any(
        not identificador
        for identificador in identificadores
    ):

        raise ValueError(
            "Existen referencias sin TFM-ID."
        )

    if (
        len(
            set(
                identificadores
            )
        )
        != len(
            identificadores
        )
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

    candidatos = [
        fila
        for fila in filas
        if fila[
            "decision"
        ]
        == "CANDIDATO_TEXTO_COMPLETO"
    ]

    revision = [
        fila
        for fila in filas
        if fila[
            "decision"
        ]
        == "REVISION_MANUAL_E06_E07"
    ]

    secundaria = [
        fila
        for fila in filas
        if fila[
            "decision"
        ]
        == "SECUNDARIA_CONSERVAR"
    ]

    excluidos = [
        fila
        for fila in filas
        if fila[
            "decision"
        ]
        == "EXCLUIR_ALTA_CONFIANZA"
    ]

    # ------------------------------------------------------
    # CONTROL DE SUMA
    # ------------------------------------------------------

    total_clasificado = (
        len(candidatos)
        + len(revision)
        + len(secundaria)
        + len(excluidos)
    )

    if (
        total_clasificado
        != len(elementos)
    ):

        raise ValueError(
            "La clasificación no cubre todos "
            "los registros."
        )

    # ------------------------------------------------------
    # MUESTRA DE CONTROL
    # ------------------------------------------------------

    generador = random.Random(
        SEMILLA_MUESTRA
    )

    numero_muestra = min(
        TAMANO_MUESTRA_CONTROL,
        len(excluidos)
    )

    if numero_muestra:

        muestra_control = (
            generador.sample(
                excluidos,
                numero_muestra
            )
        )

    else:

        muestra_control = []

    # ------------------------------------------------------
    # ESCRITURA
    # ------------------------------------------------------

    escribir_csv(
        filas,
        ARCHIVO_RESULTADOS
    )

    escribir_csv(
        candidatos,
        ARCHIVO_CANDIDATOS
    )

    escribir_csv(
        revision,
        ARCHIVO_REVISION_MANUAL
    )

    escribir_csv(
        secundaria,
        ARCHIVO_SECUNDARIA
    )

    escribir_csv(
        excluidos,
        ARCHIVO_EXCLUIDOS
    )

    escribir_csv(
        muestra_control,
        ARCHIVO_MUESTRA_CONTROL
    )

    # ------------------------------------------------------
    # MOTIVOS
    # ------------------------------------------------------

    contador_motivos = Counter(
        fila["motivo"]
        for fila in excluidos
    )

    texto_motivos = "\n".join(
        (
            f"  {motivo}: {numero}"
        )
        for motivo, numero
        in contador_motivos.most_common()
    )

    # ------------------------------------------------------
    # RESUMEN
    # ------------------------------------------------------

    resumen = (
        "E06 + E07 - CRIBADO CORREGIDO\n"
        "============================================\n\n"

        f"Registros analizados: "
        f"{len(elementos)}\n\n"

        f"Candidatos a texto completo: "
        f"{len(candidatos)}\n"

        f"Pendientes de revisión manual: "
        f"{len(revision)}\n"

        f"Literatura secundaria conservada: "
        f"{len(secundaria)}\n"

        f"Excluidos con alta confianza: "
        f"{len(excluidos)}\n\n"

        f"Muestra de control: "
        f"{len(muestra_control)}\n\n"

        "Motivos de exclusión automática:\n"

        f"{texto_motivos}\n"
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
        ARCHIVO_CANDIDATOS
    )

    print(
        ARCHIVO_REVISION_MANUAL
    )

    print(
        ARCHIVO_SECUNDARIA
    )

    print(
        ARCHIVO_EXCLUIDOS
    )

    print(
        ARCHIVO_MUESTRA_CONTROL
    )

    print(
        ARCHIVO_RESUMEN
    )


if __name__ == "__main__":
    principal()