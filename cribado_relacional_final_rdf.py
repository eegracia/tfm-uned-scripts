#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CRIBADO RELACIONAL FINAL

Revisión sistemática PRISMA / PRISMA-S.

Entrada:
    TFM_PENDIENTES_CRIBA_5332.rdf

El procedimiento evalúa cinco requisitos:

1. IA_ES_METODO
2. FORENSE_DIGITAL_REAL
3. EVIDENCIA_DE_DISPOSITIVO
4. IA_ACTUA_SOBRE_EVIDENCIA
5. TAREA_OBJETIVO

Se analizan:
- título;
- palabras clave;
- abstract;
- coaparición de conceptos;
- proximidad entre conceptos;
- contexto de uso de las técnicas.

Resultados posibles:

- CANDIDATO_CORPUS_PRINCIPAL
- LITERATURA_COMPLEMENTARIA
- REVISION_MANUAL
- EXCLUIR_ALTA_CONFIANZA
- SECUNDARIA_CONSERVAR

El script utiliza exclusivamente la biblioteca estándar
de Python.
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
    "cribado_relacional_final"
)

ARCHIVO_RESULTADOS = (
    DIRECTORIO_SALIDA
    / "TFM_relacional_resultados.csv"
)

ARCHIVO_CANDIDATOS = (
    DIRECTORIO_SALIDA
    / "TFM_relacional_corpus_principal.csv"
)

ARCHIVO_COMPLEMENTARIA = (
    DIRECTORIO_SALIDA
    / "TFM_relacional_literatura_complementaria.csv"
)

ARCHIVO_REVISION = (
    DIRECTORIO_SALIDA
    / "TFM_relacional_revision_manual.csv"
)

ARCHIVO_EXCLUIDOS = (
    DIRECTORIO_SALIDA
    / "TFM_relacional_excluidos.csv"
)

ARCHIVO_SECUNDARIA = (
    DIRECTORIO_SALIDA
    / "TFM_relacional_literatura_secundaria.csv"
)

ARCHIVO_MUESTRA_EXCLUIDOS = (
    DIRECTORIO_SALIDA
    / "TFM_relacional_muestra_excluidos.csv"
)

ARCHIVO_MUESTRA_CANDIDATOS = (
    DIRECTORIO_SALIDA
    / "TFM_relacional_muestra_candidatos.csv"
)

ARCHIVO_RESUMEN = (
    DIRECTORIO_SALIDA
    / "TFM_relacional_resumen.txt"
)

NUMERO_ESPERADO_REGISTROS = 5332

MINIMO_PALABRAS_EXCLUSION = 80

DISTANCIA_MAXIMA_RELACION = 35

TAMANO_MUESTRA_CONTROL = 50

SEMILLA_MUESTRA = 2026


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
# LITERATURA SECUNDARIA
# ==========================================================

PATRONES_SECUNDARIA = [

    r"\bsystematic review\b",
    r"\bsystematic literature review\b",
    r"\bliterature review\b",
    r"\bscoping review\b",
    r"\bcritical review\b",
    r"\bcomprehensive review\b",
    r"\bnarrative review\b",
    r"\bintegrative review\b",

    r"\breview\b",

    r"\bsurvey\b",

    r"\boverview\b",

    r"\bsystematic mapping\b",
    r"\bmapping study\b",

    r"\bbibliometric review\b",
    r"\bbibliometric analysis\b",

    r"\bstate[- ]of[- ]the[- ]art\b",
    r"\bstate of the art\b",
]


# ==========================================================
# INTELIGENCIA ARTIFICIAL
# ==========================================================

PATRONES_IA = {

    "ARTIFICIAL_INTELLIGENCE":
        r"\bartificial intelligence\b",

    "MACHINE_LEARNING":
        r"\bmachine learning\b",

    "DEEP_LEARNING":
        r"\bdeep learning\b",

    "COMPUTATIONAL_INTELLIGENCE":
        r"\bcomputational intelligence\b",

    "NEURAL_NETWORK":
        r"\bneural network",

    "DEEP_NEURAL_NETWORK":
        r"\bdeep neural network",

    "CNN":
        (
            r"\bcnn\b|"
            r"\bconvolutional neural network"
        ),

    "RNN":
        (
            r"\brnn\b|"
            r"\brecurrent neural network"
        ),

    "LSTM":
        r"\blstm\b",

    "GRU":
        r"\bgru\b",

    "GNN":
        (
            r"\bgnn\b|"
            r"\bgraph neural network"
        ),

    "TRANSFORMER":
        r"\btransformer",

    "VISION_TRANSFORMER":
        r"\bvision transformer",

    "ATTENTION":
        (
            r"\bself[- ]attention\b|"
            r"\battention mechanism\b|"
            r"\bmulti[- ]head attention\b"
        ),

    "GAN":
        (
            r"\bgans?\b|"
            r"\bgenerative adversarial network"
        ),

    "AUTOENCODER":
        r"\bautoencoder",

    "VARIATIONAL_AUTOENCODER":
        (
            r"\bvariational autoencoder\b|"
            r"\bvae\b"
        ),

    "DIFFUSION":
        r"\bdiffusion model",

    "GENERATIVE_AI":
        (
            r"\bgenerative ai\b|"
            r"\bgenerative artificial intelligence\b"
        ),

    "LARGE_LANGUAGE_MODEL":
        (
            r"\blarge language models?\b|"
            r"\bllms?\b"
        ),

    "LARGE_MULTIMODAL_MODEL":
        (
            r"\blarge multimodal models?\b|"
            r"\blmms?\b"
        ),

    "RAG":
        r"\bretrieval[- ]augmented generation\b",

    "AGENTES":
        (
            r"\bai agents?\b|"
            r"\bagentic ai\b"
        ),

    "BERT":
        r"\bbert\b",

    "ROBERTA":
        r"\broberta\b",

    "GPT":
        r"\bgpt[- ]?[2345]?\b",

    "YOLO":
        r"\byolo\b",

    "RESNET":
        r"\bresnet\b",

    "EFFICIENTNET":
        r"\befficientnet\b",

    "MOBILENET":
        r"\bmobilenet\b",

    "UNET":
        r"\bu[- ]net\b",

    "DENSENET":
        r"\bdensenet\b",

    "TRANSFER_LEARNING":
        r"\btransfer learning\b",

    "SELF_SUPERVISED":
        r"\bself[- ]supervised learning\b",

    "SEMI_SUPERVISED":
        r"\bsemi[- ]supervised learning\b",

    "SUPERVISED_LEARNING":
        r"\bsupervised learning\b",

    "UNSUPERVISED_LEARNING":
        r"\bunsupervised learning\b",

    "REINFORCEMENT_LEARNING":
        r"\breinforcement learning\b",

    "CONTRASTIVE_LEARNING":
        r"\bcontrastive learning\b",

    "REPRESENTATION_LEARNING":
        r"\brepresentation learning\b",

    "FEW_SHOT":
        r"\bfew[- ]shot learning\b",

    "ZERO_SHOT":
        r"\bzero[- ]shot learning\b",

    "FEDERATED_LEARNING":
        r"\bfederated learning\b",

    "ENSEMBLE_LEARNING":
        r"\bensemble learning\b",

    "RANDOM_FOREST":
        r"\brandom forest",

    "SVM":
        (
            r"\bsvm\b|"
            r"\bsupport vector machine"
        ),

    "XGBOOST":
        r"\bxgboost\b",

    "GRADIENT_BOOSTING":
        r"\bgradient boosting\b",

    "DECISION_TREE":
        r"\bdecision tree",

    "KNN":
        (
            r"\bknn\b|"
            r"\bk[- ]?nearest neighbou?r"
        ),

    "KMEANS":
        r"\bk[- ]?means\b",

    "NAIVE_BAYES":
        r"\bnaive bayes\b",

    "CLUSTERING":
        r"\bclustering\b",

    "XAI":
        (
            r"\bxai\b|"
            r"\bexplainable ai\b|"
            r"\bexplainable artificial intelligence\b"
        ),

    "NLP":
        (
            r"\bnlp\b|"
            r"\bnatural language processing\b"
        ),

    "COMPUTER_VISION":
        r"\bcomputer vision\b",

    "SIAMESE_NETWORK":
        r"\bsiamese (?:neural )?network",

    "ARTIFICIAL_IMMUNE":
        (
            r"\bartificial immune "
            r"(?:system|intelligence)\b"
        ),
}


