from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("apps.dashboard.urls")),
    path("accounts/", include("apps.accounts.urls")),
    path("inventory/", include("apps.inventory.urls")),
    path("stock/", include("apps.stock.urls")),
    path("customers/", include("apps.customers.urls")),
    path("sales/", include("apps.sales.urls")),
    path("suppliers/", include("apps.suppliers.urls")),
    path("purchases/", include("apps.purchases.urls")),
    path("reports/", include("apps.reports.urls")),
    path("settings/", include("apps.settings_app.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
