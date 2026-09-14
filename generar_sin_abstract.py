#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Generación del fichero de registros sin abstract
Revisión sistemática PRISMA / PRISMA-S

Funciones principales:
1. Lee el fichero RIS maestro consolidado.
2. Identifica los registros que no contienen abstract.
3. Distingue entre:
   - registros sin abstract y sin palabras clave;
   - registros sin abstract pero con palabras clave.
4. Genera un fichero CSV con los datos necesarios
   para realizar posteriormente el enriquecimiento
   de metadatos.

El fichero generado contiene:
- identificador interno;
- título;
- autores;
- año;
- DOI;
- fuente o fuentes de procedencia.
"""

from pathlib import Path
import csv
import re


# ==========================================================
# CONFIGURACIÓN
# ==========================================================

ARCHIVO_RIS_MAESTRO = Path(
    "ris_normalizados/TFM_bibliografia_consolidada.ris"
)

ARCHIVO_CSV_SALIDA = Path(
    "ris_normalizados/TFM_registros_sin_abstract.csv"
)


# ==========================================================
# LECTURA DEL FICHERO RIS
# ==========================================================

def leer_ris(ruta):
    """
    Lee un fichero RIS y devuelve una lista de registros.

    Cada registro se almacena como un diccionario:
        etiqueta RIS -> lista de valores
    """

    registros = []
    registro_actual = {}
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

                # Inicio de un nuevo registro
                if etiqueta == "TY" and registro_actual:

                    registros.append(
                        registro_actual
                    )

                    registro_actual = {}

                registro_actual.setdefault(
                    etiqueta,
                    []
                ).append(valor)

                ultima_etiqueta = etiqueta

                # Fin del registro
                if etiqueta == "ER":

                    registros.append(
                        registro_actual
                    )

                    registro_actual = {}
                    ultima_etiqueta = None

            elif ultima_etiqueta and linea.strip():

                # Continuación de un campo multilínea
                registro_actual[
                    ultima_etiqueta
                ][-1] += (
                    " " + linea.strip()
                )

    # Por seguridad, si queda un registro sin ER
    if registro_actual:

        registros.append(
            registro_actual
        )

    return registros


# ==========================================================
# FUNCIONES AUXILIARES
# ==========================================================

def obtener_primer_valor(registro, *etiquetas):
    """
    Devuelve el primer valor no vacío encontrado
    entre las etiquetas RIS indicadas.
    """

    for etiqueta in etiquetas:

        valores = registro.get(
            etiqueta,
            []
        )

        if valores:

            valor = valores[0].strip()

            if valor:
                return valor

    return ""


def obtener_autores(registro):
    """
    Obtiene todos los autores del registro y los devuelve
    separados mediante punto y coma.
    """

    autores = (
        registro.get("AU")
        or registro.get("A1")
        or []
    )

    autores_limpios = [
        autor.strip()
        for autor in autores
        if autor.strip()
    ]

    return "; ".join(
        autores_limpios
    )


def tiene_palabras_clave(registro):
    """
    Comprueba si el registro contiene alguna palabra clave
    en los campos RIS KW o K1.
    """

    palabras_clave = (
        registro.get("KW")
        or registro.get("K1")
        or []
    )

    return any(
        palabra.strip()
        for palabra in palabras_clave
    )


# ==========================================================
# IDENTIFICACIÓN DE REGISTROS SIN ABSTRACT
# ==========================================================

def obtener_registros_sin_abstract(registros):
    """
    Selecciona los registros que carecen de abstract.

    Se consideran los campos:
        AB = Abstract
        N2 = Abstract alternativo utilizado por algunos RIS
    """

    registros_sin_abstract = []

    contador_sin_abstract_sin_palabras_clave = 0
    contador_sin_abstract_con_palabras_clave = 0

    for registro in registros:

        abstract = obtener_primer_valor(
            registro,
            "AB",
            "N2"
        )

        if not abstract:

            if tiene_palabras_clave(registro):

                contador_sin_abstract_con_palabras_clave += 1

            else:

                contador_sin_abstract_sin_palabras_clave += 1

            registros_sin_abstract.append({
                "identificador_interno":
                    obtener_primer_valor(
                        registro,
                        "ID"
                    ),

                "titulo":
                    obtener_primer_valor(
                        registro,
                        "TI",
                        "T1",
                        "CT"
                    ),

                "autores":
                    obtener_autores(
                        registro
                    ),

                "anio":
                    obtener_primer_valor(
                        registro,
                        "PY",
                        "Y1",
                        "DA"
                    ),

                "doi":
                    obtener_primer_valor(
                        registro,
                        "DO"
                    ),

                "fuente_procedencia":
                    obtener_primer_valor(
                        registro,
                        "DB"
                    ),
            })

    return (
        registros_sin_abstract,
        contador_sin_abstract_sin_palabras_clave,
        contador_sin_abstract_con_palabras_clave
    )


# ==========================================================
# ESCRITURA DEL FICHERO CSV
# ==========================================================

def escribir_csv(registros, ruta):
    """
    Genera el fichero CSV de registros sin abstract.

    Se utiliza UTF-8 con BOM para facilitar su apertura
    directa en Microsoft Excel bajo Windows.
    """

    campos = [
        "identificador_interno",
        "titulo",
        "autores",
        "anio",
        "doi",
        "fuente_procedencia",
    ]

    with ruta.open(
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as archivo:

        escritor = csv.DictWriter(
            archivo,
            fieldnames=campos
        )

        escritor.writeheader()

        escritor.writerows(
            registros
        )


# ==========================================================
# PROCESO PRINCIPAL
# ==========================================================

def principal():

    print()
    print("IDENTIFICACIÓN DE REGISTROS SIN ABSTRACT")
    print("=" * 60)

    # Comprueba que exista el fichero maestro
    if not ARCHIVO_RIS_MAESTRO.exists():

        print(
            "ERROR: No se encuentra el fichero:"
        )

        print(
            ARCHIVO_RIS_MAESTRO.resolve()
        )

        return

    # Lectura del RIS maestro
    registros = leer_ris(
        ARCHIVO_RIS_MAESTRO
    )

    print(
        f"Registros del fichero maestro: "
        f"{len(registros)}"
    )

    # Identificación de registros sin abstract
    (
        registros_sin_abstract,
        sin_abstract_sin_palabras_clave,
        sin_abstract_con_palabras_clave
    ) = obtener_registros_sin_abstract(
        registros
    )

    # Generación del CSV
    escribir_csv(
        registros_sin_abstract,
        ARCHIVO_CSV_SALIDA
    )

    print()
    print("RESULTADOS")
    print("=" * 60)

    print(
        f"Registros sin abstract: "
        f"{len(registros_sin_abstract)}"
    )

    print(
        f"Sin abstract y sin palabras clave: "
        f"{sin_abstract_sin_palabras_clave}"
    )

    print(
        f"Sin abstract pero con palabras clave: "
        f"{sin_abstract_con_palabras_clave}"
    )

    print()
    print("ARCHIVO GENERADO")
    print("=" * 60)

    print(
        ARCHIVO_CSV_SALIDA
    )


if __name__ == "__main__":
    principal()