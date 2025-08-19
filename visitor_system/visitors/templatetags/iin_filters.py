from django import template

register = template.Library()


@register.filter
def mask_iin(value: str | None):
	if not value:
		return '-'
	try:
		val = str(value)
		if len(val) < 4:
			return '****'
		return '********' + val[-4:]
	except Exception:
		return '************'


