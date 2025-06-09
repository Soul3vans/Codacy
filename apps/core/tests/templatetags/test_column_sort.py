# Create your tests here.

from apps.core.templatetags.column_sort import create_header_column
from apps.core.test import TestCase


class TemplateTagTestCase(TestCase):
    """Test case for create_header_column."""

    @classmethod
    def setUpTestData(cls):
        """Common test data."""
        cls.context_empty = {"url_lookup": ""}
        cls.context_lookup = {"url_lookup": "random=1"}
        cls.context_asc_lookup_exists = {"url_lookup": "o=field_to_sort"}
        cls.context_desc_lookup_exists = {"url_lookup": "o=-field_to_sort"}
        cls.context_lookup_mix = {"url_lookup": "o=field_to_sort&random=1"}
        cls.context_lookup_mix_complex = {
            "url_lookup": "random=2&o=field_to_sort&random=1"
        }

    def test_create_header_column_empty(self):
        """Test the links creation when the sort is the first in request."""
        column_html = create_header_column(
            self.context_empty, "field_to_sort", "column_name"
        )
        self.assertIn('<th class="column-sorted text-center">', column_html)
        self.assertIn("column_name", column_html)
        self.assertIn(
            '<a href="?o=field_to_sort" role="button" title="Ordenar por column_name"><i class="fa-solid fa-sort"></i></a>',
            column_html,
        )

    def test_create_header_column_asc_lookup_exists(self):
        """Test the links creation when the sort is already in request (asc)."""
        column_html = create_header_column(
            self.context_asc_lookup_exists, "field_to_sort", "column_name"
        )
        self.assertIn('<th class="column-sorted text-center">', column_html)
        self.assertIn("column_name", column_html)
        self.assertIn(
            '<a href="?o=-field_to_sort" role="button" title="Alternar orden"><i class="fa-solid fa-sort-up"></i></a>',
            column_html,
        )
        self.assertIn(
            '<a href="?" class="" role="button" title="Quitar del orden"><i class="fa-solid fa-ban"></i></a>',
            column_html,
        )

    def test_create_header_column_desc_lookup_exists(self):
        """Test the links creation when the sort is already in request (desc)."""
        column_html = create_header_column(
            self.context_desc_lookup_exists, "field_to_sort", "column_name"
        )
        self.assertIn('<th class="column-sorted text-center">', column_html)
        self.assertIn("column_name", column_html)
        self.assertIn(
            '<a href="?o=field_to_sort" role="button" title="Alternar orden"><i class="fa-solid fa-sort-down"></i></a>',
            column_html,
        )
        self.assertIn(
            '<a href="?" class="" role="button" title="Quitar del orden"><i class="fa-solid fa-ban"></i></a>',
            column_html,
        )

    def test_create_header_column_lookup(self):
        """Test the links creation when the request contains a previous sort."""
        column_html = create_header_column(
            self.context_lookup, "field_to_sort", "column_name"
        )
        self.assertIn('<th class="column-sorted text-center">', column_html)
        self.assertIn("column_name", column_html)
        self.assertIn(
            '<a href="?random=1&amp;o=field_to_sort" role="button" title="Ordenar por column_name"><i class="fa-solid fa-sort"></i></a>',
            column_html,
        )
        self.assertIn(
            '<a href="?random=1" class="hidden" role="button" title="Quitar del orden"><i class="fa-solid fa-ban"></i></a>',
            column_html,
        )

    def test_create_header_column_lookup_mix(self):
        """Test the links creation when the request contains a previous sort and current sort is in request."""
        column_html = create_header_column(
            self.context_lookup_mix, "field_to_sort", "column_name"
        )
        self.assertIn('<th class="column-sorted text-center">', column_html)
        self.assertIn("column_name", column_html)
        self.assertIn(
            '<a href="?o=-field_to_sort&amp;random=1" role="button" title="Alternar orden"><i class="fa-solid fa-sort-up"></i></a>',
            column_html,
        )
        self.assertIn(
            '<a href="?random=1" class="" role="button" title="Quitar del orden"><i class="fa-solid fa-ban"></i></a>',
            column_html,
        )

    def test_create_header_column_lookup_mix_complex(self):
        """Test the links creation when the request contains a previous sort and current sort is in request and has another sort after."""
        column_html = create_header_column(
            self.context_lookup_mix_complex, "field_to_sort", "column_name"
        )
        self.assertIn('<th class="column-sorted text-center">', column_html)
        self.assertIn("column_name", column_html)
        self.assertIn(
            '<a href="?random=2&amp;o=-field_to_sort&amp;random=1" role="button" title="Alternar orden"><i class="fa-solid fa-sort-up"></i></a>',
            column_html,
        )
        self.assertIn(
            '<a href="?random=2&amp;random=1" class="" role="button" title="Quitar del orden"><i class="fa-solid fa-ban"></i></a>',
            column_html,
        )
