"""AQUARIA · Web pública del juego de conservación marina ODS 14.
Ejecutar: streamlit run streamlit_app.py
La clave vive en los secretos del servidor, nunca en el navegador/GitHub.
"""
from __future__ import annotations

import hmac
import json
import os
from time import perf_counter
from uuid import uuid4

import streamlit as st
from core import (MODELO, PUNTOS_POR_ACIERTO, REGISTROS, TIPOS, VERSION,
                  calcular_aporte, fecha, nuevo_id, resumen_kpi, validar_codigo)
from ai import generar_preguntas, mensaje_error_ia
from persistence import Store
from exportar import csv_zip

inicio_carga = perf_counter()
st.set_page_config(page_title='AQUARIA · ODS 14', page_icon='🐠', layout='centered',
                   initial_sidebar_state='collapsed')


def config(nombre, default=None):
    valor = os.getenv(nombre)
    if valor is not None:
        return valor
    try:
        return st.secrets[nombre]
    except (KeyError, FileNotFoundError, AttributeError):
        return default
    except Exception:
        return default


@st.cache_resource(show_spinner=False)
def conectar_db(database_url):
    return Store(database_url)


@st.cache_data(show_spinner=False)
def estilos():
    return '''<style>
    :root {--mar:#087796; --profundo:#063747; --claro:#e9f6f7; --coral:#fdba72;}
    .block-container {max-width:900px;padding-top:1.5rem;padding-bottom:1.5rem;}
    [data-testid="stAppViewContainer"] {background:linear-gradient(180deg,#e8f9fc 0%,#f6fbfc 44%,#eaf5f4 100%);}
    [data-testid="stHeader"] {background:transparent;}
    h1,h2,h3 {color:#11556b!important;}
    .aq-head {display:flex;justify-content:space-between;align-items:center;gap:16px;padding:20px 26px;background:#eaf5f6;
      border-radius:16px 16px 0 0;border:1px solid #b5dae1;box-shadow:0 8px 28px #01455e14;}
    .aq-logo {font-size:30px;font-weight:850;letter-spacing:.06em;color:#10566b;line-height:1;}
    .aq-tag {font-size:14px;color:#286171;margin-top:5px;}
    .aq-claim {font-size:17px;font-weight:650;color:#10566b;max-width:270px;text-align:right;line-height:1.35;}
    .aq-strip {height:9px;background:linear-gradient(90deg,#007995,#00afbd,#56cdcf);}
    .aq-ocean {height:210px;overflow:hidden;position:relative;border-radius:0 0 16px 16px;
      background:radial-gradient(ellipse at 15% 0%,#7adad9,transparent 55%),linear-gradient(#2aa5b8,#06718f,#06536d);
      border:1px solid #98d8db;border-top:0;}
    .aq-sand {position:absolute;bottom:-30px;left:-6%;width:112%;height:115px;background:#d2cb97;border-radius:50% 50% 0 0;}
    .aq-fish {position:absolute;font-size:36px;left:0;animation:aqswim 27s linear infinite;}
    .aq-fish.a {top:34px;animation-delay:-12s;}.aq-fish.b {top:110px;animation-delay:-25s;animation-duration:36s;}
    .aq-fish.c {bottom:44px;animation-delay:-17s;animation-duration:31s;}
    .aq-plant {position:absolute;bottom:28px;font-size:50px;animation:aqsway 4s ease-in-out infinite alternate;}
    .aq-plant.left {left:3%;}.aq-plant.right {right:4%;animation-delay:-2s;}
    .aq-coral {position:absolute;bottom:29px;right:20%;font-size:51px;}.aq-star {position:absolute;bottom:35px;left:28%;font-size:32px;}
    .aq-bubble {position:absolute;bottom:-10px;left:90%;width:12px;height:12px;border:1px solid #dcffffaa;
      border-radius:50%;animation:aqrise 11s linear infinite;}
    .aq-paused .aq-ocean * {animation-play-state:paused!important;}
    @keyframes aqswim {from{transform:translateX(-80px) scaleX(-1)}to{transform:translateX(900px) scaleX(-1)}}
    @keyframes aqsway {from{transform:rotate(-13deg)}to{transform:rotate(12deg)}}
    @keyframes aqrise {from{transform:translateY(0);opacity:0}30%{opacity:1}to{transform:translateY(-260px);opacity:0}}
    .aq-kicker {color:#0e7188;font-size:14px;font-weight:700;letter-spacing:.04em;text-transform:uppercase;}
    .aq-q {background:#eff8f9;border-left:5px solid #1899ad;border-radius:10px;padding:18px 20px;
      font-size:22px;font-weight:700;color:#114a5c;line-height:1.42;}
    .aq-score {font-size:42px;font-weight:800;color:#075e77;}
    .aq-small {color:#335c65;font-size:14px;line-height:1.5;}
    .aq-footer {text-align:center;color:#345e69;font-size:14px;padding:12px;}
    div.stButton>button[kind="primary"] {background:#116a81;border:0;color:white;}
    div.stButton>button {min-height:46px;border-radius:9px;white-space:normal;}
    @media(max-width:650px){.aq-head{padding:17px;flex-direction:column;align-items:flex-start;}
      .aq-claim{max-width:100%;text-align:left;font-size:15px}.aq-logo{font-size:26px}.aq-ocean{height:180px}}
    @media(prefers-reduced-motion: reduce){.aq-ocean *{animation:none!important;}}
    </style>'''


