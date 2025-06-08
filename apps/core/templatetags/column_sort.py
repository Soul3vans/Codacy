from django.template import Library
from django.utils.html import format_html

register = Library()


@register.simple_tag(takes_context=True)
def create_header_column(
    context: dict, field_to_sort: str, column_name: str, clases: str = "text-center"
) -> str:
    """
    Generate the column with the link to sort.
    """
    url_start = context["url_lookup"]
    sort_url = context["url_lookup"]
    order_up = True
    first_sort = True
    if f"o=-{field_to_sort}" in sort_url:
        first_sort = False
        sort_url = sort_url.replace(f"&o=-{field_to_sort}", f"&o={field_to_sort}")
        sort_url = sort_url.replace(f"o=-{field_to_sort}", f"o={field_to_sort}")
        url_start = url_start.replace(f"&o=-{field_to_sort}", "")
        url_start = url_start.replace(f"o=-{field_to_sort}", "")
    elif f"o={field_to_sort}" in sort_url:
        order_up = False
        first_sort = False
        sort_url = sort_url.replace(f"&o={field_to_sort}", f"&o=-{field_to_sort}")
        sort_url = sort_url.replace(f"o={field_to_sort}", f"o=-{field_to_sort}")
        url_start = url_start.replace(f"&o={field_to_sort}", "")
        url_start = url_start.replace(f"o={field_to_sort}", "")
    else:
        sort_url = (
            (sort_url + "&")
            if len(sort_url) > 1 and not sort_url.endswith("&")
            else sort_url
        )
        sort_url += f"o={field_to_sort}"
    url_start = url_start if not url_start.startswith("&") else url_start[1:]
    url_start = (
        url_start if not url_start.endswith("&") else url_start[: len(url_start) - 1]
    )
    return format_html(
        """
        <th class="column-sorted {classes}">
            <div>
                {column_name}
                <div class="sort-options {show_sort}">
                    <a href="?{sort_url}" role="button" title="{ordering_text}"><i class="fa-solid fa-sort{sort_direction}"></i></a>
                </div>
                <div class="sort-options">
                    <a href="?{url_start}" class="{hide_cancel}" role="button" title="Quitar del orden"><i class="fa-solid fa-ban"></i></a>
                </div>
            </div>
        </th>""",
        url_start=url_start,
        sort_direction="" if first_sort else "-up" if not order_up else "-down",
        field_to_sort=field_to_sort,
        column_name=column_name,
        ordering_text=f"Ordenar por {column_name}" if first_sort else "Alternar orden",
        classes=clases,
        hide_cancel="hidden" if first_sort else "",
        show_sort="show" if not first_sort else "",
        sort_url=sort_url,
    )
