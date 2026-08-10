from django.conf import settings

from .models import Pruefart


def app_version(request):
    return {
        "APP_VERSION": settings.APP_VERSION
    }


def wartung_pruefarten(request):
    return {
        "wartung_pruefarten": (
            Pruefart.objects
            .filter(aktiv=True)
            .order_by("order", "name")
        )
    }