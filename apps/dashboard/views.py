from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


class DashboardHomeView(LoginRequiredMixin, TemplateView):
    """
    Placeholder landing page for Sprint 1. Satisfies the roadmap milestone
    ("users can log in and navigate the application") without building
    the real KPI/reporting logic, which belongs to Phase 4 / Sprint 4.
    """
    template_name = "dashboard/home.html"

    def get_context_data(self, **kwargs):
        from apps.accounts.models import User

        context = super().get_context_data(**kwargs)
        context["active_user_count"] = User.objects.filter(status=User.STATUS_ACTIVE).count()
        return context
