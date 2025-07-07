from django.contrib.messages import get_messages
from django.urls import reverse, reverse_lazy
from django.views.generic.base import ContextMixin

from apps.accounts.factories import UserFactory
from apps.accounts.models import User
from apps.cancer_registry.factories import NeoplasmFactory
from apps.core.test import SimpleTestCase, TestCase
from apps.core.views import (
    CancelUrlMixin,
    FileDownloadView,
    PaginationFilterView,
    ReportDownloadView,
    ViewTitleMixin,
)
from apps.geographic_location.factories import ProvinceFactory
from apps.geographic_location.models import Province
from apps.geographic_location.views import ProvinceDeleteView


class Helper(CancelUrlMixin, ContextMixin):
    class RequestHelper:
        GET = {}

    cancel_url = "admin:login"
    request = RequestHelper()


class CancelUrlMixinTestCase(TestCase):
    """Test case for CancelUrlMixin."""

    @classmethod
    def setUpTestData(cls):
        """Common test data."""
        cls.mixin = Helper()

    def test_mixin_get_context_data(self):
        """Test that get_context_data in CancelUrlMixin returns the cancel url."""

        self.assertIn("cancel_url", self.mixin.get_context_data())
        self.assertEqual(
            self.mixin.get_context_data()["cancel_url"],
            "admin:login",
        )

    def test_mixin_get_cancel_url(self):
        """Test that get_cancel_url in CancelUrlMixin returns the cancel url."""
        self.assertEqual(
            reverse_lazy("admin:login"),
            self.mixin.get_cancel_url(),
        )


class ViewTitleMixinTestCase(TestCase):
    """Test case for ViewTitleMixin."""

    @classmethod
    def setUpTestData(cls):
        """Common test data."""

        class Helper(ViewTitleMixin, ContextMixin):
            title = "randomtitle"

        cls.mixin = Helper()

    def test_mixin_get_context_data(self):
        """Test that get_context_data in ViewTitleMixin returns the title of the view."""
        self.assertIn("view_title", self.mixin.get_context_data())
        self.assertEqual(
            self.mixin.get_context_data()["view_title"],
            "randomtitle",
        )


class GetObjectErrorMixinTestCase(TestCase):
    """Test case for GetObjectErrorMixin."""

    @classmethod
    def setUpTestData(cls):
        """Common test data."""
        province = ProvinceFactory.create()
        Province.objects.filter(pk=province.pk).delete()
        cls.invalid_pk = province.pk
        cls.valid_pk = ProvinceFactory.create().pk
        cls.user = UserFactory.create()

    def setUp(self) -> None:
        """Extra initialization."""
        self.client.force_login(self.user)

    def test_get(self):
        """Test that GetObjectErrorMixin redirects to the cancel_url and alert the user."""
        response = self.client.get(
            reverse("geographic_location:province_detail", args=(self.invalid_pk,))
        )
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Provincia no encontrada")
        response = self.client.get(
            reverse("geographic_location:province_detail", args=(self.valid_pk,))
        )
        self.assertIn(
            "object",
            response.context,
        )


class BaseDetailViewTestCase(TestCase):
    """Test case for BaseDetailView."""

    @classmethod
    def setUpTestData(cls):
        """Common test data."""
        cls.province_pk = ProvinceFactory.create().pk
        cls.neoplasm_pk = NeoplasmFactory.create().pk
        cls.user = UserFactory.create()

    def setUp(self) -> None:
        """Extra initialization."""
        self.client.force_login(self.user)

    def test_get_context_data(self):
        """Test that BaseDetailView makes the form readonly."""
        response = self.client.get(
            reverse("geographic_location:province_detail", args=(self.province_pk,))
        )
        self.assertIn("form", response.context)
        self.assertIn("readonly", response.content.decode())

    def test_get_context_data_disable_checkbox(self):
        """Test that BaseDetailView makes the form readonly and checkboxes disabled."""
        response = self.client.get(
            reverse("cancer_registry:neoplasm_detail", args=(self.neoplasm_pk,))
        )
        self.assertIn("form", response.context)
        self.assertIn("disabled", response.content.decode())

    def test_mixin_get_context_data_width_return_to(self):
        """Test that get_context_data in CancelUrlMixin returns the cancel url and the url lookups."""
        response = self.client.get(
            reverse(
                "cancer_registry:neoplasm_detail",
                args=(self.neoplasm_pk,),
            )
            + "?return_to=cancer_registry:neoplasm_list&page=1"
        )
        self.assertIn("url_lookup", response.context)
        self.assertEqual(response.context["url_lookup"], "page=1")


class BaseDeleteViewTestCase(TestCase):
    """Test case for BaseDeleteView."""

    @classmethod
    def setUpTestData(cls):
        """Common test data."""
        cls.province = ProvinceFactory.create()
        cls.user = UserFactory.create()

    def setUp(self) -> None:
        """Extra initialization."""
        self.client.force_login(self.user)

    def test_delete(self):
        """Test that BaseDeleteView alert the user when an instance is deleted."""
        response = self.client.post(
            reverse("geographic_location:province_delete", args=(self.province.pk,))
        )
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(
            str(messages[0]),
            ProvinceDeleteView.success_message % self.province.__dict__,
        )
        self.assertRedirects(
            response,
            ProvinceDeleteView.success_url,
            status_code=302,
            target_status_code=200,
            fetch_redirect_response=True,
        )

    def test_delete_modal(self):
        """Test that BaseDeleteView changes the template if modal is present in the request params."""
        response = self.client.get(
            reverse("geographic_location:province_delete", args=(self.province.pk,))
        )
        self.assertTemplateUsed(response, template_name="base_crud/base_delete.html")
        response = self.client.get(
            reverse("geographic_location:province_delete", args=(self.province.pk,))
            + "?modal=true"
        )
        self.assertTemplateUsed(
            response, template_name="base_crud/base_modal_delete.html"
        )


class CoreHandlerTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        """Common test data."""
        cls.user = UserFactory.create(is_staff=False, is_superuser=False)

    def test_403(self) -> None:
        self.client.force_login(self.user)
        response = self.client.get(reverse("patient:oncologic_create"))
        self.assertTemplateUsed(response, "400/403.html")


class FileDownloadViewTestCase(SimpleTestCase):
    def test_post(self) -> None:
        with self.assertRaises(NotImplementedError):
            FileDownloadView.post(None, None)


class ReportDownloadViewTestCase(SimpleTestCase):
    def test_get(self) -> None:
        response = ReportDownloadView().get_context_data()
        self.assertIn("report_name", response)
        self.assertIn("report_text", response)
        self.assertIn("report_form", response)


class PaginationFilterViewTestCase(SimpleTestCase):
    def test_post(self) -> None:
        with self.assertRaises(NotImplementedError):
            PaginationFilterView(model=User).post(None, None)
