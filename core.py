"""Reglas de negocio de AQUARIA, adaptadas del cuaderno AQUARIA_CHATGPT_V03.
No depende de Streamlit ni requiere clave para ejecutar pruebas unitarias.
"""
from __future__ import annotations

from difflib import SequenceMatcher
from datetime import datetime, timezone
import math
import random
import re
import unicodedata
from uuid import uuid4

TURNOS_POR_PARTIDA = 10
PUNTOS_POR_ACIERTO = 10
PORCENTAJE_APORTE = 0.60
VERSION = '3.0-IA-Web'
MODELO = 'gpt-4.1-mini'
TEMPERATURA = 0.8
MAX_TOKENS_SALIDA = 4000
TIMEOUT_API_S = 60

INSTRUCCIONES_IA = """Eres un educador de conservación marina. Genera exactamente
10 preguntas originales y variadas en español para un juego introductorio del
ODS 14, Vida submarina. Cubre contaminación, microplásticos, biodiversidad,
arrecifes, pesca sostenible y acciones de protección. Cada ítem contiene una
pregunta breve, tres opciones distintas de hasta 90 caracteres, exactamente
una respuesta correcta (copiada literalmente de una opción) y una frase
educativa de hasta 240 caracteres que explique la solución y su relación con
la conservación marina. Las preguntas deben tener hasta 220 caracteres.
Usa hechos consolidados; evita cifras actuales, generalizaciones falsas,
ambigüedades y tecnicismos innecesarios. Incluye dos distractores plausibles
pero claramente incorrectos. No uses todas/ninguna de las anteriores ni
referencias A/B/C. No repitas preguntas ni reformules el mismo conocimiento.
Revisa mentalmente la exactitud y que haya solo una opción correcta antes
de devolver el JSON. No incluyas explicaciones fuera del JSON."""

ESQUEMA_CUESTIONARIO = {
    'type': 'object', 'additionalProperties': False,
    'properties': {'preguntas': {
        'type': 'array', 'minItems': 10, 'maxItems': 10,
        'items': {'type': 'object', 'additionalProperties': False,
                  'properties': {
                      'pregunta': {'type': 'string'},
                      'opciones': {'type': 'array', 'items': {'type': 'string'}, 'minItems': 3, 'maxItems': 3},
                      'respuesta_correcta': {'type': 'string'},
                      'frase_educativa': {'type': 'string'},
                  },
                  'required': ['pregunta', 'opciones', 'respuesta_correcta', 'frase_educativa']},
    }},
    'required': ['preguntas'],
}

TIPOS = ('Práctica', 'Piloto', 'Prueba técnica')
REGISTROS = {
    'generaciones.csv': ('id_generacion', 'fecha_utc', 'id_partida', 'modelo', 'estado', 'tiempo_api_s', 'tiempo_total_s', 'tokens_entrada', 'tokens_salida', 'error_tipo'),
    'inicios.csv': ('id', 'fecha_utc', 'codigo', 'tipo', 'version'),
    'respuestas.csv': ('id', 'fecha_utc', 'turno', 'pregunta', 'opciones', 'elegido', 'respuesta_correcta', 'frase_educativa', 'correcto', 'proceso_ms'),
    'partidas.csv': ('id', 'fecha_utc', 'codigo', 'tipo', 'estado', 'respuestas', 'aciertos', 'puntaje', 'duracion_s'),
    'aportes.csv': ('fecha_utc', 'ingresos', 'reembolsos', 'comisiones', 'elegible', 'aporte_estimado', 'transferido', 'simulado'),
    'arranques.csv': ('fecha_utc', 'version', 'inicio_s'),
}


def fecha():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def normalizar(texto_original: str) -> str:
    texto_normal = unicodedata.normalize('NFKD', texto_original.casefold())
    return ' '.join(re.sub(r'[^a-z0-9 ]', ' ', ''.join(
        c for c in texto_normal if not unicodedata.combining(c))).split())


def validar_codigo(codigo: str) -> bool:
    return 1 <= len(codigo) <= 20 and all(c.isalnum() or c in '_-' for c in codigo)


