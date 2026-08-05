from django import template
from decimal import Decimal, InvalidOperation

register = template.Library()

@register.filter
def tem_modulo(user, chave):
    """Uso no template: {% if user|tem_modulo:'financeiro' %}...{% endif %}"""
    if not getattr(user, 'is_authenticated', False):
        return False
    return user.tem_modulo(chave)

@register.filter
def moeda(value):
    """Formata número como moeda pt-BR: R$ 1.234,56"""
    try:
        v = Decimal(str(value or 0))
        # Formata com 2 casas e separador de milhar
        inteiro, decimal = f"{abs(v):.2f}".split(".")
        inteiro_fmt = "{:,}".format(int(inteiro)).replace(",", ".")
        sinal = "-" if v < 0 else ""
        return f"R$ {sinal}{inteiro_fmt},{decimal}"
    except (InvalidOperation, TypeError, ValueError):
        return "R$ 0,00"
