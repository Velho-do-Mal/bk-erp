"""
BK ERP — Exportação CSV genérica.
Uso: return exportar_csv(filename, headers, rows)
"""
import csv
from django.http import HttpResponse


def exportar_csv(filename, headers, rows):
    """
    headers: list de strings (colunas)
    rows: list de lists/tuples (dados)
    """
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    writer = csv.writer(response, delimiter=';')
    writer.writerow(headers)
    for row in rows:
        writer.writerow(row)
    return response
