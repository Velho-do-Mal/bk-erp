"""
json_utils.py — Serializacao JSON segura para embutir em <script> nos templates.

json.dumps() puro nao escapa a sequencia "</script>" (nem outras que o parser
HTML do navegador reconhece antes do JS rodar). Se qualquer valor dentro do
JSON vier de entrada de usuario (nome de cliente, observacao, descricao de
proposta etc.) e contiver "</script><script>...", o navegador fecha a tag
<script> no meio do JSON e executa o que vier a seguir como HTML/JS
arbitrario — um XSS armazenado ou refletido classico, mesmo com o dado tendo
passado por json.dumps normalmente.

Use sempre safe_json_dumps() (em vez de json.dumps) para qualquer valor que
sera renderizado no template com `{{ variavel|safe }}` dentro de uma tag
<script> (ou <textarea>, mesmo raciocinio).
"""
import json as _json


def safe_json_dumps(data, **kwargs):
    """
    Serializa `data` em JSON (mesma assinatura de json.dumps — aceita
    default=str, ensure_ascii=False etc) e escapa '<', '>' e '&' como
    escapes unicode (\\u003c, \\u003e, \\u0026).

    O resultado continua sendo JSON/JS válido: esses 3 caracteres só
    aparecem dentro de strings JSON, e um escape \\uXXXX dentro de uma
    string é decodificado de volta ao caractere original tanto por
    JSON.parse quanto por um literal de string JS puro — então nada muda
    para o JS que consome o valor, só o HTML parser deixa de enxergar
    "<script", "</script" ou "&" no meio do documento.
    """
    texto = _json.dumps(data, **kwargs)
    return (
        texto
        .replace('<', '\\u003c')
        .replace('>', '\\u003e')
        .replace('&', '\\u0026')
    )