def validar_cuestionario(datos: dict, rng=None):
    """Valida estructura y similitud textual, no exactitud científica."""
    if not isinstance(datos, dict) or set(datos) != {'preguntas'}:
        raise ValueError('La IA no entregó la estructura de cuestionario esperada.')
    preguntas = datos['preguntas']
    if not isinstance(preguntas, list) or len(preguntas) != TURNOS_POR_PARTIDA:
        raise ValueError('Se requieren exactamente diez preguntas válidas.')
    vistos = []
    campos = {'pregunta', 'opciones', 'respuesta_correcta', 'frase_educativa'}
    for item in preguntas:
        if not isinstance(item, dict) or set(item) != campos:
            raise ValueError('Una pregunta tiene campos incompletos o inesperados.')
        for campo, limite in [('pregunta', 220), ('respuesta_correcta', 90), ('frase_educativa', 240)]:
            valor = item[campo]
            if not isinstance(valor, str) or not valor.strip() or len(valor) > limite:
                raise ValueError('Hay textos vacíos, demasiado largos o inválidos.')
        opciones = item['opciones']
        if not isinstance(opciones, list) or len(opciones) != 3 or any(
                not isinstance(o, str) or not o.strip() or len(o) > 90 for o in opciones):
            raise ValueError('Cada pregunta debe tener tres opciones breves y no vacías.')
        if len({normalizar(o) for o in opciones}) != 3 or any(not normalizar(o) for o in opciones):
            raise ValueError('Una pregunta contiene opciones repetidas o inválidas.')
        if opciones.count(item['respuesta_correcta']) != 1:
            raise ValueError('La respuesta correcta debe coincidir exactamente con una opción.')
        titulo = normalizar(item['pregunta'])
        if not titulo or any(SequenceMatcher(None, titulo, previo).ratio() >= .90 for previo in vistos):
            raise ValueError('La IA entregó preguntas repetidas o demasiado similares.')
        vistos.append(titulo)
    resultado = [{**p, 'opciones': list(p['opciones'])} for p in preguntas]
    rng = rng or random.SystemRandom()
    rng.shuffle(resultado)
    for item in resultado:
        rng.shuffle(item['opciones'])
    return resultado


def calcular_aporte(ingresos, reembolsos, comisiones):
    valores = (ingresos, reembolsos, comisiones)
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0 for v in valores):
        raise ValueError('Los valores deben ser números no negativos.')
    elegible = ingresos - reembolsos - comisiones
    if elegible < 0:
        raise ValueError('Las deducciones no pueden superar los ingresos.')
    return elegible, round(elegible * PORCENTAJE_APORTE, 2)


def resumen_kpi(registros):
    """Preserva el criterio del notebook: primer piloto por código y seis indicadores."""
    inicios = registros.get('inicios.csv', [])
    finales = {r['id']: r for r in registros.get('partidas.csv', [])}
    respuestas = registros.get('respuestas.csv', [])
    primeros = {}
    for r in inicios:
        if r['tipo'] == 'Piloto' and r['codigo'] not in primeros:
            primeros[r['codigo']] = r
    ids_piloto = {r['id'] for r in primeros.values()}
    terminadas = sum(finales.get(i, {}).get('estado') == 'completada' for i in ids_piloto)
    rp = [r for r in respuestas if r['id'] in ids_piloto]
    tecnicas = [r['id'] for r in inicios if r['tipo'] == 'Prueba técnica']
    rt = [float(r['proceso_ms']) for r in respuestas if r['id'] in tecnicas]
    arranques = [float(r['inicio_s']) for r in registros.get('arranques.csv', [])]
    aportes = registros.get('aportes.csv', [])
    sin_cierre = sum(i not in finales for i in tecnicas)
    abandonos = sum(finales.get(i, {}).get('estado') == 'abandonada' for i in tecnicas)
    completas = sum(finales.get(i, {}).get('estado') == 'completada' for i in tecnicas)
    pct = lambda a, n: f'{100*a/n:.1f} % (n={n})' if n else 'No calculable'
    promedio = lambda datos, unidad: f'{sum(datos)/len(datos):.4f} {unidad} (n={len(datos)})' if datos else 'No calculable'
    estabilidad = pct(completas, len(tecnicas)-abandonos)
    if sin_cierre:
        estabilidad = f'Pendiente: revisar {sin_cierre} intento(s) sin cierre'
    return [
        ('1 Tasa de finalización (piloto)', pct(terminadas, len(ids_piloto))),
        ('2 Porcentaje de aciertos (piloto)', pct(sum(int(r['correcto']) for r in rp), len(rp))),
        ('3 Último aporte simulado', f'{float(aportes[-1]["aporte_estimado"]):,.2f} COP' if aportes else 'Sin simulaciones'),
        ('4 Inicio medio de interfaz web (adaptado)', promedio(arranques, 's')),
        ('5 Procesamiento medio de respuestas técnicas', promedio(rt, 'ms')),
        ('6 Estabilidad técnica registrada', estabilidad),
    ]


def nuevo_id():
    return str(uuid4())
