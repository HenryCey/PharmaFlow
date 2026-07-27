"""Makes pharmacy settings (name, logo, currency symbol) available to
every template without every view having to fetch it explicitly —
used by the header/sidebar and by any page displaying a price."""
from .models import PharmacySettings


def pharmacy_settings(request):
    return {"pharmacy_settings": PharmacySettings.load()}