st.markdown(estilos(), unsafe_allow_html=True)

try:
    db = conectar_db(config('DATABASE_URL'))
except Exception:
    st.error('No se pudo iniciar la base de datos. El administrador debe revisar DATABASE_URL.')
    st.stop()

if 'aq_session' not in st.session_state:
    st.session_state.aq_session = str(uuid4())
    st.session_state.screen = 'menu'
    st.session_state.last_result = None
    st.session_state.active = False
    st.session_state.quiz = []
    st.session_state.question_index = 0
    st.session_state.choice = None
    st.session_state.score = 0
    st.session_state.answered_count = 0
    st.session_state.start_time = None
    st.session_state.partida_id = None
    st.session_state.player_code = 'P' + uuid4().hex[:6].upper()
    st.session_state.session_type = TIPOS[0]
    st.session_state.start_attempts = 0
    st.session_state.is_admin = False
    st.session_state.error = ''
    st.session_state.paused = False
    try:
        db.add('arranques.csv', {'fecha_utc': fecha(), 'version': VERSION,
                               'inicio_s': round(perf_counter()-inicio_carga, 6)}, st.session_state.aq_session)
    except Exception:
        pass

SID = st.session_state.aq_session


def registrar(nombre, datos):
    try:
        db.add(nombre, datos, SID)
        return True
    except Exception:
        st.warning('No se pudo guardar un registro. Informa al administrador de AQUARIA.')
        return False


def ir(pantalla):
    st.session_state.screen = pantalla
    st.rerun()


def cerrar_partida(situacion):
    if not st.session_state.active:
        return
    r = {'id': st.session_state.partida_id, 'fecha_utc': fecha(),
         'codigo': st.session_state.player_code, 'tipo': st.session_state.session_type,
         'estado': situacion, 'respuestas': st.session_state.answered_count,
         'aciertos': st.session_state.score // PUNTOS_POR_ACIERTO,
         'puntaje': st.session_state.score,
         'duracion_s': round(perf_counter()-st.session_state.start_time, 3)}
    st.session_state.active = False
    st.session_state.last_result = r
    registrar('partidas.csv', r)


def comenzar():
    codigo = st.session_state.player_code.strip()
    if not validar_codigo(codigo):
        st.session_state.error = 'Escribe un código de 1 a 20 caracteres: letras, números, guion o guion bajo.'
        ir('error')
    clave = config('OPENAI_API_KEY')
    if not clave:
        st.session_state.error = 'La API aún no ha sido configurada por el administrador del juego.'
        ir('error')
    try:
        max_sesion = max(0, int(config('AQUARIA_MAX_GENERATIONS_SESSION', 3)))
        max_dia = max(0, int(config('AQUARIA_MAX_GENERATIONS_DAY', 15)))
    except ValueError:
        max_sesion, max_dia = 3, 15
    if st.session_state.start_attempts >= max_sesion:
        st.session_state.error = 'Esta sesión ha alcanzado su límite de partidas nuevas.'
        ir('error')
    try:
        permitido = db.reservar_generacion(max_dia)
    except Exception:
        st.session_state.error = 'No fue posible comprobar el límite de consumo. No se llamó a OpenAI.'
        ir('error')
    if not permitido:
        st.session_state.error = 'Se agotaron las generaciones disponibles para hoy (UTC). Inténtalo otro día.'
        ir('error')
    st.session_state.start_attempts += 1
    registro = {'id_generacion': nuevo_id(), 'fecha_utc': fecha(), 'id_partida': '',
                'modelo': MODELO, 'estado': 'error', 'tiempo_api_s': '',
                'tiempo_total_s': '', 'tokens_entrada': '', 'tokens_salida': '', 'error_tipo': ''}
    preguntas = None
    mensaje = ''
    t0 = perf_counter()
    with st.spinner('Generando diez preguntas del ODS 14 con OpenAI…'):
        try:
            preguntas = generar_preguntas(clave, registro)
            registro['estado'] = 'valida'
            registro['id_partida'] = nuevo_id()
        except Exception as error:
            # Registrar solo tipo del error; nunca el mensaje crudo ni credenciales.
            registro['error_tipo'] = type(error).__name__
            mensaje = mensaje_error_ia(error)
        finally:
            registro['tiempo_total_s'] = round(perf_counter()-t0, 3)
            registrar('generaciones.csv', registro)
    if preguntas is None:
        st.session_state.error = mensaje
        ir('error')
    st.session_state.quiz = preguntas
    st.session_state.question_index = 0
    st.session_state.score = 0
    st.session_state.choice = None
    st.session_state.answered_count = 0
    st.session_state.partida_id = registro['id_partida']
    st.session_state.start_time = perf_counter()
    st.session_state.active = True
    registrar('inicios.csv', {'id': registro['id_partida'], 'fecha_utc': fecha(),
                             'codigo': codigo, 'tipo': st.session_state.session_type,
                             'version': VERSION})
    ir('game')


