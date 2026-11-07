from datetime import date

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from receipts.services import get_or_create_receipt
from tenants.models import Tenancy
from tenants.services import get_next_period_start
from .forms import PaymentForm
from .models import Payment


def _tenancy_next_period_map():
    return {
        str(tenancy.pk): get_next_period_start(tenancy).isoformat()
        for tenancy in Tenancy.objects.all()
    }


def _tenancy_monthly_rent_map():
    return {str(tenancy.pk): int(tenancy.agreed_monthly_rent) for tenancy in Tenancy.objects.all()}


class PaymentListView(LoginRequiredMixin, ListView):
    model = Payment
    template_name = "payments/payment_list.html"
    context_object_name = "payments"
    paginate_by = 25

    def get_queryset(self):
        qs = super().get_queryset().select_related(
            "tenancy", "tenancy__tenant", "tenancy__unit", "tenancy__unit__property", "receipt"
        )
        params = self.request.GET
        if params.get("tenant"):
            qs = qs.filter(tenancy__tenant__full_name__icontains=params["tenant"])
        if params.get("property"):
            qs = qs.filter(tenancy__unit__property_id=params["property"])
        if params.get("date_from"):
            qs = qs.filter(payment_date__gte=params["date_from"])
        if params.get("date_to"):
            qs = qs.filter(payment_date__lte=params["date_to"])
        return qs

    def get_context_data(self, **kwargs):
        from core.models import Property

        context = super().get_context_data(**kwargs)
        context["properties"] = Property.objects.all()
        return context


class PaymentDetailView(LoginRequiredMixin, DetailView):
    model = Payment
    template_name = "payments/payment_detail.html"
    context_object_name = "payment"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["shares"] = self.object.shares.all()
        return context


class PaymentCreateView(LoginRequiredMixin, CreateView):
    model = Payment
    form_class = PaymentForm
    template_name = "payments/payment_form.html"
    extra_context = {"title": "Record payment"}

    def get_initial(self):
        initial = super().get_initial()
        initial["payment_date"] = date.today()
        tenancy_pk = self.request.GET.get("tenancy")
        if tenancy_pk:
            initial["tenancy"] = tenancy_pk
        else:
            last_payment = Payment.objects.order_by("-created_at").first()
            if last_payment:
                initial["tenancy"] = last_payment.tenancy_id
        return initial

    def form_valid(self, form):
        tenancy = form.cleaned_data["tenancy"]
        if not tenancy.is_active and not form.cleaned_data.get("confirm_inactive"):
            form.add_error(
                None,
                "This tenancy is inactive. Tick 'Record anyway' below to confirm and save.",
            )
            return self.render_to_response(
                self.get_context_data(form=form, show_inactive_confirm=True)
            )
        form.instance.recorded_by = self.request.user
        response = super().form_valid(form)
        get_or_create_receipt(self.object)
        messages.success(self.request, "Payment recorded and receipt generated.")
        return response

    def get_success_url(self):
        return reverse("payment_detail", args=[self.object.pk])

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            **kwargs,
            **self.extra_context,
            tenancy_next_period_map=_tenancy_next_period_map(),
            tenancy_monthly_rent_map=_tenancy_monthly_rent_map(),
        )


class PaymentUpdateView(LoginRequiredMixin, UpdateView):
    model = Payment
    form_class = PaymentForm
    template_name = "payments/payment_form.html"

    def get_success_url(self):
        return reverse("payment_detail", args=[self.object.pk])

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            **kwargs,
            title="Edit payment",
            tenancy_next_period_map=_tenancy_next_period_map(),
            tenancy_monthly_rent_map=_tenancy_monthly_rent_map(),
        )


class PaymentDeleteView(LoginRequiredMixin, DeleteView):
    model = Payment
    template_name = "generic_confirm_delete.html"
    success_url = reverse_lazy("payment_list")
