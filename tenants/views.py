from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from .forms import TenancyForm, TenantForm
from .models import Tenancy, Tenant
from .services import get_tenancy_balance


class TenantListView(LoginRequiredMixin, ListView):
    model = Tenant
    template_name = "tenants/tenant_list.html"
    context_object_name = "tenants"

    def get_queryset(self):
        qs = super().get_queryset()
        search = self.request.GET.get("q")
        if search:
            qs = qs.filter(full_name__icontains=search)
        return qs


class TenantDetailView(LoginRequiredMixin, DetailView):
    model = Tenant
    template_name = "tenants/tenant_detail.html"
    context_object_name = "tenant"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenancies = []
        for tenancy in self.object.tenancies.select_related("unit", "unit__property").all():
            tenancies.append((tenancy, get_tenancy_balance(tenancy)))
        context["tenancies"] = tenancies
        context["access_links"] = self.object.access_links.all()
        return context


class TenantCreateView(LoginRequiredMixin, CreateView):
    model = Tenant
    form_class = TenantForm
    template_name = "generic_form.html"
    success_url = reverse_lazy("tenant_list")
    extra_context = {"title": "Add tenant"}

    def get_context_data(self, **kwargs):
        return super().get_context_data(**kwargs, **self.extra_context)


class TenantUpdateView(LoginRequiredMixin, UpdateView):
    model = Tenant
    form_class = TenantForm
    template_name = "generic_form.html"

    def get_success_url(self):
        return reverse("tenant_detail", args=[self.object.pk])

    def get_context_data(self, **kwargs):
        return super().get_context_data(**kwargs, title=f"Edit {self.object.full_name}")


class TenantDeleteView(LoginRequiredMixin, DeleteView):
    model = Tenant
    template_name = "generic_confirm_delete.html"
    success_url = reverse_lazy("tenant_list")


class TenancyCreateView(LoginRequiredMixin, CreateView):
    model = Tenancy
    form_class = TenancyForm
    template_name = "generic_form.html"
    extra_context = {"title": "Add tenancy"}

    def get_initial(self):
        initial = super().get_initial()
        tenant_pk = self.request.GET.get("tenant")
        if tenant_pk:
            initial["tenant"] = tenant_pk
        return initial

    def get_success_url(self):
        return reverse("tenant_detail", args=[self.object.tenant.pk])

    def get_context_data(self, **kwargs):
        return super().get_context_data(**kwargs, **self.extra_context)


class TenancyUpdateView(LoginRequiredMixin, UpdateView):
    model = Tenancy
    form_class = TenancyForm
    template_name = "generic_form.html"

    def get_success_url(self):
        return reverse("tenant_detail", args=[self.object.tenant.pk])

    def get_context_data(self, **kwargs):
        return super().get_context_data(**kwargs, title=f"Edit tenancy for {self.object.tenant}")


class TenancyDeleteView(LoginRequiredMixin, DeleteView):
    model = Tenancy
    template_name = "generic_confirm_delete.html"

    def get_success_url(self):
        return reverse("tenant_detail", args=[self.object.tenant.pk])
