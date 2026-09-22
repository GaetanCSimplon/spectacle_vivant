from django.template.loader import render_to_string
from weasyprint import HTML


def render_pdf(template_name, context=None):
    """Render a Django template to PDF bytes via WeasyPrint."""
    html = render_to_string(template_name, context or {})
    return HTML(string=html).write_pdf()
