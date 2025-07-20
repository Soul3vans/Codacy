from typing import Final

from django.db.models import Model
from django_select2.forms import ModelSelect2Widget

from apps.core.functions import getUrl

REPLACE_URL_VALUE: Final[str] = "URL_VALUE_FOR_REPLACE"


class RelatedModelWrapper(ModelSelect2Widget):
    template_name = "components/widgets/select.html"

    def __init__(self, *args, **kwargs):
        self.add_url = kwargs.pop("add_url", None)
        self.view_url = kwargs.pop("view_url", None)
        self.add_permission = kwargs.pop("add_permission", None)
        self.view_permission = kwargs.pop("view_permission", None)
        attrs = kwargs.get("attrs", {})
        attrs["class"] = attrs.get("class", "") + " related-model-field"
        kwargs["attrs"] = attrs
        super().__init__(*args, **kwargs)

    def get_context(self, name: str, value: str, attrs: dict):
        context = super().get_context(name, value, attrs)
        request = getattr(self, "request", None)
        if request is None:  # pragma: no cover
            return context
        model: Model = (
            self.model or None if self.queryset is None else self.queryset.model
        ) or self.choices.queryset.model
        add_permission = (
            self.add_permission
            or f"{model._meta.app_label}.add_{model._meta.model_name}"
        )
        view_permission = (
            self.add_permission
            or f"{model._meta.app_label}.view_{model._meta.model_name}"
        )
        if self.add_url is not None and self.view_url is not None:
            self.add_url = getUrl(full_url=self.add_url)
            self.view_url = getUrl(full_url=self.view_url, value=REPLACE_URL_VALUE)
        else:
            self.add_url = getUrl(model)
            self.view_url = getUrl(model, REPLACE_URL_VALUE, "detail")
        context["add_perm"] = (
            None if self.is_read_only_mode else request.user.has_perm(add_permission)
        )
        context["view_perm"] = request.user.has_perm(view_permission)
        context["add_url"] = None if self.is_read_only_mode else self.add_url
        context["view_url"] = self.view_url
        return context
