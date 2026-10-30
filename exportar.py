"""Descarga de los seis CSV originales en un ZIP, sin escribir archivos web públicos."""
import csv
import io
import zipfile
from core import REGISTROS


def csv_zip(registros: dict) -> bytes:
    memoria = io.BytesIO()
    with zipfile.ZipFile(memoria, 'w', zipfile.ZIP_DEFLATED) as paquete:
        for nombre, campos in REGISTROS.items():
            texto = io.StringIO(newline='')
            writer = csv.DictWriter(texto, fieldnames=campos, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(registros.get(nombre, []))
            paquete.writestr(nombre, texto.getvalue().encode('utf-8-sig'))
    return memoria.getvalue()
