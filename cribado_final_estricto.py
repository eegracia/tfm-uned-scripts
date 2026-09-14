#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CRIBADO FINAL ESTRICTO

Entrada procedente del cribado relacional anterior:

1. TFM_relacional_corpus_principal.csv
2. TFM_relacional_revision_manual.csv

Ambos conjuntos se fusionan para que ningún registro
pendiente de decisión desaparezca del flujo de selección.

Cada registro conserva su procedencia mediante:

- origen_fase_anterior
- decision_fase_anterior
- motivo_fase_anterior

Se aplica un cribado final más estricto basado en:

1. Uso de IA como método.
2. Contexto explícito de análisis forense digital.
3. Evidencia digital específica procedente de dispositivos
   o sistemas.
4. Relación explícita entre IA, evidencia y tarea.
5. Tarea alineada con el foco del TFM:
   - detección;
   - identificación;
   - atribución;
   - clasificación;
   - filtrado;
   - triage;
   - priorización;
   - ranking.

Resultados:

- CANDIDATO_TEXTO_COMPLETO
- LITERATURA_COMPLEMENTARIA
- REVISION_MANUAL_FINAL
- EXCLUIR_ALTA_CONFIANZA
- SECUNDARIA_CONSERVAR

El script utiliza exclusivamente librerías estándar
de Python.
"""

from pathlib import Path
from collections import Counter
import csv
import re
import html
import random
import unicodedata


# ==========================================================
# CONFIGURACIÓN
# ==========================================================

DIRECTORIO_FASE_ANTERIOR = Path(
    "cribado_relacional_final"
)

NOMBRE_ARCHIVO_CANDIDATOS_PREVIOS = (
    "TFM_relacional_corpus_principal.csv"
)

NOMBRE_ARCHIVO_REVISION_PREVIA = (
    "TFM_relacional_revision_manual.csv"
)

DIRECTORIO_SALIDA = Path(
    "cribado_final_estricto"
)

ARCHIVO_RESULTADOS = (
    DIRECTORIO_SALIDA
    / "TFM_final_resultados.csv"
)

ARCHIVO_CANDIDATOS = (
    DIRECTORIO_SALIDA
    / "TFM_final_candidatos_texto_completo.csv"
)

ARCHIVO_COMPLEMENTARIA = (
    DIRECTORIO_SALIDA
    / "TFM_final_literatura_complementaria.csv"
)

ARCHIVO_REVISION = (
    DIRECTORIO_SALIDA
    / "TFM_final_revision_manual.csv"
)

ARCHIVO_EXCLUIDOS = (
    DIRECTORIO_SALIDA
    / "TFM_final_excluidos.csv"
)

ARCHIVO_SECUNDARIA = (
    DIRECTORIO_SALIDA
    / "TFM_final_literatura_secundaria.csv"
)

ARCHIVO_MUESTRA_EXCLUIDOS = (
    DIRECTORIO_SALIDA
    / "TFM_final_muestra_excluidos.csv"
)

ARCHIVO_MUESTRA_CANDIDATOS = (
    DIRECTORIO_SALIDA
    / "TFM_final_muestra_candidatos.csv"
)

ARCHIVO_MUESTRA_REVISION = (
    DIRECTORIO_SALIDA
    / "TFM_final_muestra_revision.csv"
)

ARCHIVO_RESUMEN = (
    DIRECTORIO_SALIDA
    / "TFM_final_resumen.txt"
)

# Valores de control correspondientes al estado actual.
NUMERO_ESPERADO_CANDIDATOS_PREVIOS = 268
NUMERO_ESPERADO_REVISION_PREVIA = 1291
NUMERO_ESPERADO_TOTAL = 1559

TAMANO_MUESTRA_CONTROL = 30

SEMILLA_MUESTRA = 2026

MAXIMO_PALABRAS_DOS_FRASES = 100


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
    r"\btaxonomy\b",

    r"\bsystematic mapping\b",
    r"\bmapping study\b",

    r"\bbibliometric analysis\b",
    r"\bbibliometric review\b",

    r"\bstate[- ]of[- ]the[- ]art\b",
    r"\bstate of the art\b",
]


# ==========================================================
# TÉCNICAS DE INTELIGENCIA ARTIFICIAL
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
        r"\bneural networks?\b",

    "CNN":
        (
            r"\bcnn\b|"
            r"\bconvolutional neural networks?\b"
        ),

    "RNN":
        (
            r"\brnn\b|"
            r"\brecurrent neural networks?\b"
        ),

    "LSTM":
        r"\blstm\b",

    "GRU":
        r"\bgru\b",

    "GNN":
        (
            r"\bgnn\b|"
            r"\bgraph neural networks?\b"
        ),

    "TRANSFORMER":
        r"\btransformers?\b",

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
            r"\bgenerative adversarial networks?\b"
        ),

    "AUTOENCODER":
        r"\bautoencoder",

    "VARIATIONAL_AUTOENCODER":
        (
            r"\bvariational autoencoder\b|"
            r"\bvae\b"
        ),

    "DIFFUSION_MODEL":
        r"\bdiffusion models?\b",

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

    "AI_AGENT":
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

    "SUPERVISED":
        r"\bsupervised learning\b",

    "UNSUPERVISED":
        r"\bunsupervised learning\b",

    "REINFORCEMENT":
        r"\breinforcement learning\b",

    "CONTRASTIVE":
        r"\bcontrastive learning\b",

    "REPRESENTATION":
        r"\brepresentation learning\b",

    "FEDERATED":
        r"\bfederated learning\b",

    "ENSEMBLE":
        r"\bensemble learning\b",

    "RANDOM_FOREST":
        r"\brandom forest",

    "SVM":
        (
            r"\bsvm\b|"
            r"\bsupport vector machines?\b"
        ),

    "XGBOOST":
        r"\bxgboost\b",

    "GRADIENT_BOOSTING":
        r"\bgradient boosting\b",

    "DECISION_TREE":
        r"\bdecision trees?\b",

    "KNN":
        (
            r"\bknn\b|"
            r"\bk[- ]?nearest neighbou?r"
        ),

    "KMEANS":
        r"\bk[- ]?means\b",

    "NAIVE_BAYES":
        r"\bnaive bayes\b",

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
        r"\bsiamese (?:neural )?networks?\b",

    "ARTIFICIAL_IMMUNE":
        (
            r"\bartificial immune "
            r"(?:system|intelligence)\b"
        ),
}


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

    "DIGITAL_CRIME_INVESTIGATION":
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

    "POST_INCIDENT":
        r"\bpost[- ]incident\b",

    "EVENT_RECONSTRUCTION":
        r"\bevent reconstruction\b",

    "INCIDENT_RECONSTRUCTION":
        r"\bincident reconstruction\b",

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

    "ANDROID_FORENSICS":
        r"\bandroid forensic",

    "IOS_FORENSICS":
        r"\bios forensic",

    "MULTIMEDIA_FORENSICS":
        r"\bmultimedia forensic",

    "IMAGE_FORENSICS":
        r"\bimage forensic",

    "VIDEO_FORENSICS":
        r"\bvideo forensic",

    "AUDIO_FORENSICS":
        r"\baudio forensic",

    "DOCUMENT_FORENSICS":
        r"\bdocument forensic",

    "PDF_FORENSICS":
        r"\bpdf forensic",

    "ANTI_FORENSICS":
        r"\banti[- ]forensic",
}


# ==========================================================
# EVIDENCIA PRIMARIA
# ==========================================================

PATRONES_EVIDENCIA_PRIMARIA = {

    "FILE_SYSTEM":
        (
            r"\bfile system\b|"
            r"\bfilesystem\b"
        ),

    "FILE_FRAGMENT":
        r"\bfile fragments?\b",

    "FILE_CARVING":
        r"\bfile carving\b",

    "DATA_CARVING":
        r"\bdata carving\b",

    "DELETED_FILES":
        r"\bdeleted (?:files?|data)\b",

    "CORRUPTED_FILE":
        r"\bcorrupted files?\b",

    "STORAGE_MEDIA":
        (
            r"\bstorage media\b|"
            r"\bstorage devices?\b"
        ),

    "DISK_IMAGE":
        r"\bdisk images?\b",

    "MEMORY":
        (
            r"\bmemory dumps?\b|"
            r"\bmemory images?\b|"
            r"\bvolatile memory\b|"
            r"\bram dumps?\b|"
            r"\bmemory artifacts?\b"
        ),

    "WINDOWS_REGISTRY":
        r"\bwindows registry\b",

    "LOGS":
        (
            r"\bevent logs?\b|"
            r"\bsystem logs?\b|"
            r"\bapplication logs?\b|"
            r"\bforensic logs?\b|"
            r"\blog files?\b"
        ),

    "PACKET_CAPTURE":
        (
            r"\bpacket captures?\b|"
            r"\bpcap\b"
        ),

    "MOBILE_ARTIFACT":
        (
            r"\bmobile artifacts?\b|"
            r"\bmobile artefacts?\b|"
            r"\bandroid artifacts?\b|"
            r"\bios artifacts?\b|"
            r"\bsmartphone artifacts?\b"
        ),

    "MOBILE_DEVICE":
        (
            r"\bmobile devices?\b|"
            r"\bsmartphones?\b"
        ),

    "MESSAGES":
        (
            r"\bchat messages?\b|"
            r"\btext messages?\b|"
            r"\bemail messages?\b|"
            r"\bwhatsapp\b"
        ),

    "BROWSER":
        (
            r"\bbrowser history\b|"
            r"\bweb history\b"
        ),

    "APPLICATION_ARTIFACT":
        (
            r"\bapplication artifacts?\b|"
            r"\bapp artifacts?\b"
        ),

    "CLOUD_ARTIFACT":
        (
            r"\bcloud artifacts?\b|"
            r"\bcloud logs?\b"
        ),

    "IOT_ARTIFACT":
        (
            r"\biot artifacts?\b|"
            r"\biot logs?\b|"
            r"\bdevice logs?\b"
        ),

    "PDF":
        (
            r"\bpdf files?\b|"
            r"\bpdf documents?\b|"
            r"\bcorrupted pdf\b"
        ),

    "ELECTRONIC_DEVICE":
        r"\belectronic devices?\b",
}


# ==========================================================
# EVIDENCIA GENÉRICA
# ==========================================================

PATRONES_EVIDENCIA_GENERICA = {

    "DIGITAL_EVIDENCE":
        r"\bdigital evidence\b",

    "ELECTRONIC_EVIDENCE":
        r"\belectronic evidence\b",

    "DIGITAL_ARTIFACT":
        (
            r"\bdigital artifacts?\b|"
            r"\bdigital artefacts?\b"
        ),
}


# ==========================================================
# EVIDENCIA CONDICIONADA / COMPLEMENTARIA
# ==========================================================

PATRONES_EVIDENCIA_CONDICIONADA = {

    "NETWORK_TRAFFIC":
        r"\bnetwork traffic\b",

    "NETWORK_PACKET":
        r"\bnetwork packets?\b",

    "MALWARE":
        (
            r"\bmalware\b|"
            r"\bransomware\b|"
            r"\bmalicious software\b"
        ),

    "IMAGE":
        (
            r"\bdigital images?\b|"
            r"\bimage files?\b"
        ),

    "VIDEO":
        (
            r"\bdigital videos?\b|"
            r"\bvideo files?\b"
        ),

    "AUDIO":
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

    "BLOCKCHAIN":
        (
            r"\bblockchain transactions?\b|"
            r"\btransaction records?\b"
        ),

    "LEGAL_DOCUMENT":
        (
            r"\blegal documents?\b|"
            r"\bjudicial documents?\b"
        ),
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
# VERBOS DE ACCIÓN
# ==========================================================

PATRONES_ACCION = [

    r"\buse(?:d|s|ing)?\b",
    r"\bapply(?:ing|ies|ied)?\b",
    r"\bemploy(?:ed|ing|s)?\b",
    r"\bleverag(?:e|ed|es|ing)\b",
    r"\butili[sz](?:e|ed|es|ing)\b",
    r"\btrain(?:ed|ing|s)?\b",
    r"\bdevelop(?:ed|ing|s)?\b",
    r"\bimplement(?:ed|ing|s)?\b",
    r"\bpropos(?:e|ed|es|ing)\b",
    r"\bprocess(?:es|ed|ing)?\b",
    r"\banaly[sz](?:e|ed|es|ing)\b",
    r"\bclassif(?:y|ies|ied|ication)\b",
    r"\bdetect(?:s|ed|ing|ion)?\b",
    r"\bidentif(?:y|ies|ied|ication)\b",
    r"\bfilter(?:s|ed|ing)?\b",
    r"\bprioriti[sz](?:e|ed|es|ing|ation)\b",
    r"\bextract(?:s|ed|ing|ion)?\b",
]


# ==========================================================
# IA COMO OBJETO, NO COMO MÉTODO
# ==========================================================

PATRONES_IA_COMO_OBJETO = [

    r"\bforensic analysis of "
    r"(?:chatgpt|artificial intelligence|ai systems?)\b",

    r"\bforensic examination of "
    r"(?:chatgpt|artificial intelligence|ai systems?)\b",

    r"\btraces? (?:left|generated|created) by "
    r"(?:ai|chatgpt)",

    r"\bartifacts? (?:left|generated|created) by "
    r"(?:ai|chatgpt)",

    r"\bai application artifacts?\b",

    r"\bchatgpt artifacts?\b",
]


# ==========================================================
# CIBERSEGURIDAD PREVENTIVA
# ==========================================================

PATRONES_PREVENTIVOS = [

    r"\bintrusion detection\b",
    r"\bintrusion detection system\b",
    r"\bnetwork intrusion\b",
    r"\bddos\b",
    r"\bdenial of service\b",
    r"\bphishing detection\b",
    r"\bvulnerability detection\b",
    r"\bvulnerability assessment\b",
    r"\bbotnet detection\b",
    r"\battack prediction\b",
    r"\bthreat prediction\b",
    r"\breal[- ]time threat detection\b",
    r"\bthreat defense\b",
]


# ==========================================================
# OBJETOS FUERA DEL FOCO
# ==========================================================

PATRONES_FUERA_FOCO = [

    r"\bresearch vision\b",
    r"\bvision paper\b",
    r"\bconceptual framework\b",
    r"\broadmap\b",

    r"\blegal implications?\b",
    r"\bethical implications?\b",
    r"\bgovernance\b",

    r"\beducation\b",
    r"\bcurriculum\b",
    r"\btraining program\b",
    r"\btraining programme\b",

    r"\bforensic readiness\b",
    r"\bchain of custody\b",
    r"\bevidence preservation\b",
    r"\bevidence integrity\b",
    r"\bevidence storage\b",

    r"\breport generation\b",
    r"\breport summarization\b",

    r"\btool testing\b",
    r"\bcode testing\b",
]


# ==========================================================
# DOMINIOS COMPLEMENTARIOS
# ==========================================================

PATRONES_DOMINIOS_COMPLEMENTARIOS = {

    "MULTIMEDIA":
        (
            r"\bdeepfake|"
            r"\bimage forgery\b|"
            r"\bvideo forgery\b|"
            r"\bimage manipulation\b|"
            r"\bvideo manipulation\b|"
            r"\bimage tampering\b|"
            r"\bmultimedia\b|"
            r"\bface morphing\b|"
            r"\bvoice cloning\b|"
            r"\baudio spoofing\b"
        ),

    "BIOMETRIA":
        (
            r"\bbiometric|"
            r"\bface recognition\b|"
            r"\bspeaker recognition\b|"
            r"\bsignature verification\b"
        ),

    "AUTORIA":
        (
            r"\bauthorship attribution\b|"
            r"\bauthor identification\b"
        ),

    "LEGAL":
        (
            r"\blegal documents?\b|"
            r"\bjudicial documents?\b|"
            r"\blegal proceedings?\b"
        ),

    "BLOCKCHAIN":
        (
            r"\bblockchain transactions?\b|"
            r"\btransaction graph"
        ),
}


# ==========================================================
# FUNCIONES DE TEXTO
# ==========================================================

def limpiar_texto(texto):

    if texto is None:
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

    texto = re.sub(
        r"\s+",
        " ",
        texto
    )

    return texto.strip()


def normalizar_texto(texto):

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


def dividir_frases(texto):

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
# FUNCIONES DE BÚSQUEDA
# ==========================================================

def buscar_grupos(
    texto,
    patrones
):

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

    return any(
        re.search(
            patron,
            texto,
            re.IGNORECASE
        )
        for patron in patrones
    )


# ==========================================================
# LOCALIZACIÓN DE ARCHIVOS
# ==========================================================

def localizar_archivo(nombre):

    rutas_posibles = [

        DIRECTORIO_FASE_ANTERIOR
        / nombre,

        Path(nombre),
    ]

    for ruta in rutas_posibles:

        if ruta.exists():

            return ruta

    raise FileNotFoundError(
        "No se ha encontrado el archivo "
        f"'{nombre}'. Se ha buscado en:\n"
        f"  - {DIRECTORIO_FASE_ANTERIOR / nombre}\n"
        f"  - {Path(nombre)}"
    )


# ==========================================================
# LECTURA CSV
# ==========================================================

def leer_csv(ruta):

    registros = []

    with ruta.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as archivo:

        lector = csv.DictReader(
            archivo
        )

        for fila in lector:

            registros.append(
                dict(fila)
            )

    return registros


# ==========================================================
# PREPARACIÓN DE LOS DOS GRUPOS
# ==========================================================

def preparar_registros():

    ruta_candidatos = localizar_archivo(
        NOMBRE_ARCHIVO_CANDIDATOS_PREVIOS
    )

    ruta_revision = localizar_archivo(
        NOMBRE_ARCHIVO_REVISION_PREVIA
    )

    candidatos = leer_csv(
        ruta_candidatos
    )

    revision = leer_csv(
        ruta_revision
    )

    for fila in candidatos:

        fila[
            "origen_fase_anterior"
        ] = "CANDIDATO_PREVIO"

        fila[
            "decision_fase_anterior"
        ] = fila.get(
            "decision",
            ""
        )

        fila[
            "motivo_fase_anterior"
        ] = fila.get(
            "motivo_final",
            ""
        )

    for fila in revision:

        fila[
            "origen_fase_anterior"
        ] = "REVISION_MANUAL_PREVIA"

        fila[
            "decision_fase_anterior"
        ] = fila.get(
            "decision",
            ""
        )

        fila[
            "motivo_fase_anterior"
        ] = fila.get(
            "motivo_final",
            ""
        )

    return (
        candidatos,
        revision,
        candidatos + revision,
        ruta_candidatos,
        ruta_revision,
    )


# ==========================================================
# ANÁLISIS DE UNA UNIDAD DE TEXTO
# ==========================================================

def analizar_unidad(
    texto,
    forense_en_titulo=False
):

    texto_normalizado = normalizar_texto(
        texto
    )

    ia = buscar_grupos(
        texto_normalizado,
        PATRONES_IA
    )

    forense = buscar_grupos(
        texto_normalizado,
        PATRONES_FORENSES
    )

    evidencia_primaria = buscar_grupos(
        texto_normalizado,
        PATRONES_EVIDENCIA_PRIMARIA
    )

    evidencia_generica = buscar_grupos(
        texto_normalizado,
        PATRONES_EVIDENCIA_GENERICA
    )

    evidencia_condicionada = buscar_grupos(
        texto_normalizado,
        PATRONES_EVIDENCIA_CONDICIONADA
    )

    tareas = buscar_grupos(
        texto_normalizado,
        PATRONES_TAREAS
    )

    hay_accion = contiene_alguno(
        texto_normalizado,
        PATRONES_ACCION
    )

    ia_como_objeto = contiene_alguno(
        texto_normalizado,
        PATRONES_IA_COMO_OBJETO
    )

    contexto_forense = bool(
        forense
        or forense_en_titulo
    )

    relacion_primaria = bool(
        ia
        and tareas
        and evidencia_primaria
        and hay_accion
        and contexto_forense
        and not ia_como_objeto
    )

    relacion_generica = bool(
        ia
        and tareas
        and evidencia_generica
        and hay_accion
        and contexto_forense
        and not ia_como_objeto
    )

    relacion_condicionada = bool(
        ia
        and tareas
        and evidencia_condicionada
        and hay_accion
        and contexto_forense
        and not ia_como_objeto
    )

    return {

        "ia":
            ia,

        "forense":
            forense,

        "evidencia_primaria":
            evidencia_primaria,

        "evidencia_generica":
            evidencia_generica,

        "evidencia_condicionada":
            evidencia_condicionada,

        "tareas":
            tareas,

        "hay_accion":
            hay_accion,

        "ia_como_objeto":
            ia_como_objeto,

        "relacion_primaria":
            relacion_primaria,

        "relacion_generica":
            relacion_generica,

        "relacion_condicionada":
            relacion_condicionada,
    }


# ==========================================================
# BÚSQUEDA DE RELACIONES
# ==========================================================

def buscar_relaciones(
    titulo,
    abstract
):

    titulo_normalizado = normalizar_texto(
        titulo
    )

    forense_en_titulo = bool(
        buscar_grupos(
            titulo_normalizado,
            PATRONES_FORENSES
        )
    )

    resultado = {

        "relacion_fuerte_primaria":
            False,

        "relacion_fuerte_generica":
            False,

        "relacion_fuerte_condicionada":
            False,

        "relacion_dos_frases_primaria":
            False,

        "relacion_dos_frases_generica":
            False,

        "relacion_dos_frases_condicionada":
            False,

        "fragmento_relacion":
            "",

        "tipo_relacion":
            "",
    }

    # ------------------------------------------------------
    # TÍTULO
    # ------------------------------------------------------

    analisis_titulo = analizar_unidad(
        titulo,
        forense_en_titulo
    )

    if analisis_titulo[
        "relacion_primaria"
    ]:

        resultado[
            "relacion_fuerte_primaria"
        ] = True

        resultado[
            "fragmento_relacion"
        ] = titulo

        resultado[
            "tipo_relacion"
        ] = "TITULO"

        return resultado

    if analisis_titulo[
        "relacion_generica"
    ]:

        resultado[
            "relacion_fuerte_generica"
        ] = True

        resultado[
            "fragmento_relacion"
        ] = titulo

        resultado[
            "tipo_relacion"
        ] = "TITULO_EVIDENCIA_GENERICA"

    if analisis_titulo[
        "relacion_condicionada"
    ]:

        resultado[
            "relacion_fuerte_condicionada"
        ] = True

        resultado[
            "fragmento_relacion"
        ] = titulo

        resultado[
            "tipo_relacion"
        ] = "TITULO_EVIDENCIA_CONDICIONADA"

    # ------------------------------------------------------
    # FRASES DEL ABSTRACT
    # ------------------------------------------------------

    frases = dividir_frases(
        abstract
    )

    for frase in frases:

        analisis = analizar_unidad(
            frase,
            forense_en_titulo
        )

        if analisis[
            "relacion_primaria"
        ]:

            resultado[
                "relacion_fuerte_primaria"
            ] = True

            resultado[
                "fragmento_relacion"
            ] = frase

            resultado[
                "tipo_relacion"
            ] = "MISMA_FRASE_ABSTRACT"

            return resultado

        if (
            analisis[
                "relacion_generica"
            ]
            and not resultado[
                "relacion_fuerte_generica"
            ]
        ):

            resultado[
                "relacion_fuerte_generica"
            ] = True

            resultado[
                "fragmento_relacion"
            ] = frase

            resultado[
                "tipo_relacion"
            ] = "MISMA_FRASE_ABSTRACT_GENERICA"

        if (
            analisis[
                "relacion_condicionada"
            ]
            and not resultado[
                "relacion_fuerte_condicionada"
            ]
        ):

            resultado[
                "relacion_fuerte_condicionada"
            ] = True

            resultado[
                "fragmento_relacion"
            ] = frase

            resultado[
                "tipo_relacion"
            ] = "MISMA_FRASE_ABSTRACT_CONDICIONADA"

    # ------------------------------------------------------
    # DOS FRASES CONSECUTIVAS
    # ------------------------------------------------------

    for indice in range(
        len(frases) - 1
    ):

        texto_dos_frases = (
            frases[indice]
            + " "
            + frases[indice + 1]
        )

        if (
            len(
                texto_dos_frases.split()
            )
            > MAXIMO_PALABRAS_DOS_FRASES
        ):

            continue

        analisis = analizar_unidad(
            texto_dos_frases,
            forense_en_titulo
        )

        if analisis[
            "relacion_primaria"
        ]:

            resultado[
                "relacion_dos_frases_primaria"
            ] = True

            if not resultado[
                "fragmento_relacion"
            ]:

                resultado[
                    "fragmento_relacion"
                ] = texto_dos_frases

                resultado[
                    "tipo_relacion"
                ] = "DOS_FRASES_ABSTRACT"

        elif analisis[
            "relacion_generica"
        ]:

            resultado[
                "relacion_dos_frases_generica"
            ] = True

        elif analisis[
            "relacion_condicionada"
        ]:

            resultado[
                "relacion_dos_frases_condicionada"
            ] = True

    return resultado


# ==========================================================
# CLASIFICACIÓN
# ==========================================================

def clasificar_registro(fila):

    titulo = limpiar_texto(
        fila.get(
            "titulo",
            ""
        )
    )

    palabras_clave = limpiar_texto(
        fila.get(
            "palabras_clave",
            ""
        )
    )

    abstract = limpiar_texto(
        fila.get(
            "abstract",
            ""
        )
    )

    titulo_normalizado = normalizar_texto(
        titulo
    )

    palabras_normalizadas = normalizar_texto(
        palabras_clave
    )

    abstract_normalizado = normalizar_texto(
        abstract
    )

    texto_total = (
        titulo_normalizado
        + " "
        + palabras_normalizadas
        + " "
        + abstract_normalizado
    )

    texto_central = (
        titulo_normalizado
        + " "
        + palabras_normalizadas
    )

    # ------------------------------------------------------
    # LITERATURA SECUNDARIA
    # ------------------------------------------------------

    if contiene_alguno(
        titulo_normalizado,
        PATRONES_SECUNDARIA
    ):

        return {

            "decision_final":
                "SECUNDARIA_CONSERVAR",

            "prioridad_revision":
                "",

            "motivo_final":
                (
                    "El título identifica una revisión, "
                    "survey, overview, taxonomy u otro "
                    "trabajo de literatura secundaria."
                ),

            "forense_fuerte":
                False,

            "ia_metodo":
                False,

            "evidencia_primaria":
                False,

            "tarea_objetivo":
                False,

            "relacion_explicita":
                False,

            "tipo_relacion":
                "",

            "fragmento_relacion":
                "",
        }

    # ------------------------------------------------------
    # INDICADORES
    # ------------------------------------------------------

    ia_total = buscar_grupos(
        texto_total,
        PATRONES_IA
    )

    forense_titulo = buscar_grupos(
        titulo_normalizado,
        PATRONES_FORENSES
    )

    forense_palabras = buscar_grupos(
        palabras_normalizadas,
        PATRONES_FORENSES
    )

    forense_abstract = buscar_grupos(
        abstract_normalizado,
        PATRONES_FORENSES
    )

    evidencia_primaria_total = buscar_grupos(
        texto_total,
        PATRONES_EVIDENCIA_PRIMARIA
    )

    evidencia_generica_total = buscar_grupos(
        texto_total,
        PATRONES_EVIDENCIA_GENERICA
    )

    evidencia_condicionada_total = buscar_grupos(
        texto_total,
        PATRONES_EVIDENCIA_CONDICIONADA
    )

    tareas_total = buscar_grupos(
        texto_total,
        PATRONES_TAREAS
    )

    tareas_centrales = buscar_grupos(
        texto_central,
        PATRONES_TAREAS
    )

    dominios_complementarios = buscar_grupos(
        texto_central,
        PATRONES_DOMINIOS_COMPLEMENTARIOS
    )

    fuera_foco = contiene_alguno(
        titulo_normalizado,
        PATRONES_FUERA_FOCO
    )

    preventivo = contiene_alguno(
        titulo_normalizado,
        PATRONES_PREVENTIVOS
    )

    ia_como_objeto = contiene_alguno(
        texto_total,
        PATRONES_IA_COMO_OBJETO
    )

    relaciones = buscar_relaciones(
        titulo,
        abstract
    )

    relacion_fuerte_primaria = relaciones[
        "relacion_fuerte_primaria"
    ]

    relacion_fuerte_generica = relaciones[
        "relacion_fuerte_generica"
    ]

    relacion_fuerte_condicionada = relaciones[
        "relacion_fuerte_condicionada"
    ]

    relacion_dos_frases_primaria = relaciones[
        "relacion_dos_frases_primaria"
    ]

    relacion_dos_frases_condicionada = relaciones[
        "relacion_dos_frases_condicionada"
    ]

    # ------------------------------------------------------
    # CRITERIOS FINALES
    # ------------------------------------------------------

    forense_fuerte = bool(
        forense_titulo
        or relacion_fuerte_primaria
        or relacion_fuerte_condicionada
    )

    forense_intermedio = bool(
        forense_palabras
        or forense_abstract
    )

    ia_metodo = bool(
        relacion_fuerte_primaria
        or relacion_fuerte_generica
        or relacion_fuerte_condicionada
        or relacion_dos_frases_primaria
    )

    evidencia_primaria = bool(
        evidencia_primaria_total
    )

    tarea_objetivo = bool(
        tareas_centrales
        or relacion_fuerte_primaria
        or relacion_fuerte_condicionada
    )

    relacion_explicita = bool(
        relacion_fuerte_primaria
        or relacion_fuerte_generica
        or relacion_fuerte_condicionada
    )

    # ======================================================
    # EXCLUSIONES DE ALTA CONFIANZA
    # ======================================================

    if (
        ia_como_objeto
        and not relacion_fuerte_primaria
    ):

        return {

            "decision_final":
                "EXCLUIR_ALTA_CONFIANZA",

            "prioridad_revision":
                "",

            "motivo_final":
                (
                    "La IA aparece como objeto investigado "
                    "y no se confirma que actúe como método "
                    "sobre la evidencia."
                ),

            "forense_fuerte":
                forense_fuerte,

            "ia_metodo":
                False,

            "evidencia_primaria":
                evidencia_primaria,

            "tarea_objetivo":
                tarea_objetivo,

            "relacion_explicita":
                relacion_explicita,

            "tipo_relacion":
                relaciones["tipo_relacion"],

            "fragmento_relacion":
                relaciones["fragmento_relacion"],
        }

    if (
        fuera_foco
        and not relacion_fuerte_primaria
    ):

        return {

            "decision_final":
                "EXCLUIR_ALTA_CONFIANZA",

            "prioridad_revision":
                "",

            "motivo_final":
                (
                    "El objeto central está fuera de las "
                    "tareas operativas definidas para el "
                    "corpus principal."
                ),

            "forense_fuerte":
                forense_fuerte,

            "ia_metodo":
                ia_metodo,

            "evidencia_primaria":
                evidencia_primaria,

            "tarea_objetivo":
                tarea_objetivo,

            "relacion_explicita":
                relacion_explicita,

            "tipo_relacion":
                relaciones["tipo_relacion"],

            "fragmento_relacion":
                relaciones["fragmento_relacion"],
        }

    if (
        preventivo
        and not relacion_fuerte_primaria
    ):

        return {

            "decision_final":
                "EXCLUIR_ALTA_CONFIANZA",

            "prioridad_revision":
                "",

            "motivo_final":
                (
                    "El trabajo se centra en ciberseguridad "
                    "preventiva y no se identifica una "
                    "relación explícita entre IA y evidencia "
                    "forense primaria."
                ),

            "forense_fuerte":
                forense_fuerte,

            "ia_metodo":
                ia_metodo,

            "evidencia_primaria":
                evidencia_primaria,

            "tarea_objetivo":
                tarea_objetivo,

            "relacion_explicita":
                relacion_explicita,

            "tipo_relacion":
                relaciones["tipo_relacion"],

            "fragmento_relacion":
                relaciones["fragmento_relacion"],
        }

    if not ia_total:

        return {

            "decision_final":
                "EXCLUIR_ALTA_CONFIANZA",

            "prioridad_revision":
                "",

            "motivo_final":
                (
                    "No se identifica ninguna técnica "
                    "de inteligencia artificial."
                ),

            "forense_fuerte":
                forense_fuerte,

            "ia_metodo":
                False,

            "evidencia_primaria":
                evidencia_primaria,

            "tarea_objetivo":
                tarea_objetivo,

            "relacion_explicita":
                False,

            "tipo_relacion":
                "",

            "fragmento_relacion":
                "",
        }

    if (
        not forense_titulo
        and not forense_palabras
        and not forense_abstract
    ):

        return {

            "decision_final":
                "EXCLUIR_ALTA_CONFIANZA",

            "prioridad_revision":
                "",

            "motivo_final":
                (
                    "No se identifica contexto de "
                    "análisis forense digital."
                ),

            "forense_fuerte":
                False,

            "ia_metodo":
                ia_metodo,

            "evidencia_primaria":
                evidencia_primaria,

            "tarea_objetivo":
                tarea_objetivo,

            "relacion_explicita":
                relacion_explicita,

            "tipo_relacion":
                relaciones["tipo_relacion"],

            "fragmento_relacion":
                relaciones["fragmento_relacion"],
        }

    if not tareas_total:

        return {

            "decision_final":
                "EXCLUIR_ALTA_CONFIANZA",

            "prioridad_revision":
                "",

            "motivo_final":
                (
                    "No se identifica una tarea de "
                    "detección, identificación, atribución, "
                    "clasificación, filtrado, triage o "
                    "priorización."
                ),

            "forense_fuerte":
                forense_fuerte,

            "ia_metodo":
                ia_metodo,

            "evidencia_primaria":
                evidencia_primaria,

            "tarea_objetivo":
                False,

            "relacion_explicita":
                relacion_explicita,

            "tipo_relacion":
                relaciones["tipo_relacion"],

            "fragmento_relacion":
                relaciones["fragmento_relacion"],
        }

    # ======================================================
    # CANDIDATO DIRECTO
    # ======================================================

    if (
        relacion_fuerte_primaria
        and forense_fuerte
        and ia_metodo
        and tarea_objetivo
        and evidencia_primaria
        and not dominios_complementarios
    ):

        return {

            "decision_final":
                "CANDIDATO_TEXTO_COMPLETO",

            "prioridad_revision":
                "",

            "motivo_final":
                (
                    "Existe una relación explícita entre "
                    "una técnica de IA, una tarea objetivo, "
                    "evidencia digital específica y un "
                    "contexto forense."
                ),

            "forense_fuerte":
                True,

            "ia_metodo":
                True,

            "evidencia_primaria":
                True,

            "tarea_objetivo":
                True,

            "relacion_explicita":
                True,

            "tipo_relacion":
                relaciones["tipo_relacion"],

            "fragmento_relacion":
                relaciones["fragmento_relacion"],
        }

    # ======================================================
    # LITERATURA COMPLEMENTARIA
    # ======================================================

    if (
        dominios_complementarios
        and (
            relacion_fuerte_condicionada
            or relacion_fuerte_generica
            or relacion_dos_frases_condicionada
        )
        and (
            forense_fuerte
            or forense_intermedio
        )
    ):

        return {

            "decision_final":
                "LITERATURA_COMPLEMENTARIA",

            "prioridad_revision":
                "",

            "motivo_final":
                (
                    "La publicación relaciona IA y análisis "
                    "forense, pero el objeto pertenece a un "
                    "ámbito complementario respecto al foco "
                    "principal del corpus."
                ),

            "forense_fuerte":
                forense_fuerte,

            "ia_metodo":
                ia_metodo,

            "evidencia_primaria":
                evidencia_primaria,

            "tarea_objetivo":
                tarea_objetivo,

            "relacion_explicita":
                relacion_explicita,

            "tipo_relacion":
                relaciones["tipo_relacion"],

            "fragmento_relacion":
                relaciones["fragmento_relacion"],
        }

    if (
        evidencia_condicionada_total
        and not evidencia_primaria_total
        and (
            forense_fuerte
            or forense_intermedio
        )
        and (
            relacion_fuerte_condicionada
            or relacion_dos_frases_condicionada
        )
    ):

        return {

            "decision_final":
                "LITERATURA_COMPLEMENTARIA",

            "prioridad_revision":
                "",

            "motivo_final":
                (
                    "La evidencia pertenece a un ámbito "
                    "condicionado y no se identifica evidencia "
                    "primaria específica de dispositivo "
                    "o sistema."
                ),

            "forense_fuerte":
                forense_fuerte,

            "ia_metodo":
                ia_metodo,

            "evidencia_primaria":
                False,

            "tarea_objetivo":
                tarea_objetivo,

            "relacion_explicita":
                relacion_explicita,

            "tipo_relacion":
                relaciones["tipo_relacion"],

            "fragmento_relacion":
                relaciones["fragmento_relacion"],
        }

    # ======================================================
    # REVISIÓN MANUAL FINAL
    # ======================================================

    criterios_cumplidos = sum([

        bool(ia_metodo),
        bool(forense_fuerte),
        bool(evidencia_primaria),
        bool(tarea_objetivo),

        bool(
            relacion_fuerte_primaria
            or relacion_dos_frases_primaria
        ),
    ])

    if (
        relacion_dos_frases_primaria
        or criterios_cumplidos >= 4
    ):

        prioridad = "ALTA"

    elif criterios_cumplidos >= 3:

        prioridad = "MEDIA"

    else:

        prioridad = "BAJA"

    motivos_revision = []

    if not ia_metodo:

        motivos_revision.append(
            "no se confirma que la IA sea el método"
        )

    if not forense_fuerte:

        motivos_revision.append(
            "el contexto forense no es suficientemente central"
        )

    if not evidencia_primaria:

        if evidencia_generica_total:

            motivos_revision.append(
                "solo se identifica evidencia digital genérica"
            )

        elif evidencia_condicionada_total:

            motivos_revision.append(
                "solo se identifica evidencia condicionada"
            )

        else:

            motivos_revision.append(
                "no se identifica evidencia primaria específica"
            )

    if not tarea_objetivo:

        motivos_revision.append(
            "la tarea objetivo no es suficientemente central"
        )

    if not relacion_fuerte_primaria:

        if relacion_dos_frases_primaria:

            motivos_revision.append(
                "la relación aparece repartida entre dos frases"
            )

        else:

            motivos_revision.append(
                "no existe relación explícita completa "
                "en una misma unidad textual"
            )

    return {

        "decision_final":
            "REVISION_MANUAL_FINAL",

        "prioridad_revision":
            prioridad,

        "motivo_final":
            "; ".join(
                motivos_revision
            ),

        "forense_fuerte":
            forense_fuerte,

        "ia_metodo":
            ia_metodo,

        "evidencia_primaria":
            evidencia_primaria,

        "tarea_objetivo":
            tarea_objetivo,

        "relacion_explicita":
            relacion_explicita,

        "tipo_relacion":
            relaciones["tipo_relacion"],

        "fragmento_relacion":
            relaciones["fragmento_relacion"],
    }


# ==========================================================
# COLUMNAS DE SALIDA
# ==========================================================

COLUMNAS_SALIDA = [

    "tfm_id",
    "titulo",
    "anio",
    "doi",
    "tipo_documental",

    "origen_fase_anterior",
    "decision_fase_anterior",
    "motivo_fase_anterior",

    "decision_final",
    "prioridad_revision",
    "motivo_final",

    "forense_fuerte",
    "ia_metodo",
    "evidencia_primaria",
    "tarea_objetivo",
    "relacion_explicita",

    "tipo_relacion",
    "fragmento_relacion",

    "palabras_clave",
    "abstract",

    "decision_manual",
    "motivo_manual",
    "observaciones_manual",
]


# ==========================================================
# GENERACIÓN DE FILA
# ==========================================================

def generar_fila_salida(
    fila_original,
    resultado
):

    return {

        "tfm_id":
            fila_original.get(
                "tfm_id",
                ""
            ),

        "titulo":
            fila_original.get(
                "titulo",
                ""
            ),

        "anio":
            fila_original.get(
                "anio",
                ""
            ),

        "doi":
            fila_original.get(
                "doi",
                ""
            ),

        "tipo_documental":
            fila_original.get(
                "tipo_documental",
                ""
            ),

        "origen_fase_anterior":
            fila_original.get(
                "origen_fase_anterior",
                ""
            ),

        "decision_fase_anterior":
            fila_original.get(
                "decision_fase_anterior",
                ""
            ),

        "motivo_fase_anterior":
            fila_original.get(
                "motivo_fase_anterior",
                ""
            ),

        "decision_final":
            resultado.get(
                "decision_final",
                ""
            ),

        "prioridad_revision":
            resultado.get(
                "prioridad_revision",
                ""
            ),

        "motivo_final":
            resultado.get(
                "motivo_final",
                ""
            ),

        "forense_fuerte":
            resultado.get(
                "forense_fuerte",
                False
            ),

        "ia_metodo":
            resultado.get(
                "ia_metodo",
                False
            ),

        "evidencia_primaria":
            resultado.get(
                "evidencia_primaria",
                False
            ),

        "tarea_objetivo":
            resultado.get(
                "tarea_objetivo",
                False
            ),

        "relacion_explicita":
            resultado.get(
                "relacion_explicita",
                False
            ),

        "tipo_relacion":
            resultado.get(
                "tipo_relacion",
                ""
            ),

        "fragmento_relacion":
            resultado.get(
                "fragmento_relacion",
                ""
            ),

        "palabras_clave":
            fila_original.get(
                "palabras_clave",
                ""
            ),

        "abstract":
            fila_original.get(
                "abstract",
                ""
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
            fieldnames=COLUMNAS_SALIDA
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
        "CRIBADO FINAL ESTRICTO"
    )

    print("=" * 70)

    DIRECTORIO_SALIDA.mkdir(
        parents=True,
        exist_ok=True
    )

    (
        candidatos_previos,
        revision_previa,
        registros,
        ruta_candidatos,
        ruta_revision,
    ) = preparar_registros()

    print(
        f"Candidatos fase anterior: "
        f"{len(candidatos_previos)}"
    )

    print(
        f"Revisión manual fase anterior: "
        f"{len(revision_previa)}"
    )

    print(
        f"Total pendiente de resolución: "
        f"{len(registros)}"
    )

    # ------------------------------------------------------
    # CONTROLES DE NÚMERO
    # ------------------------------------------------------

    if (
        len(candidatos_previos)
        != NUMERO_ESPERADO_CANDIDATOS_PREVIOS
    ):

        raise ValueError(
            "El número de candidatos previos "
            "no coincide con el esperado. "
            f"Esperados: "
            f"{NUMERO_ESPERADO_CANDIDATOS_PREVIOS}. "
            f"Encontrados: "
            f"{len(candidatos_previos)}."
        )

    if (
        len(revision_previa)
        != NUMERO_ESPERADO_REVISION_PREVIA
    ):

        raise ValueError(
            "El número de registros de revisión "
            "manual previa no coincide con el esperado. "
            f"Esperados: "
            f"{NUMERO_ESPERADO_REVISION_PREVIA}. "
            f"Encontrados: "
            f"{len(revision_previa)}."
        )

    if (
        len(registros)
        != NUMERO_ESPERADO_TOTAL
    ):

        raise ValueError(
            "El número total de registros pendientes "
            "no coincide con el esperado. "
            f"Esperados: "
            f"{NUMERO_ESPERADO_TOTAL}. "
            f"Encontrados: "
            f"{len(registros)}."
        )

    # ------------------------------------------------------
    # VALIDACIÓN TFM-ID
    # ------------------------------------------------------

    identificadores = [
        fila.get(
            "tfm_id",
            ""
        ).strip().upper()
        for fila in registros
    ]

    sin_identificador = [
        identificador
        for identificador in identificadores
        if not identificador
    ]

    if sin_identificador:

        raise ValueError(
            "Existen registros sin TFM-ID."
        )

    contador_identificadores = Counter(
        identificadores
    )

    duplicados = [
        identificador
        for identificador, cantidad
        in contador_identificadores.items()
        if cantidad > 1
    ]

    if duplicados:

        raise ValueError(
            "Existen TFM-ID duplicados entre "
            "los dos ficheros de entrada. "
            f"Duplicados detectados: "
            f"{len(duplicados)}."
        )

    print(
        f"TFM-ID válidos y únicos: "
        f"{len(identificadores)}"
    )

    print()
    print(
        "Procesando..."
    )

    # ------------------------------------------------------
    # CLASIFICACIÓN
    # ------------------------------------------------------

    filas_salida = []

    for numero, fila in enumerate(
        registros,
        start=1
    ):

        resultado = clasificar_registro(
            fila
        )

        fila_salida = generar_fila_salida(
            fila,
            resultado
        )

        filas_salida.append(
            fila_salida
        )

        if (
            numero % 100 == 0
            or numero == len(registros)
        ):

            print(
                f"  Procesados: "
                f"{numero}/"
                f"{len(registros)}"
            )

    # ------------------------------------------------------
    # AGRUPACIÓN
    # ------------------------------------------------------

    candidatos = [
        fila
        for fila in filas_salida
        if fila[
            "decision_final"
        ]
        == "CANDIDATO_TEXTO_COMPLETO"
    ]

    complementaria = [
        fila
        for fila in filas_salida
        if fila[
            "decision_final"
        ]
        == "LITERATURA_COMPLEMENTARIA"
    ]

    revision = [
        fila
        for fila in filas_salida
        if fila[
            "decision_final"
        ]
        == "REVISION_MANUAL_FINAL"
    ]

    excluidos = [
        fila
        for fila in filas_salida
        if fila[
            "decision_final"
        ]
        == "EXCLUIR_ALTA_CONFIANZA"
    ]

    secundaria = [
        fila
        for fila in filas_salida
        if fila[
            "decision_final"
        ]
        == "SECUNDARIA_CONSERVAR"
    ]

    # ------------------------------------------------------
    # CONTROL DE SUMA
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
        != len(registros)
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

    generador_revision = random.Random(
        SEMILLA_MUESTRA + 2
    )

    muestra_excluidos = (
        generador_excluidos.sample(
            excluidos,
            min(
                TAMANO_MUESTRA_CONTROL,
                len(excluidos)
            )
        )
        if excluidos
        else []
    )

    muestra_candidatos = (
        generador_candidatos.sample(
            candidatos,
            min(
                TAMANO_MUESTRA_CONTROL,
                len(candidatos)
            )
        )
        if candidatos
        else []
    )

    muestra_revision = (
        generador_revision.sample(
            revision,
            min(
                TAMANO_MUESTRA_CONTROL,
                len(revision)
            )
        )
        if revision
        else []
    )

    # ------------------------------------------------------
    # ESCRITURA DE ARCHIVOS
    # ------------------------------------------------------

    escribir_csv(
        filas_salida,
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

    escribir_csv(
        muestra_revision,
        ARCHIVO_MUESTRA_REVISION
    )

    # ------------------------------------------------------
    # DISTRIBUCIÓN DE LA REVISIÓN MANUAL
    # ------------------------------------------------------

    contador_prioridad = Counter(
        fila[
            "prioridad_revision"
        ]
        for fila in revision
    )

    # ------------------------------------------------------
    # RESULTADO SEGÚN ORIGEN
    # ------------------------------------------------------

    contador_origen_decision = Counter(
        (
            fila[
                "origen_fase_anterior"
            ],
            fila[
                "decision_final"
            ]
        )
        for fila in filas_salida
    )

    texto_origen = ""

    for origen in [
        "CANDIDATO_PREVIO",
        "REVISION_MANUAL_PREVIA",
    ]:

        texto_origen += (
            f"\n{origen}:\n"
        )

        for decision in [

            "CANDIDATO_TEXTO_COMPLETO",
            "LITERATURA_COMPLEMENTARIA",
            "REVISION_MANUAL_FINAL",
            "EXCLUIR_ALTA_CONFIANZA",
            "SECUNDARIA_CONSERVAR",
        ]:

            texto_origen += (
                f"  {decision}: "
                f"{contador_origen_decision.get(
                    (origen, decision),
                    0
                )}\n"
            )

    # ------------------------------------------------------
    # MOTIVOS DE EXCLUSIÓN
    # ------------------------------------------------------

    contador_exclusiones = Counter(
        fila[
            "motivo_final"
        ]
        for fila in excluidos
    )

    texto_exclusiones = "\n".join(
        f"  {motivo}: {cantidad}"
        for motivo, cantidad
        in contador_exclusiones.most_common()
    )

    # ------------------------------------------------------
    # RESUMEN
    # ------------------------------------------------------

    resumen = (

        "CRIBADO FINAL ESTRICTO\n"
        "============================================\n\n"

        f"Archivo candidatos previos: "
        f"{ruta_candidatos}\n"

        f"Archivo revisión previa: "
        f"{ruta_revision}\n\n"

        f"Candidatos fase anterior: "
        f"{len(candidatos_previos)}\n"

        f"Revisión manual fase anterior: "
        f"{len(revision_previa)}\n"

        f"Total analizado en esta fase: "
        f"{len(registros)}\n\n"

        f"Candidatos a texto completo: "
        f"{len(candidatos)}\n"

        f"Literatura complementaria: "
        f"{len(complementaria)}\n"

        f"Pendientes de revisión manual final: "
        f"{len(revision)}\n"

        f"Excluidos con alta confianza: "
        f"{len(excluidos)}\n"

        f"Literatura secundaria: "
        f"{len(secundaria)}\n\n"

        "Prioridad de revisión manual final:\n"

        f"  ALTA: "
        f"{contador_prioridad.get('ALTA', 0)}\n"

        f"  MEDIA: "
        f"{contador_prioridad.get('MEDIA', 0)}\n"

        f"  BAJA: "
        f"{contador_prioridad.get('BAJA', 0)}\n\n"

        "Distribución según origen de la fase anterior:\n"

        f"{texto_origen}\n"

        "Motivos de exclusión:\n"

        f"{texto_exclusiones}\n"
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
        f"{len(registros)}"
    )

    print(
        f"Candidatos a texto completo: "
        f"{len(candidatos)}"
    )

    print(
        f"Literatura complementaria: "
        f"{len(complementaria)}"
    )

    print(
        f"Revisión manual final: "
        f"{len(revision)}"
    )

    print(
        f"Excluidos: "
        f"{len(excluidos)}"
    )

    print(
        f"Literatura secundaria: "
        f"{len(secundaria)}"
    )

    print()

    print(
        "REVISIÓN MANUAL FINAL"
    )

    print("=" * 70)

    print(
        f"Prioridad ALTA: "
        f"{contador_prioridad.get('ALTA', 0)}"
    )

    print(
        f"Prioridad MEDIA: "
        f"{contador_prioridad.get('MEDIA', 0)}"
    )

    print(
        f"Prioridad BAJA: "
        f"{contador_prioridad.get('BAJA', 0)}"
    )

    print()

    print(
        "ARCHIVOS GENERADOS"
    )

    print("=" * 70)

    rutas = [

        ARCHIVO_RESULTADOS,
        ARCHIVO_CANDIDATOS,
        ARCHIVO_COMPLEMENTARIA,
        ARCHIVO_REVISION,
        ARCHIVO_EXCLUIDOS,
        ARCHIVO_SECUNDARIA,
        ARCHIVO_MUESTRA_EXCLUIDOS,
        ARCHIVO_MUESTRA_CANDIDATOS,
        ARCHIVO_MUESTRA_REVISION,
        ARCHIVO_RESUMEN,
    ]

    for ruta in rutas:

        print(
            ruta
        )


if __name__ == "__main__":
    principal()