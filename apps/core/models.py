from django.db import models
from django.db.models import Func


class TimeStampedModel(models.Model):
    """
    A model to reuse the `created_at` and `updated_at` fields
    """

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# ! Skipped from coverage until used
class SingletonModel(models.Model):  # pragma: no cover
    """Model to handele single row models."""

    def delete(self, *args, **kwargs):
        """Avoids instance from being deleted."""
        pass

    @classmethod
    def load(cls):
        """Create an instance or returns the existing one."""
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

    def save(self, *args, **kwargs):
        """Save the instance without create new ones."""
        self.pk = 1
        super().save(*args, **kwargs)

    class Meta:
        abstract = True


class Round2(Func):
    """Util to handle Database round with precision. Can be drop in django 4.0.
    https://docs.djangoproject.com/en/4.0/releases/4.0/#models:~:text=The%20new%20precision%20argument%20of%20the%20Round()%20database%20function%20allows%20specifying%20the%20number%20of%20decimal%20places%20after%20rounding.
    """

    function = "ROUND"
    template = "%(function)s(%(expressions)s, 2)"