# ==========================================================
# EXPRESIONES QUE INDICAN USO DE IA COMO MÉTODO
# ==========================================================

PATRONES_USO_IA = [

    r"\buse(?:d|s|ing)?\b",
    r"\bapply(?:ing|ies|ied)?\b",
    r"\bemploy(?:ed|ing|s)?\b",
    r"\bleverag(?:e|ed|es|ing)\b",
    r"\btrain(?:ed|ing|s)?\b",
    r"\bdevelop(?:ed|ing|s)?\b",
    r"\bimplement(?:ed|ing|s)?\b",
    r"\bpropos(?:e|ed|es|ing)\b",
    r"\butili[sz](?:e|ed|es|ing)\b",
    r"\bclassif(?:y|ies|ied|ication)\b",
    r"\bdetect(?:s|ed|ing|ion)?\b",
    r"\bidentif(?:y|ies|ied|ication)\b",
    r"\banaly[sz](?:e|ed|es|ing)\b",
    r"\bmodel(?:led|ed|ing)?\b",
    r"\bpredict(?:s|ed|ing|ion)?\b",
]


# ==========================================================
# IA COMO OBJETO INVESTIGADO
# ==========================================================

PATRONES_IA_COMO_OBJETO = [

    r"\bforensic(?:s)? of artificial intelligence\b",

    r"\bforensic analysis of "
    r"(?:chatgpt|llm|artificial intelligence|ai systems?)\b",

    r"\bforensic examination of "
    r"(?:chatgpt|llm|artificial intelligence|ai systems?)\b",

    r"\btraces? (?:left|generated|created) by "
    r"(?:ai|chatgpt|llm)",

    r"\bartifacts? (?:left|generated|created) by "
    r"(?:ai|chatgpt|llm)",

    r"\bai application artifacts?\b",

    r"\bchatgpt artifacts?\b",

    r"\bllm artifacts?\b",

    r"\bforensic examination of an? ai system\b",
]


# ==========================================================
# CONTEXTO FORENSE DIGITAL
# ==========================================================

PATRONES_FORENSES = {

    "DIGITAL_FORENSICS":
        r"\bdigital forensic",

    "DIGITAL_EVIDENCE":
        r"\bdigital evidence\b",

    "DIGITAL_INVESTIGATION":
        r"\bdigital investigation",

    "DIGITAL_CRIME":
        r"\bdigital crime investigation\b",

    "COMPUTER_FORENSICS":
        r"\bcomputer forensic",

    "CYBER_FORENSICS":
        r"\bcyber forensic",

    "ELECTRONIC_EVIDENCE":
        r"\belectronic evidence\b",

    "FORENSIC_INVESTIGATION":
        r"\bforensic investigation\b",

    "FORENSIC_EXAMINATION":
        r"\bforensic examination\b",

    "FORENSIC_ANALYSIS":
        r"\bforensic analysis\b",

    "FORENSIC_TRIAGE":
        r"\bforensic triage\b",

    "FORENSIC_TIMELINE":
        r"\bforensic timeline\b",

    "EVENT_RECONSTRUCTION":
        r"\bevent reconstruction\b",

    "INCIDENT_RECONSTRUCTION":
        r"\bincident reconstruction\b",

    "POST_INCIDENT":
        r"\bpost[- ]incident investigation\b",

    "MEMORY_FORENSICS":
        r"\bmemory forensic",

    "MOBILE_FORENSICS":
        r"\bmobile forensic",

    "NETWORK_FORENSICS":
        r"\bnetwork forensic",

    "CLOUD_FORENSICS":
        r"\bcloud forensic",

    "IOT_FORENSICS":
        r"\biot forensic",

    "FILESYSTEM_FORENSICS":
        (
            r"\bfilesystem forensic|"
            r"\bfile system forensic"
        ),

    "MALWARE_FORENSICS":
        r"\bmalware forensic",

    "DATABASE_FORENSICS":
        r"\bdatabase forensic",

    "BROWSER_FORENSICS":
        r"\bbrowser forensic",

    "MULTIMEDIA_FORENSICS":
        r"\bmultimedia forensic",

    "IMAGE_FORENSICS":
        r"\bimage forensic",

    "VIDEO_FORENSICS":
        r"\bvideo forensic",

    "AUDIO_FORENSICS":
        r"\baudio forensic",

    "ANDROID_FORENSICS":
        r"\bandroid forensic",

    "IOS_FORENSICS":
        r"\bios forensic",

    "DOCUMENT_FORENSICS":
        r"\bdocument forensic",

    "PDF_FORENSICS":
        r"\bpdf forensic",

    "ANTI_FORENSICS":
        r"\banti[- ]forensic",
}


# ==========================================================
# EVIDENCIA PROCEDENTE DE DISPOSITIVOS O SISTEMAS
# ==========================================================