def conservar_tipo_sesion():
    """El estado del widget es temporal; guardamos el tipo en una clave persistente."""
    st.session_state.session_type = st.session_state.session_type_control


def conservar_codigo_jugador():
    """Evita perder el código al abandonar el menú principal."""
    st.session_state.player_code = st.session_state.player_code_control


def responder(elegido):
    if not st.session_state.active or st.session_state.choice is not None:
        return
    t0 = perf_counter()
    item = st.session_state.quiz[st.session_state.question_index]
    if elegido not in item['opciones']:
        return
    correcto = elegido == item['respuesta_correcta']
    st.session_state.choice = elegido
    st.session_state.answered_count += 1
    if correcto:
        st.session_state.score += PUNTOS_POR_ACIERTO
    proceso_ms = round((perf_counter()-t0)*1000, 6)
    registrar('respuestas.csv', {'id': st.session_state.partida_id,
        'fecha_utc': fecha(), 'turno': st.session_state.question_index+1,
        'pregunta': item['pregunta'], 'opciones': json.dumps(item['opciones'], ensure_ascii=False),
        'elegido': elegido, 'respuesta_correcta': item['respuesta_correcta'],
        'frase_educativa': item['frase_educativa'], 'correcto': int(correcto),
        'proceso_ms': proceso_ms})
    st.rerun()


def siguiente():
    if not st.session_state.active or st.session_state.choice is None:
        return
    if st.session_state.question_index == len(st.session_state.quiz)-1:
        cerrar_partida('completada')
        ir('resultado')
    else:
        st.session_state.question_index += 1
        st.session_state.choice = None
        st.rerun()


with st.sidebar:
    st.markdown('## ⚙️ AQUARIA')
    st.write('ODS 14 · Conservación marina')
    if st.button('Pausar fondo' if not st.session_state.paused else 'Activar fondo'):
        st.session_state.paused = not st.session_state.paused
        st.rerun()
    if st.session_state.screen not in ('menu', 'game') and st.button('Volver al menú', key='sidebar_volver'):
        ir('menu')
    st.caption('Las preguntas se generan en un servidor. Tu navegador no recibe la clave de API.')
    with st.expander('Administración y registros completos'):
        clave_admin = config('AQUARIA_ADMIN_PASSWORD')
        if not clave_admin:
            st.info('Los registros globales están protegidos. Configura AQUARIA_ADMIN_PASSWORD en el servidor.')
        elif not st.session_state.is_admin:
            password = st.text_input('Contraseña de administración', type='password')
            if st.button('Entrar como administrador'):
                if password and hmac.compare_digest(password, str(clave_admin)):
                    st.session_state.is_admin = True
                    st.rerun()
                else:
                    st.error('Contraseña incorrecta.')
        else:
            st.success('Acceso administrativo habilitado.')
            if st.button('Cerrar acceso administrativo'):
                st.session_state.is_admin = False
                st.rerun()

st.markdown('''<div class="aq-head"><div><div class="aq-logo">AQUARIA</div>
  <div class="aq-tag">Aprende a cuidar la vida marina</div></div>
  <div class="aq-claim">Cada decisión cuenta para cuidar el océano.</div></div>
  <div class="aq-strip"></div>''', unsafe_allow_html=True)

