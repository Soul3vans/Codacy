from django.urls import reverse

from apps.accounts.factories import UserFactory
from apps.core.test import TestCase


class ModelFormViewTestCase(TestCase):
    """Test case for ModelForm validation."""

    @classmethod
    def setUpTestData(cls):
        """Common test data."""
        cls.user = UserFactory.create()

    def setUp(self) -> None:
        """Extra initialization."""
        self.client.force_login(self.user)

    def test_post(self):
        """Test ModelForm validation method to ensure adds the css class for validation."""
        response = self.client.post(
            reverse("patient:oncologic_create"),
            {"first_name": "Test", "identity_card": "11"},
        )
        self.assertIn("is-invalid", response.content.decode())
        self.assertIn("is-valid", response.content.decode())