PATRONES_EVIDENCIA_DISPOSITIVO = {

    "DIGITAL_EVIDENCE":
        r"\bdigital evidence\b",

    "ELECTRONIC_EVIDENCE":
        r"\belectronic evidence\b",

    "DIGITAL_ARTIFACT":
        (
            r"\bdigital artifact|"
            r"\bdigital artefact"
        ),

    "FILE_SYSTEM":
        (
            r"\bfile system\b|"
            r"\bfilesystem\b"
        ),

    "FILE_FRAGMENT":
        r"\bfile fragment",

    "FILE_CARVING":
        r"\bfile carving\b",

    "DATA_CARVING":
        r"\bdata carving\b",

    "DELETED_FILES":
        r"\bdeleted (?:file|files|data)\b",

    "CORRUPTED_FILE":
        r"\bcorrupted file",

    "DISK_IMAGE":
        r"\bdisk image\b",

    "PDF":
        (
            r"\bpdf files?\b|"
            r"\bpdf documents?\b|"
            r"\bcorrupted pdf\b"
        ),

    "MEMORY":
        (
            r"\bmemory dump|"
            r"\bmemory image\b|"
            r"\bvolatile memory\b|"
            r"\bram dump\b"
        ),

    "REGISTRY":
        r"\bwindows registry\b",

    "LOG":
        (
            r"\bevent logs?\b|"
            r"\bsystem logs?\b|"
            r"\bapplication logs?\b|"
            r"\bforensic logs?\b"
        ),

    "PACKET_CAPTURE":
        (
            r"\bpacket capture\b|"
            r"\bpcap\b"
        ),

    "MOBILE_ARTIFACT":
        (
            r"\bmobile artifacts?\b|"
            r"\bmobile artefacts?\b|"
            r"\bandroid artifacts?\b|"
            r"\bios artifacts?\b"
        ),

    "MESSAGES":
        (
            r"\bwhatsapp\b|"
            r"\bchat messages?\b|"
            r"\btext messages?\b|"
            r"\bemail messages?\b"
        ),

    "BROWSER":
        (
            r"\bbrowser history\b|"
            r"\bweb history\b"
        ),

    "CLOUD_ARTIFACT":
        (
            r"\bcloud artifacts?\b|"
            r"\bcloud logs?\b"
        ),

    "IOT_ARTIFACT":
        (
            r"\biot artifacts?\b|"
            r"\biot logs?\b"
        ),

    "APPLICATION_ARTIFACT":
        r"\bapplication artifacts?\b",

    "DATABASE_RECORD":
        r"\bdatabase records?\b",
}


# ==========================================================
# OBJETOS DIGITALES QUE REQUIEREN CONTEXTO FORENSE
# ==========================================================

PATRONES_EVIDENCIA_CONDICIONADA = {

    "NETWORK_TRAFFIC":
        r"\bnetwork traffic\b",

    "NETWORK_PACKET":
        r"\bnetwork packets?\b",

    "MALWARE_SAMPLE":
        (
            r"\bmalware samples?\b|"
            r"\bmalicious files?\b"
        ),

    "DIGITAL_IMAGE":
        (
            r"\bdigital images?\b|"
            r"\bimage files?\b"
        ),

    "DIGITAL_VIDEO":
        (
            r"\bdigital videos?\b|"
            r"\bvideo files?\b"
        ),

    "DIGITAL_AUDIO":
        (
            r"\bdigital audio\b|"
            r"\baudio files?\b"
        ),

    "DEEPFAKE":
        r"\bdeepfake",

    "IMAGE_FORGERY":
        r"\bimage forgery\b",

    "VIDEO_FORGERY":
        r"\bvideo forgery\b",

    "IMAGE_MANIPULATION":
        r"\bimage manipulation\b",

    "VIDEO_MANIPULATION":
        r"\bvideo manipulation\b",
}


# ==========================================================
# TAREAS OBJETIVO
# ==========================================================

PATRONES_TAREAS = {

    "DETECCION":
        r"\bdetect(?:ion|ing|ed|s)?\b",

    "IDENTIFICACION":
        r"\bidentif(?:y|ies|ied|ication)\b",

    "ATRIBUCION":
        (
            r"\battribution\b|"
            r"\bsource identification\b|"
            r"\bsource attribution\b"
        ),

    "CLASIFICACION":
        (
            r"\bclassif(?:y|ies|ied|ication)\b|"
            r"\bcategor(?:ize|ized|ization|isation)\b"
        ),

    "FILTRADO":
        r"\bfilter(?:ing|ed)?\b",

    "TRIAGE":
        r"\btriage\b",

    "PRIORIZACION":
        (
            r"\bprioriti[sz]"
            r"(?:e|ed|es|ing|ation)\b"
        ),

    "RANKING":
        r"\branking\b",

    "LOCALIZACION":
        (
            r"\blocali[sz]"
            r"(?:e|ed|es|ing|ation)\b"
        ),
}


# ==========================================================
# TAREAS FUERA DEL FOCO PRINCIPAL
# ==========================================================

PATRONES_TAREAS_NO_OBJETIVO = [

    r"\bchain of custody\b",
    r"\bevidence preservation\b",
    r"\bevidence storage\b",
    r"\bforensic readiness\b",
    r"\breport generation\b",
    r"\breport summarization\b",
    r"\bforensic report\b",
    r"\bblockchain[- ]based storage\b",
    r"\bevidence integrity\b",
]


# ==========================================================
# CIBERSEGURIDAD PREVENTIVA
# ==========================================================

PATRONES_CIBERSEGURIDAD_PREVENTIVA = [

    r"\bintrusion detection\b",
    r"\bintrusion detection system\b",

    r"\bphishing detection\b",

    r"\bddos\b",
    r"\bdenial of service\b",

    r"\bvulnerability detection\b",
    r"\bvulnerability assessment\b",

    r"\bbotnet detection\b",

    r"\battack prediction\b",

    r"\bthreat prediction\b",

    r"\breal[- ]time threat detection\b",

    r"\bnetwork intrusion\b",
]


# ==========================================================
# ÁMBITOS NO TÉCNICOS
# ==========================================================

PATRONES_NO_TECNICOS = [

    r"\blegal framework\b",
    r"\blegal analysis\b",
    r"\blegislation\b",
    r"\bjudicial\b",

    r"\beducation\b",
    r"\bteaching\b",
    r"\bcurriculum\b",
    r"\bcourse survey\b",

    r"\bgovernance\b",
    r"\bethical framework\b",
    r"\bpolicy framework\b",
]


# ==========================================================
# FUNCIONES DE TEXTO
# ==========================================================

def limpiar_texto(texto):
    """
    Elimina HTML y normaliza espacios.
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

    texto = re.sub(
        r"\s+",
        " ",
        texto
    )

    return texto.strip()


def normalizar_texto(texto):
    """
    Convierte a minúsculas y elimina diacríticos.
    """

    texto = limpiar_texto(
        texto
    ).lower()

    texto = unicodedata.normalize(
        "NFKD",
        texto
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
    Obtiene el texto completo de un elemento XML.
    """

    if elemento is None:
        return ""

    return limpiar_texto(
        "".join(
            elemento.itertext()
        )
    )


def dividir_frases(texto):
    """
    Divide un texto en unidades aproximadas de frase.
    """

    texto = limpiar_texto(
        texto
    )

    if not texto:
        return []

    return [
        frase.strip()
        for frase in re.split(
            r"(?<=[.!?;])\s+",
            texto
        )
        if frase.strip()
    ]


# ==========================================================
# EXTRACCIÓN RDF
# ==========================================================

def obtener_tfm_id(elemento):
    """
    Recupera el TFM-ID almacenado en Adicional.
    """

    for descripcion in elemento.findall(
        "dc:description",
        ESPACIOS_NOMBRES
    ):

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

        if valor and valor not in palabras:
            palabras.append(
                valor
            )

    return "; ".join(
        palabras
    )


def obtener_doi(elemento):

    for identificador in elemento.findall(
        "dc:identifier",
        ESPACIOS_NOMBRES
    ):

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


def es_elemento_bibliografico(elemento):

    tipo = obtener_tipo_documental(
        elemento
    )

    return (
        bool(tipo)
        and tipo.lower()
        not in {
            "attachment",
            "note"
        }
    )