pantalla = st.session_state.screen
with st.container(border=True):
    if pantalla == 'menu':
        st.header('Menú principal')
        st.write('Selecciona el propósito de la sesión. Utiliza un código como P01, sin nombre ni correo.')
        c1, c2 = st.columns(2)
        with c1:
            if 'session_type_control' not in st.session_state:
                st.session_state.session_type_control = st.session_state.session_type
            st.selectbox('Sesión', TIPOS, key='session_type_control',
                         on_change=conservar_tipo_sesion)
        with c2:
            if 'player_code_control' not in st.session_state:
                st.session_state.player_code_control = st.session_state.player_code
            st.text_input('Código de jugador', key='player_code_control',
                          max_chars=20, on_change=conservar_codigo_jugador)
        a,b,c = st.columns(3)
        with a:
            if st.button('🐠 Jugar', type='primary', use_container_width=True):ir('elegir')
        with b:
            if st.button('📘 Cómo jugar', use_container_width=True):ir('instrucciones')
        with c:
            if st.button('🏅 Mi resultado', use_container_width=True):ir('resultado')
        d,e,f = st.columns(3)
        with d:
            if st.button('🌊 Nuestro aporte', use_container_width=True):ir('aporte')
        with e:
            if st.button('📊 Registros y KPI', use_container_width=True):ir('kpi')
        with f:
            if st.button('👋 Terminar', use_container_width=True):ir('fin')
        st.caption('Explora el ODS 14 y descubre cómo proteger la vida submarina.')

    elif pantalla == 'instrucciones':
        st.header('Cómo jugar')
        st.markdown('''1. Al iniciar, OpenAI genera diez preguntas sobre el ODS 14.
2. Lee cada pregunta y elige una de sus tres opciones.
3. Cada acierto suma **10 puntos**; un error suma **0**.
4. Lee la frase educativa y pulsa **Siguiente**.
5. Completa los diez turnos. El máximo es **100 puntos**.''')
        st.info('No hay límite de tiempo ni más de una respuesta por pregunta. Cada partida genera preguntas nuevas; pueden coincidir ideas entre partidas. El contenido de IA puede tener errores de exactitud científica.')
        if st.button('Elegir juego', type='primary'): ir('elegir')
        if st.button('Volver al menú'):ir('menu')

    elif pantalla == 'elegir':
        st.header('Elige un minijuego')
        st.subheader('Explora y protege el océano')
        st.write('10 preguntas por partida · ODS 14 · Conservación marina')
        st.caption('Iniciar solicita un cuestionario nuevo a OpenAI y consume cuota del servidor.')
        if st.button('Iniciar partida', type='primary', use_container_width=True):comenzar()
        st.divider()
        st.subheader('Decisiones por el océano')
        st.write('Segundo minijuego previsto para una entrega posterior.')
        st.button('Próximamente', disabled=True)
        if st.button('Volver al menú'):ir('menu')

    elif pantalla == 'game':
        item = st.session_state.quiz[st.session_state.question_index]
        pos = st.session_state.question_index
        st.markdown('<span class="aq-kicker">Explora y protege el océano</span>', unsafe_allow_html=True)
        st.progress((pos+1)/len(st.session_state.quiz))
        st.write(f'Pregunta **{pos+1} de {len(st.session_state.quiz)}** · Puntaje: **{st.session_state.score}**')
        st.markdown('<div class="aq-q">'+__import__('html').escape(item['pregunta'])+'</div>', unsafe_allow_html=True)
        st.write('')
        if st.session_state.choice is None:
            for k, opcion in enumerate(item['opciones']):
                if st.button(opcion, key=f'answer_{st.session_state.partida_id}_{pos}_{k}', use_container_width=True):
                    responder(opcion)
            if st.button('Abandonar partida'):
                cerrar_partida('abandonada')
                ir('resultado')
        else:
            correcto = st.session_state.choice == item['respuesta_correcta']
            if correcto:
                st.success('¡Correcto! +10 puntos')
            else:
                st.error('Incorrecto. La respuesta correcta es: ' + item['respuesta_correcta'])
            st.info('🌊 ' + item['frase_educativa'])
            if st.button('Ver resultado' if pos == len(st.session_state.quiz)-1 else 'Siguiente',
                         type='primary', use_container_width=True):
                siguiente()

    elif pantalla == 'resultado':
        st.header('Mi último resultado')
        r = st.session_state.last_result
        if r is None:
            st.write('Aún no has jugado una partida en esta sesión.')
        else:
            st.subheader('Partida ' + r['estado'])
            st.markdown(f'<div class="aq-score">{r["puntaje"]} / 100 puntos</div>', unsafe_allow_html=True)
            st.write(f'{r["aciertos"]} aciertos en {r["respuestas"]} respuestas · Duración {r["duracion_s"]} segundos')
            st.caption('Evita dejar residuos en ríos, playas y océanos.')
        if st.button('Jugar otra vez', type='primary'):ir('elegir')
        if st.button('Volver al menú'):ir('menu')

    elif pantalla == 'aporte':
        st.header('Nuestro aporte al océano')
        st.write('AQUARIA promueve la educación marina relacionada con el ODS 14.')
        st.write('Se propone destinar el **60 % de los ingresos elegibles** a una fundación pendiente de seleccionar.')
        st.warning('**Simulación académica:** no se cobra ni se transfiere dinero.')
        with st.form('form_aporte'):
            ingresos = st.number_input('Ingresos (COP)', min_value=0, value=100000, step=10000)
            reembolsos = st.number_input('Reembolsos (COP)', min_value=0, value=0, step=10000)
            comisiones = st.number_input('Comisiones (COP)', min_value=0, value=0, step=10000)
            enviar = st.form_submit_button('Calcular aporte', type='primary')
        if enviar:
            try:
                elegible, aporte = calcular_aporte(ingresos, reembolsos, comisiones)
                registrar('aportes.csv', {'fecha_utc': fecha(), 'ingresos': ingresos,
                    'reembolsos': reembolsos, 'comisiones': comisiones, 'elegible': elegible,
                    'aporte_estimado': aporte, 'transferido': 0, 'simulado': True})
                st.success(f'Ingreso elegible: {elegible:,.0f} COP · Aporte estimado: {aporte:,.2f} COP')
                st.caption('Transferencia real: 0 COP')
            except ValueError as error:
                st.error(str(error))
        if st.button('Volver al menú'):ir('menu')

    elif pantalla == 'kpi':
        st.header('Registros y KPI')
        try:
            registros = db.all_records()
            st.table([{'Indicador': a, 'Resultado observado': b} for a,b in resumen_kpi(registros)])
            generaciones = registros['generaciones.csv']
            validas = [r for r in generaciones if r['estado'] == 'valida']
            tiempos = [float(r['tiempo_api_s']) for r in validas if r['tiempo_api_s'] != '']
            media = f'{sum(tiempos)/len(tiempos):.2f} s' if tiempos else 'No calculable'
            st.write(f'Solicitudes registradas: **{len(generaciones)}** · Cuestionarios válidos: **{len(validas)}** · Tiempo medio API (válidas): **{media}**')
        except Exception:
            st.error('No fue posible leer los registros de la base de datos.')
        st.caption('Los KPI usan los datos de AQUARIA. El indicador 4 se adaptó a tiempo de inicio de la interfaz web; no es directamente comparable con Colab. La estabilidad no mide disponibilidad de OpenAI. En alojamiento gratuito sin PostgreSQL, los registros pueden perderse al reiniciar el servidor.')
        if st.session_state.is_admin:
            st.download_button('Descargar todos los registros CSV (ZIP)',
                data=csv_zip(db.all_records()), file_name='AQUARIA_registros_globales.zip',
                mime='application/zip', type='primary')
        else:
            st.download_button('Descargar mis registros de esta sesión (ZIP)',
                data=csv_zip(db.all_records(session_id=SID)),
                file_name='AQUARIA_mis_registros.zip', mime='application/zip', type='primary')
            st.caption('Para proteger a otros jugadores, solo los administradores pueden descargar registros globales.')
        if st.button('Volver al menú'):ir('menu')

    elif pantalla == 'error':
        st.header('No se inició la partida')
        st.error(st.session_state.error)
        st.caption('No se reintenta automáticamente. Otra solicitud puede consumir créditos de la API.')
        if st.button('Reintentar generación', type='primary'):
            comenzar()
        if st.button('Volver al menú'):ir('menu')

    elif pantalla == 'fin':
        st.header('¡Gracias por jugar!')
        if st.button('Volver al menú', type='primary'):ir('menu')

st.markdown('<div class="'+('aq-paused' if st.session_state.paused else '')+'"><div class="aq-ocean" aria-label="Fondo marino animado">'
    '<div class="aq-sand"></div><span class="aq-fish a">🐠</span><span class="aq-fish b">🐟</span>'
    '<span class="aq-fish c">🐠</span><span class="aq-star">⭐</span><span class="aq-coral">🪸</span>'
    '<span class="aq-plant left">🌿</span><span class="aq-plant right">🌿</span><span class="aq-bubble"></span>'
    '</div></div><div class="aq-footer">ODS 14 · Conservación marina · AQUARIA</div>', unsafe_allow_html=True)
