from django.apps import AppConfig


class StudentsConfig(AppConfig):
    name = 'students'

    def ready(self):
        # Keeps class enrollment counts in sync with student changes
        from . import signals  # noqa: F401