# ==========================================================
# BÚSQUEDA DE PATRONES
# ==========================================================

def buscar_grupos(
    texto,
    patrones
):
    """
    Devuelve los grupos encontrados.
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


def contiene_alguno(
    texto,
    patrones
):
    """
    Comprueba si aparece al menos un patrón.
    """

    return any(
        re.search(
            patron,
            texto,
            re.IGNORECASE
        )
        for patron in patrones
    )


# ==========================================================
# PROXIMIDAD ENTRE CONCEPTOS
# ==========================================================

def posiciones_patrones(
    texto,
    patrones
):

    posiciones = []

    for patron in patrones.values():

        for coincidencia in re.finditer(
            patron,
            texto,
            re.IGNORECASE
        ):

            posicion = len(
                texto[
                    :coincidencia.start()
                ].split()
            )

            posiciones.append(
                posicion
            )

    return posiciones


def existe_proximidad(
    texto,
    patrones_a,
    patrones_b,
    distancia_maxima
):

    posiciones_a = posiciones_patrones(
        texto,
        patrones_a
    )

    posiciones_b = posiciones_patrones(
        texto,
        patrones_b
    )

    for posicion_a in posiciones_a:

        for posicion_b in posiciones_b:

            if (
                abs(
                    posicion_a
                    - posicion_b
                )
                <= distancia_maxima
            ):

                return True

    return False


# ==========================================================
# LITERATURA SECUNDARIA
# ==========================================================

def detectar_secundaria(titulo):

    return contiene_alguno(
        normalizar_texto(
            titulo
        ),
        PATRONES_SECUNDARIA
    )


# ==========================================================
# RESULTADO VACÍO
# ==========================================================

def crear_resultado_base():
    """
    Crea siempre la misma estructura de salida.

    Evita errores por campos inexistentes.
    """

    return {

        "decision":
            "",

        "motivo_final":
            "",

        "numero_palabras":
            0,

        "IA_ES_METODO":
            "",

        "IA_ES_METODO_motivo":
            "",

        "IA_ES_METODO_evidencia":
            "",

        "FORENSE_DIGITAL_REAL":
            "",

        "FORENSE_DIGITAL_REAL_motivo":
            "",

        "FORENSE_DIGITAL_REAL_evidencia":
            "",

        "EVIDENCIA_DE_DISPOSITIVO":
            "",

        "EVIDENCIA_DE_DISPOSITIVO_motivo":
            "",

        "EVIDENCIA_DE_DISPOSITIVO_evidencia":
            "",

        "IA_ACTUA_SOBRE_EVIDENCIA":
            "",

        "IA_ACTUA_SOBRE_EVIDENCIA_motivo":
            "",

        "IA_ACTUA_SOBRE_EVIDENCIA_evidencia":
            "",

        "TAREA_OBJETIVO":
            "",

        "TAREA_OBJETIVO_motivo":
            "",

        "TAREA_OBJETIVO_evidencia":
            "",
    }


# ==========================================================
# RELACIÓN IA - EVIDENCIA - TAREA
# ==========================================================

def analizar_relacion(
    titulo,
    palabras,
    abstract
):
    """
    Busca una relación estructurada entre:

    IA + evidencia + tarea.

    Se consideran tres niveles:

    1. Título y palabras clave.
    2. Misma frase del abstract.
    3. Proximidad dentro del abstract.
    """

    texto_central = normalizar_texto(
        f"{titulo} {palabras}"
    )

    # ------------------------------------------------------
    # TÍTULO + PALABRAS CLAVE
    # ------------------------------------------------------

    ia_central = buscar_grupos(
        texto_central,
        PATRONES_IA
    )

    evidencia_central = (
        buscar_grupos(
            texto_central,
            PATRONES_EVIDENCIA_DISPOSITIVO
        )
        +
        buscar_grupos(
            texto_central,
            PATRONES_FORENSES
        )
    )

    tarea_central = buscar_grupos(
        texto_central,
        PATRONES_TAREAS
    )

    if (
        ia_central
        and evidencia_central
        and tarea_central
    ):

        return (
            True,
            "TITULO_PALABRAS_CLAVE"
        )

    # ------------------------------------------------------
    # MISMA FRASE DEL ABSTRACT
    # ------------------------------------------------------

    for frase_original in dividir_frases(
        abstract
    ):

        frase = normalizar_texto(
            frase_original
        )

        ia = buscar_grupos(
            frase,
            PATRONES_IA
        )

        evidencia = (
            buscar_grupos(
                frase,
                PATRONES_EVIDENCIA_DISPOSITIVO
            )
            +
            buscar_grupos(
                frase,
                PATRONES_FORENSES
            )
        )

        tarea = buscar_grupos(
            frase,
            PATRONES_TAREAS
        )

        if (
            ia
            and evidencia
            and tarea
        ):

            return (
                True,
                "MISMA_FRASE_ABSTRACT"
            )

    # ------------------------------------------------------
    # PROXIMIDAD EN ABSTRACT
    # ------------------------------------------------------

    abstract_normalizado = normalizar_texto(
        abstract
    )

    ia_evidencia_directa = existe_proximidad(
        abstract_normalizado,
        PATRONES_IA,
        PATRONES_EVIDENCIA_DISPOSITIVO,
        DISTANCIA_MAXIMA_RELACION
    )

    ia_forense = existe_proximidad(
        abstract_normalizado,
        PATRONES_IA,
        PATRONES_FORENSES,
        DISTANCIA_MAXIMA_RELACION
    )

    ia_tarea = existe_proximidad(
        abstract_normalizado,
        PATRONES_IA,
        PATRONES_TAREAS,
        DISTANCIA_MAXIMA_RELACION
    )

    if (
        (
            ia_evidencia_directa
            or ia_forense
        )
        and ia_tarea
    ):

        return (
            True,
            "PROXIMIDAD_ABSTRACT"
        )

    return (
        False,
        ""
    )


# ==========================================================
# CRITERIO 1 - IA ES MÉTODO
# ==========================================================

def evaluar_ia_es_metodo(
    titulo,
    palabras,
    abstract
):

    texto_total = normalizar_texto(
        f"{titulo} {palabras} {abstract}"
    )

    texto_central = normalizar_texto(
        f"{titulo} {palabras}"
    )

    indicadores_ia = buscar_grupos(
        texto_total,
        PATRONES_IA
    )

    if not indicadores_ia:

        return (
            "NO",
            "No se identifica ninguna técnica de IA.",
            ""
        )

    # ------------------------------------------------------
    # IA COMO OBJETO
    # ------------------------------------------------------

    if contiene_alguno(
        texto_total,
        PATRONES_IA_COMO_OBJETO
    ):

        relacion, _ = analizar_relacion(
            titulo,
            palabras,
            abstract
        )

        if not relacion:

            return (
                "NO",
                (
                    "La IA aparece como objeto de "
                    "investigación y no como método "
                    "de análisis de evidencia."
                ),
                "; ".join(
                    indicadores_ia
                )
            )

    # ------------------------------------------------------
    # IA CENTRAL
    # ------------------------------------------------------

    ia_en_central = buscar_grupos(
        texto_central,
        PATRONES_IA
    )

    if ia_en_central:

        if (
            contiene_alguno(
                texto_central,
                PATRONES_USO_IA
            )
            or buscar_grupos(
                texto_central,
                PATRONES_TAREAS
            )
        ):

            return (
                "SI",
                (
                    "La IA aparece como componente "
                    "metodológico central."
                ),
                "; ".join(
                    ia_en_central
                )
            )

    # ------------------------------------------------------
    # FRASES ABSTRACT
    # ------------------------------------------------------

    for frase_original in dividir_frases(
        abstract
    ):

        frase = normalizar_texto(
            frase_original
        )

        if (
            buscar_grupos(
                frase,
                PATRONES_IA
            )
            and contiene_alguno(
                frase,
                PATRONES_USO_IA
            )
        ):

            return (
                "SI",
                (
                    "Se identifica una frase en la "
                    "que la IA se utiliza como método."
                ),
                frase_original
            )

    return (
        "DUDOSO",
        (
            "Se identifica IA, pero no puede "
            "confirmarse automáticamente que "
            "constituya el método de análisis."
        ),
        "; ".join(
            indicadores_ia
        )
    )


# ==========================================================
# CRITERIO 2 - CONTEXTO FORENSE REAL
# ==========================================================

def evaluar_forense_real(
    titulo,
    palabras,
    abstract
):

    texto_total = normalizar_texto(
        f"{titulo} {palabras} {abstract}"
    )

    texto_central = normalizar_texto(
        f"{titulo} {palabras}"
    )

    indicadores_totales = buscar_grupos(
        texto_total,
        PATRONES_FORENSES
    )

    indicadores_centrales = buscar_grupos(
        texto_central,
        PATRONES_FORENSES
    )

    if indicadores_centrales:

        return (
            "SI",
            (
                "El contexto de análisis forense "
                "digital aparece en título o "
                "palabras clave."
            ),
            "; ".join(
                indicadores_centrales
            )
        )

    if len(
        indicadores_totales
    ) >= 2:

        return (
            "SI",
            (
                "Se identifican varios indicadores "
                "coherentes de análisis forense digital."
            ),
            "; ".join(
                indicadores_totales
            )
        )

    if (
        contiene_alguno(
            texto_central,
            PATRONES_CIBERSEGURIDAD_PREVENTIVA
        )
        and not indicadores_totales
    ):

        return (
            "NO",
            (
                "El objeto central es ciberseguridad "
                "preventiva sin contexto forense."
            ),
            ""
        )

    if (
        contiene_alguno(
            texto_central,
            PATRONES_NO_TECNICOS
        )
        and not indicadores_totales
    ):

        return (
            "NO",
            (
                "El objeto central no corresponde "
                "a análisis técnico forense digital."
            ),
            ""
        )

    if indicadores_totales:

        return (
            "DUDOSO",
            (
                "Existe algún indicador forense, "
                "pero su centralidad no puede "
                "confirmarse."
            ),
            "; ".join(
                indicadores_totales
            )
        )

    return (
        "NO",
        (
            "No se identifica un contexto de "
            "análisis forense digital."
        ),
        ""
    )


# ==========================================================
# CRITERIO 3 - EVIDENCIA DE DISPOSITIVO
# ==========================================================

def evaluar_evidencia_dispositivo(
    titulo,
    palabras,
    abstract,
    estado_forense
):

    texto_total = normalizar_texto(
        f"{titulo} {palabras} {abstract}"
    )

    evidencia_directa = buscar_grupos(
        texto_total,
        PATRONES_EVIDENCIA_DISPOSITIVO
    )

    if evidencia_directa:

        return (
            "SI",
            (
                "Se identifica evidencia procedente "
                "de dispositivos o sistemas digitales."
            ),
            "; ".join(
                evidencia_directa
            )
        )

    # ------------------------------------------------------
    # SUBDOMINIOS QUE IMPLICAN DISPOSITIVO
    # ------------------------------------------------------

    subdominios = buscar_grupos(
        texto_total,
        PATRONES_FORENSES
    )

    subdominios_dispositivo = {

        "MEMORY_FORENSICS",
        "MOBILE_FORENSICS",
        "CLOUD_FORENSICS",
        "IOT_FORENSICS",
        "FILESYSTEM_FORENSICS",
        "ANDROID_FORENSICS",
        "IOS_FORENSICS",
        "DATABASE_FORENSICS",
        "BROWSER_FORENSICS",
        "PDF_FORENSICS",
    }

    encontrados = [
        subdominio
        for subdominio in subdominios
        if subdominio
        in subdominios_dispositivo
    ]

    if encontrados:

        return (
            "SI",
            (
                "El subdominio forense implica "
                "evidencia procedente de un "
                "dispositivo o sistema digital."
            ),
            "; ".join(
                encontrados
            )
        )

    # ------------------------------------------------------
    # EVIDENCIA CONDICIONADA
    # ------------------------------------------------------

    evidencia_condicionada = buscar_grupos(
        texto_total,
        PATRONES_EVIDENCIA_CONDICIONADA
    )

    if evidencia_condicionada:

        if estado_forense == "SI":

            return (
                "DUDOSO",
                (
                    "Existe un objeto digital en "
                    "contexto forense, pero no se "
                    "confirma su correspondencia "
                    "directa con el foco de "
                    "dispositivos o sistemas."
                ),
                "; ".join(
                    evidencia_condicionada
                )
            )

        return (
            "NO",
            (
                "Existe contenido digital, pero "
                "no se confirma como evidencia "
                "procedente de un proceso forense."
            ),
            "; ".join(
                evidencia_condicionada
            )
        )

    return (
        "NO",
        (
            "No se identifica evidencia procedente "
            "de dispositivos o sistemas electrónicos."
        ),
        ""
    )


# ==========================================================
# CRITERIO 4 - IA ACTÚA SOBRE EVIDENCIA
# ==========================================================

def evaluar_ia_sobre_evidencia(
    titulo,
    palabras,
    abstract
):

    relacion, metodo = analizar_relacion(
        titulo,
        palabras,
        abstract
    )

    if relacion:

        return (
            "SI",
            (
                "Se identifica una relación directa "
                "entre IA, evidencia y tarea."
            ),
            metodo
        )

    texto_total = normalizar_texto(
        f"{titulo} {palabras} {abstract}"
    )

    if contiene_alguno(
        texto_total,
        PATRONES_IA_COMO_OBJETO
    ):

        return (
            "NO",
            (
                "La IA aparece como objeto "
                "investigado y no como método "
                "aplicado a la evidencia."
            ),
            ""
        )

    return (
        "DUDOSO",
        (
            "No puede confirmarse automáticamente "
            "que la IA actúe directamente sobre "
            "la evidencia."
        ),
        ""
    )


# ==========================================================
# CRITERIO 5 - TAREA OBJETIVO
# ==========================================================

def evaluar_tarea_objetivo(
    titulo,
    palabras,
    abstract
):

    texto_central = normalizar_texto(
        f"{titulo} {palabras}"
    )

    tareas_centrales = buscar_grupos(
        texto_central,
        PATRONES_TAREAS
    )

    if tareas_centrales:

        return (
            "SI",
            (
                "La tarea objetivo aparece en "
                "título o palabras clave."
            ),
            "; ".join(
                tareas_centrales
            )
        )

    tareas_abstract = buscar_grupos(
        normalizar_texto(
            abstract
        ),
        PATRONES_TAREAS
    )

    if tareas_abstract:

        return (
            "DUDOSO",
            (
                "La tarea objetivo se identifica "
                "únicamente en el abstract."
            ),
            "; ".join(
                tareas_abstract
            )
        )

    if contiene_alguno(
        texto_central,
        PATRONES_TAREAS_NO_OBJETIVO
    ):

        return (
            "NO",
            (
                "La tarea central está fuera "
                "del foco operativo establecido."
            ),
            ""
        )

    texto_total = normalizar_texto(
        f"{titulo} {palabras} {abstract}"
    )

    if (
        len(
            texto_total.split()
        )
        >= MINIMO_PALABRAS_EXCLUSION
    ):

        return (
            "NO",
            (
                "No se identifica ninguna tarea "
                "de detección, identificación, "
                "atribución, clasificación, "
                "filtrado, triage, priorización "
                "o ranking."
            ),
            ""
        )

    return (
        "DUDOSO",
        (
            "La información disponible no "
            "permite determinar la tarea."
        ),
        ""
    )


# ==========================================================
# CLASIFICACIÓN GLOBAL
# ==========================================================

def clasificar_registro(elemento):

    resultado = crear_resultado_base()

    titulo = obtener_titulo(
        elemento
    )

    abstract = obtener_abstract(
        elemento
    )

    palabras = obtener_palabras_clave(
        elemento
    )

    texto_disponible = limpiar_texto(
        f"{titulo} {palabras} {abstract}"
    )

    resultado[
        "numero_palabras"
    ] = len(
        texto_disponible.split()
    )

    # ------------------------------------------------------
    # LITERATURA SECUNDARIA
    # ------------------------------------------------------

    if detectar_secundaria(
        titulo
    ):

        resultado[
            "decision"
        ] = "SECUNDARIA_CONSERVAR"

        resultado[
            "motivo_final"
        ] = (
            "El título identifica una revisión, "
            "survey, overview u otro estudio "
            "de literatura secundaria."
        )

        return resultado

    # ------------------------------------------------------
    # CRITERIO 1
    # ------------------------------------------------------

    (
        estado_ia,
        motivo_ia,
        evidencia_ia
    ) = evaluar_ia_es_metodo(
        titulo,
        palabras,
        abstract
    )

    # ------------------------------------------------------
    # CRITERIO 2
    # ------------------------------------------------------

    (
        estado_forense,
        motivo_forense,
        evidencia_forense
    ) = evaluar_forense_real(
        titulo,
        palabras,
        abstract
    )

    # ------------------------------------------------------
    # CRITERIO 3
    # ------------------------------------------------------

    (
        estado_dispositivo,
        motivo_dispositivo,
        evidencia_dispositivo
    ) = evaluar_evidencia_dispositivo(
        titulo,
        palabras,
        abstract,
        estado_forense
    )

    # ------------------------------------------------------
    # CRITERIO 4
    # ------------------------------------------------------

    (
        estado_relacion,
        motivo_relacion,
        evidencia_relacion
    ) = evaluar_ia_sobre_evidencia(
        titulo,
        palabras,
        abstract
    )

    # ------------------------------------------------------
    # CRITERIO 5
    # ------------------------------------------------------

    (
        estado_tarea,
        motivo_tarea,
        evidencia_tarea
    ) = evaluar_tarea_objetivo(
        titulo,
        palabras,
        abstract
    )

    # ------------------------------------------------------
    # GUARDAR RESULTADOS INDIVIDUALES
    # ------------------------------------------------------

    resultado[
        "IA_ES_METODO"
    ] = estado_ia

    resultado[
        "IA_ES_METODO_motivo"
    ] = motivo_ia

    resultado[
        "IA_ES_METODO_evidencia"
    ] = evidencia_ia

    resultado[
        "FORENSE_DIGITAL_REAL"
    ] = estado_forense

    resultado[
        "FORENSE_DIGITAL_REAL_motivo"
    ] = motivo_forense

    resultado[
        "FORENSE_DIGITAL_REAL_evidencia"
    ] = evidencia_forense

    resultado[
        "EVIDENCIA_DE_DISPOSITIVO"
    ] = estado_dispositivo

    resultado[
        "EVIDENCIA_DE_DISPOSITIVO_motivo"
    ] = motivo_dispositivo

    resultado[
        "EVIDENCIA_DE_DISPOSITIVO_evidencia"
    ] = evidencia_dispositivo

    resultado[
        "IA_ACTUA_SOBRE_EVIDENCIA"
    ] = estado_relacion

    resultado[
        "IA_ACTUA_SOBRE_EVIDENCIA_motivo"
    ] = motivo_relacion

    resultado[
        "IA_ACTUA_SOBRE_EVIDENCIA_evidencia"
    ] = evidencia_relacion

    resultado[
        "TAREA_OBJETIVO"
    ] = estado_tarea

    resultado[
        "TAREA_OBJETIVO_motivo"
    ] = motivo_tarea

    resultado[
        "TAREA_OBJETIVO_evidencia"
    ] = evidencia_tarea

    estados = {

        "IA_ES_METODO":
            estado_ia,

        "FORENSE_DIGITAL_REAL":
            estado_forense,

        "EVIDENCIA_DE_DISPOSITIVO":
            estado_dispositivo,

        "IA_ACTUA_SOBRE_EVIDENCIA":
            estado_relacion,

        "TAREA_OBJETIVO":
            estado_tarea,
    }

    # ------------------------------------------------------
    # CANDIDATO CORPUS PRINCIPAL
    # ------------------------------------------------------

    if all(
        estado == "SI"
        for estado in estados.values()
    ):

        resultado[
            "decision"
        ] = (
            "CANDIDATO_CORPUS_PRINCIPAL"
        )

        resultado[
            "motivo_final"
        ] = (
            "Cumple afirmativamente los cinco "
            "requisitos establecidos para el "
            "corpus principal."
        )

        return resultado

    # ------------------------------------------------------
    # LITERATURA COMPLEMENTARIA
    # ------------------------------------------------------

    if (
        estado_ia == "SI"
        and estado_forense == "SI"
        and estado_relacion == "SI"
        and estado_tarea == "SI"
        and estado_dispositivo != "SI"
    ):

        resultado[
            "decision"
        ] = (
            "LITERATURA_COMPLEMENTARIA"
        )

        resultado[
            "motivo_final"
        ] = (
            "La IA se aplica directamente en "
            "un contexto forense y a una tarea "
            "pertinente, pero no se confirma "
            "que la evidencia responda al foco "
            "principal de dispositivos o "
            "sistemas electrónicos."
        )

        return resultado

    # ------------------------------------------------------
    # CIBERSEGURIDAD PREVENTIVA
    # ------------------------------------------------------

    texto_central = normalizar_texto(
        f"{titulo} {palabras}"
    )

    if (
        estado_forense == "NO"
        and contiene_alguno(
            texto_central,
            PATRONES_CIBERSEGURIDAD_PREVENTIVA
        )
        and resultado[
            "numero_palabras"
        ]
        >= MINIMO_PALABRAS_EXCLUSION
    ):

        resultado[
            "decision"
        ] = (
            "EXCLUIR_ALTA_CONFIANZA"
        )

        resultado[
            "motivo_final"
        ] = (
            "Ciberseguridad preventiva sin "
            "contexto de investigación "
            "forense digital."
        )

        return resultado

    # ------------------------------------------------------
    # DOS REQUISITOS ESENCIALES NEGATIVOS
    # ------------------------------------------------------

    criterios_esenciales = {

        "IA_ES_METODO":
            estado_ia,

        "FORENSE_DIGITAL_REAL":
            estado_forense,

        "IA_ACTUA_SOBRE_EVIDENCIA":
            estado_relacion,

        "TAREA_OBJETIVO":
            estado_tarea,
    }

    negativos = [
        criterio
        for criterio, estado
        in criterios_esenciales.items()
        if estado == "NO"
    ]

    if (
        len(negativos) >= 2
        and resultado[
            "numero_palabras"
        ]
        >= MINIMO_PALABRAS_EXCLUSION
    ):

        resultado[
            "decision"
        ] = (
            "EXCLUIR_ALTA_CONFIANZA"
        )

        resultado[
            "motivo_final"
        ] = (
            "Incumplimiento claro de al menos "
            "dos requisitos esenciales: "
            + "; ".join(
                negativos
            )
        )

        return resultado

    # ------------------------------------------------------
    # SIN FORENSE Y SIN EVIDENCIA DE DISPOSITIVO
    # ------------------------------------------------------

    if (
        estado_dispositivo == "NO"
        and estado_forense == "NO"
        and resultado[
            "numero_palabras"
        ]
        >= MINIMO_PALABRAS_EXCLUSION
    ):

        resultado[
            "decision"
        ] = (
            "EXCLUIR_ALTA_CONFIANZA"
        )

        resultado[
            "motivo_final"
        ] = (
            "No se identifica contexto forense "
            "digital ni evidencia procedente de "
            "dispositivos o sistemas."
        )

        return resultado

    # ------------------------------------------------------
    # REVISIÓN MANUAL
    # ------------------------------------------------------

    criterios_dudosos = [
        criterio
        for criterio, estado
        in estados.items()
        if estado == "DUDOSO"
    ]

    criterios_negativos = [
        criterio
        for criterio, estado
        in estados.items()
        if estado == "NO"
    ]

    resultado[
        "decision"
    ] = "REVISION_MANUAL"

    resultado[
        "motivo_final"
    ] = (
        "La información disponible no permite "
        "adoptar una decisión automática."
    )

    if criterios_dudosos:

        resultado[
            "motivo_final"
        ] += (
            " Criterios dudosos: "
            + "; ".join(
                criterios_dudosos
            )
            + "."
        )

    if criterios_negativos:

        resultado[
            "motivo_final"
        ] += (
            " Criterios negativos: "
            + "; ".join(
                criterios_negativos
            )
            + "."
        )

    return resultado


# ==========================================================
# COLUMNAS CSV
# ==========================================================

COLUMNAS = [

    "tfm_id",
    "titulo",
    "anio",
    "doi",
    "tipo_documental",

    "decision",
    "motivo_final",
    "numero_palabras",

    "IA_ES_METODO",
    "IA_ES_METODO_motivo",
    "IA_ES_METODO_evidencia",

    "FORENSE_DIGITAL_REAL",
    "FORENSE_DIGITAL_REAL_motivo",
    "FORENSE_DIGITAL_REAL_evidencia",

    "EVIDENCIA_DE_DISPOSITIVO",
    "EVIDENCIA_DE_DISPOSITIVO_motivo",
    "EVIDENCIA_DE_DISPOSITIVO_evidencia",

    "IA_ACTUA_SOBRE_EVIDENCIA",
    "IA_ACTUA_SOBRE_EVIDENCIA_motivo",
    "IA_ACTUA_SOBRE_EVIDENCIA_evidencia",

    "TAREA_OBJETIVO",
    "TAREA_OBJETIVO_motivo",
    "TAREA_OBJETIVO_evidencia",

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

    fila = {

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
            resultado.get(
                "decision",
                ""
            ),

        "motivo_final":
            resultado.get(
                "motivo_final",
                ""
            ),

        "numero_palabras":
            resultado.get(
                "numero_palabras",
                0
            ),

        "IA_ES_METODO":
            resultado.get(
                "IA_ES_METODO",
                ""
            ),

        "IA_ES_METODO_motivo":
            resultado.get(
                "IA_ES_METODO_motivo",
                ""
            ),

        "IA_ES_METODO_evidencia":
            resultado.get(
                "IA_ES_METODO_evidencia",
                ""
            ),

        "FORENSE_DIGITAL_REAL":
            resultado.get(
                "FORENSE_DIGITAL_REAL",
                ""
            ),

        "FORENSE_DIGITAL_REAL_motivo":
            resultado.get(
                "FORENSE_DIGITAL_REAL_motivo",
                ""
            ),

        "FORENSE_DIGITAL_REAL_evidencia":
            resultado.get(
                "FORENSE_DIGITAL_REAL_evidencia",
                ""
            ),

        "EVIDENCIA_DE_DISPOSITIVO":
            resultado.get(
                "EVIDENCIA_DE_DISPOSITIVO",
                ""
            ),

        "EVIDENCIA_DE_DISPOSITIVO_motivo":
            resultado.get(
                "EVIDENCIA_DE_DISPOSITIVO_motivo",
                ""
            ),

        "EVIDENCIA_DE_DISPOSITIVO_evidencia":
            resultado.get(
                "EVIDENCIA_DE_DISPOSITIVO_evidencia",
                ""
            ),

        "IA_ACTUA_SOBRE_EVIDENCIA":
            resultado.get(
                "IA_ACTUA_SOBRE_EVIDENCIA",
                ""
            ),

        "IA_ACTUA_SOBRE_EVIDENCIA_motivo":
            resultado.get(
                "IA_ACTUA_SOBRE_EVIDENCIA_motivo",
                ""
            ),

        "IA_ACTUA_SOBRE_EVIDENCIA_evidencia":
            resultado.get(
                "IA_ACTUA_SOBRE_EVIDENCIA_evidencia",
                ""
            ),

        "TAREA_OBJETIVO":
            resultado.get(
                "TAREA_OBJETIVO",
                ""
            ),

        "TAREA_OBJETIVO_motivo":
            resultado.get(
                "TAREA_OBJETIVO_motivo",
                ""
            ),

        "TAREA_OBJETIVO_evidencia":
            resultado.get(
                "TAREA_OBJETIVO_evidencia",
                ""
            ),

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

    return fila


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
        "CRIBADO RELACIONAL FINAL"
    )
    print("=" * 70)

    # ------------------------------------------------------
    # COMPROBACIÓN DEL RDF
    # ------------------------------------------------------

    if not ARCHIVO_RDF_ENTRADA.exists():

        raise FileNotFoundError(
            "No se encuentra el fichero: "
            f"{ARCHIVO_RDF_ENTRADA}"
        )

    DIRECTORIO_SALIDA.mkdir(
        parents=True,
        exist_ok=True
    )

    # ------------------------------------------------------
    # LECTURA DEL RDF
    # ------------------------------------------------------

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
        f"Referencias: "
        f"{len(elementos)}"
    )

    if (
        len(elementos)
        != NUMERO_ESPERADO_REGISTROS
    ):

        raise ValueError(
            "Número de referencias inesperado. "
            f"Esperadas: "
            f"{NUMERO_ESPERADO_REGISTROS}. "
            f"Encontradas: "
            f"{len(elementos)}."
        )

    # ------------------------------------------------------
    # VALIDACIÓN TFM-ID
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
        f"TFM-ID válidos: "
        f"{len(identificadores)}"
    )

    print()
    print(
        "Procesando referencias..."
    )

    # ------------------------------------------------------
    # CLASIFICACIÓN
    # ------------------------------------------------------

    filas = []

    for numero, elemento in enumerate(
        elementos,
        start=1
    ):

        fila = generar_fila(
            elemento
        )

        filas.append(
            fila
        )

        if (
            numero % 250 == 0
            or numero == len(elementos)
        ):

            print(
                f"  Procesadas: "
                f"{numero}/"
                f"{len(elementos)}"
            )

    # ------------------------------------------------------
    # AGRUPACIÓN
    # ------------------------------------------------------

    candidatos = [
        fila
        for fila in filas
        if fila["decision"]
        == "CANDIDATO_CORPUS_PRINCIPAL"
    ]

    complementaria = [
        fila
        for fila in filas
        if fila["decision"]
        == "LITERATURA_COMPLEMENTARIA"
    ]

    revision = [
        fila
        for fila in filas
        if fila["decision"]
        == "REVISION_MANUAL"
    ]

    excluidos = [
        fila
        for fila in filas
        if fila["decision"]
        == "EXCLUIR_ALTA_CONFIANZA"
    ]

    secundaria = [
        fila
        for fila in filas
        if fila["decision"]
        == "SECUNDARIA_CONSERVAR"
    ]

    # ------------------------------------------------------
    # CONTROL DE CONSISTENCIA
    # ------------------------------------------------------

    total_clasificado = (
        len(candidatos)
        + len(complementaria)
        + len(revision)
        + len(excluidos)
        + len(secundaria)
    )

    if (
        total_clasificado
        != len(filas)
    ):

        raise ValueError(
            "La clasificación no cubre "
            "todos los registros."
        )

    # ------------------------------------------------------
    # MUESTRAS DE CONTROL
    # ------------------------------------------------------

    generador_excluidos = random.Random(
        SEMILLA_MUESTRA
    )

    generador_candidatos = random.Random(
        SEMILLA_MUESTRA + 1
    )

    muestra_excluidos = []

    if excluidos:

        muestra_excluidos = (
            generador_excluidos.sample(
                excluidos,
                min(
                    TAMANO_MUESTRA_CONTROL,
                    len(excluidos)
                )
            )
        )

    muestra_candidatos = []

    if candidatos:

        muestra_candidatos = (
            generador_candidatos.sample(
                candidatos,
                min(
                    TAMANO_MUESTRA_CONTROL,
                    len(candidatos)
                )
            )
        )

    # ------------------------------------------------------
    # GENERACIÓN DE ARCHIVOS
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
        complementaria,
        ARCHIVO_COMPLEMENTARIA
    )

    escribir_csv(
        revision,
        ARCHIVO_REVISION
    )

    escribir_csv(
        excluidos,
        ARCHIVO_EXCLUIDOS
    )

    escribir_csv(
        secundaria,
        ARCHIVO_SECUNDARIA
    )

    escribir_csv(
        muestra_excluidos,
        ARCHIVO_MUESTRA_EXCLUIDOS
    )

    escribir_csv(
        muestra_candidatos,
        ARCHIVO_MUESTRA_CANDIDATOS
    )

    # ------------------------------------------------------
    # DISTRIBUCIÓN POR CRITERIO
    # ------------------------------------------------------

    criterios = [

        "IA_ES_METODO",

        "FORENSE_DIGITAL_REAL",

        "EVIDENCIA_DE_DISPOSITIVO",

        "IA_ACTUA_SOBRE_EVIDENCIA",

        "TAREA_OBJETIVO",
    ]

    texto_criterios = ""

    for criterio in criterios:

        contador = Counter(
            fila[criterio]
            for fila in filas
            if fila[criterio]
        )

        texto_criterios += (
            f"\n{criterio}:\n"
            f"  SI: "
            f"{contador.get('SI', 0)}\n"
            f"  DUDOSO: "
            f"{contador.get('DUDOSO', 0)}\n"
            f"  NO: "
            f"{contador.get('NO', 0)}\n"
        )

    # ------------------------------------------------------
    # RESUMEN
    # ------------------------------------------------------

    resumen = (

        "CRIBADO RELACIONAL FINAL\n"
        "============================================\n\n"

        f"Registros analizados: "
        f"{len(filas)}\n\n"

        f"Candidatos corpus principal: "
        f"{len(candidatos)}\n"

        f"Literatura complementaria: "
        f"{len(complementaria)}\n"

        f"Pendientes revisión manual: "
        f"{len(revision)}\n"

        f"Excluidos alta confianza: "
        f"{len(excluidos)}\n"

        f"Literatura secundaria: "
        f"{len(secundaria)}\n\n"

        "Distribución por criterio:\n"

        f"{texto_criterios}\n"
    )

    ARCHIVO_RESUMEN.write_text(
        resumen,
        encoding="utf-8"
    )

    # ------------------------------------------------------
    # SALIDA EN PANTALLA
    # ------------------------------------------------------

    print()
    print(
        "RESULTADO"
    )
    print("=" * 70)

    print(
        f"Registros analizados: "
        f"{len(filas)}"
    )

    print(
        f"Candidatos corpus principal: "
        f"{len(candidatos)}"
    )

    print(
        f"Literatura complementaria: "
        f"{len(complementaria)}"
    )

    print(
        f"Pendientes revisión manual: "
        f"{len(revision)}"
    )

    print(
        f"Excluidos alta confianza: "
        f"{len(excluidos)}"
    )

    print(
        f"Literatura secundaria: "
        f"{len(secundaria)}"
    )

    print()
    print(
        "ARCHIVOS GENERADOS"
    )
    print("=" * 70)

    rutas_generadas = [

        ARCHIVO_RESULTADOS,
        ARCHIVO_CANDIDATOS,
        ARCHIVO_COMPLEMENTARIA,
        ARCHIVO_REVISION,
        ARCHIVO_EXCLUIDOS,
        ARCHIVO_SECUNDARIA,
        ARCHIVO_MUESTRA_EXCLUIDOS,
        ARCHIVO_MUESTRA_CANDIDATOS,
        ARCHIVO_RESUMEN,
    ]

    for ruta in rutas_generadas:

        print(
            ruta
        )


if __name__ == "__main__":
    principal()