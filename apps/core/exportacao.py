"""
BK ERP — Exportação CSV genérica.
Uso: return exportar_csv(filename, headers, rows)
"""
import csv
import io
from django.http import HttpResponse


def exportar_csv(filename, headers, rows):
    """
    headers: list de strings (colunas)
    rows: list de lists/tuples (dados)

    CORRIGIDO: antes, o csv.writer escrevia direto no HttpResponse (que
    tinha charset=utf-8-sig). HttpResponse.write() faz
    value.encode(self.charset) a cada chamada — e cada writer.writerow()
    é uma chamada separada — então "".encode('utf-8-sig') prefixava o BOM
    (\\xef\\xbb\\xbf) EM TODA LINHA do CSV, não só na primeira. Isso
    afetava todo export que usa este helper (propostas, clientes,
    fornecedores, documentos, transações, etc.). Agora o CSV é montado
    inteiro num buffer de texto e codificado de uma vez só — BOM aparece
    exatamente 1x, no início do arquivo (é o que o Excel espera para
    reconhecer UTF-8 e acentuação funcionar sem precisar "Importar Dados").
    """
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=';')
    writer.writerow(headers)
    for row in rows:
        writer.writerow(row)

    response = HttpResponse(
        buffer.getvalue().encode('utf-8-sig'),
        content_type='text/csv; charset=utf-8-sig',
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
