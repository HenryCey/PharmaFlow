from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from apps.reports.services import dashboard_service


class DashboardHomeView(LoginRequiredMixin, TemplateView):
    """
    Sprint 5: the placeholder landing page from Sprint 1 is replaced with
    real business statistics. Every figure comes from DashboardService —
    this view's only job is auth + handing the request's user through for
    row-level scoping (Cashiers see their own sales in Today's Sales /
    Recent Sales, same visibility rule Sales History already applies).

    No new permission is required to view the dashboard itself — it's the
    landing page every role sees after login, per the Blueprint's default
    roles. The individual Reports pages (Sprint 5, next increment) are
    where view_*_reports permissions actually gate access.
    """
    template_name = "dashboard/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(dashboard_service.dashboard_context(user=self.request.user))
        return context
