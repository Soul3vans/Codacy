from typing import Any

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.forms import CheckboxInput, Form
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import path, reverse, reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, UpdateView
from django.views.generic.base import TemplateView
from django_filters.views import FilterView

from apps.core.forms import BaseReportForm


def http_403(request: HttpRequest, exception) -> HttpResponse:
    return render(request, "400/403.html")


def close_popup_view(request: HttpRequest) -> HttpResponse:
    return render(request, "components/close_popup.html")


class PopupMixin:
    """Add the popup behavior to the views."""

    def is_popup(self):
        """Returns True if the view is in popup mode."""
        return self.request.GET.get("is_popup", False) == "true"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["is_popup"] = self.is_popup()
        return context

    def get_success_url(self):
        if self.is_popup():
            return reverse("close_popup")
        return super().get_success_url()


class FileDownloadView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    TemplateView,
):
    def post(self, request, *args, **kwargs):
        """
        Download a file.
        """
        raise NotImplementedError("This method must be implemented.")


class ReportDownloadView(FileDownloadView):
    report_name = None
    report_text = None
    report_form = BaseReportForm
    permission_required = "accounts.download_cancer_report"
    template_name = "report/base_report.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """
        Return context data to generate report.
        """
        context = super().get_context_data(**kwargs)
        context["report_name"] = self.report_name
        context["report_text"] = self.report_text
        context["report_form"] = self.report_form()
        return context


class PaginationFilterView(LoginRequiredMixin, PermissionRequiredMixin, FilterView):
    """FilterView with pagination."""

    paginate_by = 30
    extra_context: dict = None
    permission_required = None
    post_function = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        model = self.model or self.queryset.model
        self.permission_required = (
            self.permission_required
            or f"{model._meta.app_label}.view_{model._meta.model_name}"
        )

    def get_ordering(self):
        """Return the field or fields to use for ordering the queryset."""
        ordering = self.request.GET.getlist(key="o", default=None)
        return ordering if len(ordering) > 0 else None

    def get_context_data(self, *args, **kwargs) -> dict:
        """
        Save the url lookup filters to use it in the url links.
        <a href="?page={{ page_obj.next_page_number }}&{{ parameters }}">
            Next
        </a>
        """
        _request_copy = self.request.GET.copy()
        parameters = _request_copy.pop("page", True) and _request_copy.urlencode()
        context = super().get_context_data(*args, **kwargs)
        self.extra_context = self.extra_context or {}
        context["parameters"] = parameters
        context["url_lookup"] = self.request.GET.urlencode()
        current_page = context["page_obj"].number
        paginator = context["paginator"]
        pagination_range = paginator.get_elided_page_range(
            current_page, on_each_side=2, on_ends=0
        )
        if self.model is not None:
            CURRENT_MODEL = self.model
            MODEL_NAME = self.model.__name__.lower()
        else:
            CURRENT_MODEL = self.queryset.model
            MODEL_NAME = self.queryset.model.__name__.lower()
        pagination_range = list(
            filter(lambda element: element != paginator.ELLIPSIS, pagination_range)
        )
        context["pagination_range"] = pagination_range
        APP_NAME = (
            context.get("app_name", None) or CURRENT_MODEL._meta.app_label.lower()
        )
        context["crud_name"] = (
            CURRENT_MODEL._meta.verbose_name_plural.capitalize() or context["crud_name"]
        )
        context["crud_instance_name"] = (
            CURRENT_MODEL._meta.verbose_name.lower() or context["crud_instance_name"]
        )
        context["add_url"] = f"{APP_NAME}:{MODEL_NAME}_create" or context["add_url"]
        context["detail_url"] = (
            f"{APP_NAME}:{MODEL_NAME}_detail" or context["detail_url"]
        )
        context["edit_url"] = f"{APP_NAME}:{MODEL_NAME}_update" or context["edit_url"]
        context["delete_url"] = (
            f"{APP_NAME}:{MODEL_NAME}_delete" or context["delete_url"]
        )

        context |= self.extra_context
        return context

    def post(self, request, *args, **kwargs):
        """
        Download a file.
        """
        if self.post_function is not None:
            return self.post_function(self, request, *args, **kwargs)
        raise NotImplementedError("This method must be implemented.")


class CancelUrlMixin:
    """Mixin to add cancel url to django generics views."""

    cancel_url = None

    def get_context_data(self, *args, **kwargs) -> dict:
        """Adds given url to the context."""
        context = super().get_context_data(*args, **kwargs)
        if not self.request.GET.get("return_to", False):
            context["cancel_url"] = self.cancel_url
        else:
            _request_copy = self.request.GET.copy()
            parameters = (
                _request_copy.pop("return_to", True) and _request_copy.urlencode()
            )
            context["cancel_url"] = self.request.GET.get("return_to")
            context["url_lookup"] = parameters
        return context

    def get_cancel_url(self):
        """Returns cancel url."""
        return reverse_lazy(self.cancel_url)


class ViewTitleMixin:
    """Mixin to view title to django generics views."""

    title = None

    def get_context_data(self, *args, **kwargs) -> dict:
        """Adds given title to the context."""
        context = super().get_context_data(*args, **kwargs)
        context["view_title"] = self.title
        return context


class GetObjectErrorMixin:
    """Generate user friendly message for object not found exception."""

    object_not_found_error_message = None

    def get(self, request: HttpRequest, *args, **kwargs):
        """Override get_object to handle object not found exception."""
        try:
            self.object = self.get_object()
        except Http404:
            messages.error(request, self.object_not_found_error_message)
            return redirect(self.get_cancel_url())
        return super().get(request, *args, **kwargs)


class BaseCreateView(
    PopupMixin,
    LoginRequiredMixin,
    PermissionRequiredMixin,
    SuccessMessageMixin,
    CancelUrlMixin,
    ViewTitleMixin,
    CreateView,
):
    """Base create view."""

    template_name = "base_crud/base_create.html"
    permission_required = None

    def get_form_kwargs(self):
        """Return the keyword arguments for instantiating the form."""
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def __init__(self, **kwargs):
        self.permission_required = (
            self.permission_required
            or f"{self.model._meta.app_label}.add_{self.model._meta.model_name}"
        )
        self.title = f"Añadir {self.model._meta.verbose_name.lower()}"
        super().__init__(**kwargs)


class BaseUpdateView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    SuccessMessageMixin,
    GetObjectErrorMixin,
    CancelUrlMixin,
    ViewTitleMixin,
    UpdateView,
):
    """Base update view."""

    template_name = "base_crud/base_update.html"
    permission_required = None

    def get_form_kwargs(self):
        """Return the keyword arguments for instantiating the form."""
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def __init__(self, **kwargs):
        self.permission_required = (
            self.permission_required
            or f"{self.model._meta.app_label}.change_{self.model._meta.model_name}"
        )
        self.title = f"Editar {self.model._meta.verbose_name.lower()}"
        super().__init__(**kwargs)


class BaseDetailView(
    PopupMixin,
    LoginRequiredMixin,
    PermissionRequiredMixin,
    GetObjectErrorMixin,
    CancelUrlMixin,
    ViewTitleMixin,
    DetailView,
):
    """Base detail view."""

    template_name = "base_crud/base_detail.html"
    form_class = None
    permission_required = None

    def __init__(self, **kwargs):
        self.permission_required = (
            self.permission_required
            or f"{self.model._meta.app_label}.view_{self.model._meta.model_name}"
        )
        self.title = f"Detalles de {self.model._meta.verbose_name.lower()}"
        super().__init__(**kwargs)

    def get_form_kwargs(self):
        """Return the keyword arguments for instantiating the form."""
        return {"request": self.request}

    def get_form_for_detail(self):
        """Returns the form_class with all the fields in readonly."""

        class ReadOnlyForm(self.form_class):
            """Helper class"""

            def __init__(self, *args, **kwargs):
                self.read_only_form = True
                super().__init__(*args, **kwargs)
                for _, field in self.fields.items():
                    field.widget.attrs["readonly"] = True
                    if isinstance(field.widget, CheckboxInput):
                        field.widget.attrs["disabled"] = True

        return ReadOnlyForm

    def get_context_data(self, *args, **kwargs) -> dict:
        """Adds given form to the context."""
        context = super().get_context_data(*args, **kwargs)
        form = self.get_form_for_detail()(
            instance=self.object, **self.get_form_kwargs()
        )
        context["form"] = form
        return context


class BaseDeleteView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    SuccessMessageMixin,
    GetObjectErrorMixin,
    CancelUrlMixin,
    ViewTitleMixin,
    DeleteView,
):
    """Base delete view."""

    template_name = "base_crud/base_delete.html"
    template_modal = "base_crud/base_modal_delete.html"
    permission_required = None

    def __init__(self, **kwargs):
        self.permission_required = (
            self.permission_required
            or f"{self.model._meta.app_label}.delete_{self.model._meta.model_name}"
        )
        self.title = f"Eliminar {self.model._meta.verbose_name.lower()}"
        super().__init__(**kwargs)

    def get_template_names(self) -> list[str]:
        """
        Changes the template in case the user uses the modal
        """
        if self.request.GET.get("modal", False) == "true":
            return [self.template_modal]
        return super().get_template_names()

    def form_valid(self, form: Form):
        """
        Call the delete() method on the fetched object and then redirect to the
        success URL.
        """
        self.object = self.get_object()
        success_url = self.get_success_url()
        self.object.delete()
        object_dict = {
            field.name: str(getattr(self.object, field.name, ""))
            for field in self.object._meta.fields
        }
        success_message = self.get_success_message(object_dict)
        messages.success(self.request, success_message)
        return redirect(success_url)


def getUrl(
    crud_class: View | None,
):
    """
    Returns the path for the given crud_class.
    """
    model_name = crud_class.model.__name__.lower()
    if issubclass(crud_class, BaseCreateView):
        return path(
            f"{model_name}/create/",
            crud_class.as_view(),
            name=f"{model_name}_create",
        )
    elif issubclass(crud_class, BaseUpdateView):
        return path(
            f"{model_name}/update/<pk>/",
            crud_class.as_view(),
            name=f"{model_name}_update",
        )
    elif issubclass(crud_class, BaseDetailView):
        return path(
            f"{model_name}/detail/<pk>/",
            crud_class.as_view(),
            name=f"{model_name}_detail",
        )
    else:
        return path(
            f"{model_name}/delete/<pk>/",
            crud_class.as_view(),
            name=f"{model_name}_delete",
        )
