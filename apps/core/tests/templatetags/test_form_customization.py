from apps.core.templatetags.form_customization import close_div, create_div_row
from apps.core.test import SimpleTestCase


class TemplateTagTestCase(SimpleTestCase):
    """Test case for form_customization."""

    def test_create_div_row(self):
        """Test the div row creation."""
        result = create_div_row()
        self.assertIn('<div class="row">', result)

    def test_close_div(self):
        """Test the div close creation."""
        result = close_div()
        self.assertIn("</div>", result)
