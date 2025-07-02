from django.db.models import Model
from django.urls import reverse


def getUrl(
    model: Model | None = None,
    value: str | None = None,
    crud_action: str | None = None,
    full_url: str | None = None,
):
    """
    Returns the path for the given model_name.
    """
    if full_url is not None:
        return reverse(full_url) if value is None else reverse(full_url, args=(value,))
    model_name = model.__name__.lower()
    app_label = model._meta.app_label.lower()
    crud_action = crud_action or "create"
    return (
        reverse(f"{app_label}:{model_name}_{crud_action}")
        if value is None
        else reverse(f"{app_label}:{model_name}_{crud_action}", args=(value,))
    )
