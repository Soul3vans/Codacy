from django.forms import (
    DateField,
    DateInput,
    Form,
    ModelChoiceField,
    ModelForm,
    TypedChoiceField,
)

from apps.core.fields import RelatedModelWrapper


class ChoiceField(TypedChoiceField):
    def __init__(
        self,
        choices=(),
        empty_label=None,
        required=True,
        widget=None,
        label=None,
        initial=None,
        help_text=None,
        empty_value=None,
        *args,
        **kwargs,
    ):
        # prepend an empty label if it exists (and field is not required!)
        if not required and empty_label is not None:
            choices = tuple([(None, empty_label)] + list(choices))  # pragma: no cover

        super().__init__(
            choices=choices,
            required=required,
            widget=widget,
            label=label,
            initial=initial,
            help_text=help_text,
            empty_value=empty_value,
            *args,
            **kwargs,
        )


class ModelForm(ModelForm):
    """Class to handle form validation."""

    def __init__(self, *args, **kwargs) -> None:
        request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)
        for _, field in self.fields.items():
            if isinstance(field, ModelChoiceField) and isinstance(
                field.widget, RelatedModelWrapper
            ):
                field.widget.request = request
                field.widget.is_read_only_mode = (
                    getattr(self, "read_only_form", False) is True
                )

    def is_valid(self) -> bool:
        """
        Returns if form is valid and adds css clases according to field valid state.
        """
        result = super().is_valid()
        if not result:
            for key, field in self.fields.items():
                if "class" in field.widget.attrs:
                    if key in self.errors:
                        field.widget.attrs["class"] = (
                            "is-invalid " + field.widget.attrs["class"]
                        )
                    else:
                        field.widget.attrs["class"] = (
                            "is-valid " + field.widget.attrs["class"]
                        )
        return result


class BaseReportForm(Form):
    initial_date = DateField(
        widget=DateInput(
            attrs={
                "class": "form-control",
                "placeholder": "Fecha inicial",
                "type": "date",
            },
            format="%Y-%m-%d",
        ),
        label="Fecha inicial",
        required=False,
    )
    final_date = DateField(
        widget=DateInput(
            attrs={
                "class": "form-control",
                "placeholder": "Fecha final",
                "type": "date",
            },
            format="%Y-%m-%d",
        ),
        label="Fecha final",
        required=False,
    )
