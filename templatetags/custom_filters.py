from django import template

register = template.Library()

@register.filter(name='multiply')
def multiply(value, arg):
    """Multiplies the value by the argument."""
    # Convertir les arguments en float si ce sont des chaînes avec des virgules comme séparateurs décimaux
    try:
        if isinstance(value, str):
            value = value.replace(',', '.')
        if isinstance(arg, str):
            arg = arg.replace(',', '.')
        return float(value) * float(arg)
    except (ValueError, TypeError) as e:
        print(f"Error in multiply filter with value {value} and arg {arg}: {e}")
        return None

@register.filter
def truncatechars_custom(value, arg):
    if len(value) > arg:
        return value[:arg] + '...'
    return value