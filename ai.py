"""Conector OpenAI: una petición por partida, sin claves en el repositorio."""
from __future__ import annotations
import json
from time import perf_counter
from uuid import uuid4
from openai import (OpenAI, AuthenticationError, PermissionDeniedError, RateLimitError,
                    APITimeoutError, APIConnectionError, BadRequestError, NotFoundError, APIStatusError)
from core import (MODELO, TEMPERATURA, MAX_TOKENS_SALIDA, TIMEOUT_API_S,
                  INSTRUCCIONES_IA, ESQUEMA_CUESTIONARIO, validar_cuestionario)


def generar_preguntas(clave: str, registro: dict):
    cliente = OpenAI(api_key=clave, max_retries=0, timeout=TIMEOUT_API_S)
    t0 = perf_counter()
    try:
        respuesta = cliente.chat.completions.create(
            model=MODELO, temperature=TEMPERATURA,
            max_completion_tokens=MAX_TOKENS_SALIDA, store=False,
            messages=[
                {'role': 'system', 'content': INSTRUCCIONES_IA},
                {'role': 'user', 'content': 'Crea un cuestionario nuevo y diverso. Variante: ' + str(uuid4())},
            ],
            response_format={'type': 'json_schema', 'json_schema': {
                'name': 'cuestionario_ods14', 'strict': True,
                'schema': ESQUEMA_CUESTIONARIO,
            }},
        )
    finally:
        registro['tiempo_api_s'] = round(perf_counter() - t0, 3)
        cliente.close()
    registro['modelo'] = respuesta.model
    if respuesta.usage:
        registro['tokens_entrada'] = respuesta.usage.prompt_tokens
        registro['tokens_salida'] = respuesta.usage.completion_tokens
    if not respuesta.choices:
        raise ValueError('La API no devolvió preguntas.')
    opcion = respuesta.choices[0]
    if opcion.message.refusal:
        raise ValueError('La IA rechazó la generación. No se inició una partida.')
    if opcion.finish_reason != 'stop' or not opcion.message.content:
        raise ValueError('La respuesta de la IA está incompleta. No se inició una partida.')
    try:
        datos = json.loads(opcion.message.content)
    except (ValueError, TypeError):
        raise ValueError('La IA no devolvió un JSON válido.') from None
    return validar_cuestionario(datos)


def mensaje_error_ia(error):
    if isinstance(error, AuthenticationError):
        return 'La API no está autorizada. El administrador debe revisar la clave del servidor.'
    if isinstance(error, PermissionDeniedError):
        return 'La configuración del servidor no tiene permiso para usar este modelo.'
    if isinstance(error, RateLimitError):
        return ('Se agotó la cuota disponible de la API.' if getattr(error, 'code', '') == 'insufficient_quota'
                else 'Se alcanzó un límite de solicitudes de OpenAI. Inténtalo más tarde.')
    if isinstance(error, APITimeoutError):
        return 'La solicitud agotó el tiempo de espera. No se reintenta automáticamente.'
    if isinstance(error, APIConnectionError):
        return 'No fue posible conectar con OpenAI. Vuelve a intentarlo más tarde.'
    if isinstance(error, (BadRequestError, NotFoundError)):
        return 'El administrador debe revisar el modelo y la configuración de la API.'
    if isinstance(error, APIStatusError):
        return 'OpenAI devolvió un error temporal. Inténtalo más tarde.'
    if isinstance(error, ValueError):
        return str(error)
    return 'No se pudo preparar el cuestionario. Contacta al administrador.'
