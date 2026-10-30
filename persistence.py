"""Almacén SQL de eventos y cuota diaria compartida por base de datos.
SQLite local es efímera en Community Cloud; configurar DATABASE_URL PostgreSQL
para obtener persistencia y cuotas globales compartidas entre réplicas.
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import (create_engine, MetaData, Table, Column, Integer, String,
                        Text, Index, select, insert, update)
from sqlalchemy.engine import Engine
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.dialects.postgresql import insert as pg_insert
from core import REGISTROS

metadata = MetaData()
events = Table('events', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('kind', String(40), nullable=False),
    Column('session_id', String(50), nullable=False),
    Column('ts', String(40), nullable=False),
    Column('payload', Text, nullable=False),
)
Index('idx_events_kind', events.c.kind)
Index('idx_events_session', events.c.session_id)
quota = Table('generation_quota', metadata,
    Column('day', String(10), primary_key=True),
    Column('used', Integer, nullable=False, default=0),
)


class Store:
    def __init__(self, database_url=None):
        if not database_url:
            Path('data').mkdir(exist_ok=True)
            database_url = 'sqlite:///data/aquaria.sqlite3'
        # SQLAlchemy uses postgresql+psycopg:// for the bundled driver.
        if database_url.startswith('postgres://'):
            database_url = 'postgresql+psycopg://' + database_url[len('postgres://'):]
        elif database_url.startswith('postgresql://'):
            database_url = 'postgresql+psycopg://' + database_url[len('postgresql://'):]
        self.engine: Engine = create_engine(database_url, pool_pre_ping=True)
        metadata.create_all(self.engine)
        self.persistent = self.engine.dialect.name == 'postgresql'

    def add(self, kind, payload, session_id):
        if kind not in REGISTROS:
            raise ValueError('Registro desconocido: ' + kind)
        if set(payload) != set(REGISTROS[kind]):
            raise ValueError('Encabezado incompatible: ' + kind)
        with self.engine.begin() as conn:
            conn.execute(insert(events).values(kind=kind, payload=json.dumps(payload, ensure_ascii=False),
                         session_id=session_id, ts=datetime.now(timezone.utc).isoformat()))

    def read(self, kind, session_id=None):
        if kind not in REGISTROS:
            raise ValueError('Registro desconocido')
        consulta = select(events.c.payload).where(events.c.kind == kind).order_by(events.c.id)
        if session_id is not None:
            consulta = consulta.where(events.c.session_id == session_id)
        with self.engine.connect() as conn:
            return [json.loads(row[0]) for row in conn.execute(consulta)]

    def all_records(self, session_id=None):
        return {nombre: self.read(nombre, session_id=session_id) for nombre in REGISTROS}

    def reservar_generacion(self, limite: int):
        """Reserva atómica hasta límite diario para una DB compartida.
        Cuenta intentos, aun cuando OpenAI devuelve error, para proteger saldo.
        """
        dia = datetime.now(timezone.utc).date().isoformat()
        limite = max(0, int(limite))
        dialect = self.engine.dialect.name
        if dialect == 'postgresql':
            sentencia = pg_insert(quota).values(day=dia, used=0).on_conflict_do_nothing(index_elements=['day'])
        elif dialect == 'sqlite':
            sentencia = sqlite_insert(quota).values(day=dia, used=0).on_conflict_do_nothing(index_elements=['day'])
        else:
            raise RuntimeError('Motor de base de datos no admitido para el control de cuota')
        with self.engine.begin() as conn:
            conn.execute(sentencia)
            r = conn.execute(update(quota).where(quota.c.day == dia, quota.c.used < limite)
                             .values(used=quota.c.used + 1))
            return r.rowcount == 1

    def consumidas_hoy(self):
        dia = datetime.now(timezone.utc).date().isoformat()
        with self.engine.connect() as conn:
            return conn.execute(select(quota.c.used).where(quota.c.day == dia)).scalar() or 0
