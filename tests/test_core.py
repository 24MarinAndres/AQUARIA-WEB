import io
import zipfile
import pytest
from core import (calcular_aporte, normalizar, validar_cuestionario,
                  resumen_kpi, validar_codigo, REGISTROS)
from exportar import csv_zip
from persistence import Store


def preguntas():
    temas = [
      '¿Qué material plástico se fragmenta en partículas diminutas?',
      '¿Qué ecosistema protege la costa de fuertes oleajes?',
      '¿Cómo puede una persona reducir residuos en una playa?',
      '¿Cuál es una consecuencia de la pesca ilegal?',
      '¿Qué organismos construyen grandes arrecifes?',
      '¿Por qué es importante conservar los manglares?',
      '¿Qué práctica ayuda a evitar el daño a tortugas marinas?',
      '¿Cómo afecta el calentamiento al oxígeno disuelto en el agua?',
      '¿Qué actividad puede mejorar la biodiversidad de un estuario?',
      '¿Qué objetivo global busca proteger la vida submarina?',
    ]
    return {'preguntas': [
        {'pregunta': titulo,
         'opciones': [f'Acción sostenible {i}', f'Acción dañina {i}', f'Acción indiferente {i}'],
         'respuesta_correcta': f'Acción sostenible {i}',
         'frase_educativa': f'Las buenas acciones protegen la biodiversidad marina {i}.'}
        for i, titulo in enumerate(temas)]}


def test_validador_preguntas():
    val = validar_cuestionario(preguntas())
    assert len(val) == 10
    for p in val:
        assert len(p['opciones']) == 3 and p['respuesta_correcta'] in p['opciones']


def test_validador_rechaza_duplicados():
    d = preguntas()
    d['preguntas'][1]['pregunta'] = d['preguntas'][0]['pregunta']
    with pytest.raises(ValueError):validar_cuestionario(d)


def test_aporte():
    assert calcular_aporte(100000, 10000, 5000) == (85000, 51000)
    with pytest.raises(ValueError):calcular_aporte(10, 20, 0)
    with pytest.raises(ValueError):calcular_aporte(-1, 0, 0)


def test_normalizar_codigo():
    assert normalizar('ACCIÓN, Oceánica') == 'accion oceanica'
    assert validar_codigo('P01') and not validar_codigo('P 01')


def test_kpi_seis_y_piloto_primero():
    datos = {x: [] for x in REGISTROS}
    datos['inicios.csv'] = [
        {'id':'1','tipo':'Piloto','codigo':'P01'},
        {'id':'2','tipo':'Piloto','codigo':'P01'},
        {'id':'3','tipo':'Prueba técnica','codigo':'T01'},
    ]
    datos['partidas.csv'] = [{'id':'1','estado':'completada'}, {'id':'2','estado':'abandonada'},
                            {'id':'3','estado':'completada'}]
    datos['respuestas.csv'] = [{'id':'1','correcto':1,'proceso_ms':2}, {'id':'1','correcto':0,'proceso_ms':2},
                              {'id':'3','correcto':1,'proceso_ms':8}]
    r = resumen_kpi(datos)
    assert len(r) == 6
    assert '100.0 %' in r[0][1]
    assert '50.0 %' in r[1][1]
    assert '8.0000 ms' in r[4][1]


def test_guardado_y_exportacion(tmp_path):
    db = Store(f'sqlite:///{tmp_path}/test.db')
    vacios = {x: [] for x in REGISTROS}
    assert len(zipfile.ZipFile(io.BytesIO(csv_zip(vacios))).namelist()) == 6
    fila = dict(zip(REGISTROS['inicios.csv'], ['1','2026-10-27','P01','Piloto','3.0']))
    db.add('inicios.csv',fila,'session1')
    assert db.read('inicios.csv')[0] == fila
    assert len(db.read('inicios.csv','session1')) == 1
    assert db.read('inicios.csv','session2') == []


def test_cuota_diaria_atómica(tmp_path):
    db=Store(f'sqlite:///{tmp_path}/quota.db')
    assert db.reservar_generacion(2)
    assert db.reservar_generacion(2)
    assert not db.reservar_generacion(2)
    assert db.consumidas_hoy() == 2
