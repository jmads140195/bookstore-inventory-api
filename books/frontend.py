import gettext

import pycountry
from django.conf import settings
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET


@require_GET
@never_cache
def inventory_app(request):
    translate = gettext.translation("iso3166-1", pycountry.LOCALES_DIR, languages=["es"], fallback=True).gettext
    countries = sorted(({"code": country.alpha_2, "name": translate(country.name)}
                        for country in pycountry.countries), key=lambda country: country["name"])
    response = render(request, "books/inventory.html", {"countries": countries, "currency": settings.LOCAL_CURRENCY})
    response["Content-Security-Policy"] = (
        "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
        "font-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
    )
    response["Referrer-Policy"] = "same-origin"
    return response
