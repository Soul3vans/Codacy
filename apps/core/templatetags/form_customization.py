from django.template import Library
from django.utils.html import format_html

register = Library()


@register.simple_tag()
def create_div_row() -> str:
    """
    Generate a div row.
    """

    return format_html(
        """
        <div class="row">
        """
    )


@register.simple_tag()
def close_div() -> str:
    """
    Generate a div close.
    """

    return format_html(
        """
        </div>
        """
    )
