from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from core.models import Property
from .forms import ExpenseCategoryForm, ExpenseForm
from .models import Expense, ExpenseCategory


class ExpenseListView(LoginRequiredMixin, ListView):
    model = Expense
    template_name = "expenses/expense_list.html"
    context_object_name = "expenses"
    paginate_by = 25

    def get_queryset(self):
        qs = super().get_queryset().select_related("property", "unit", "category")
        params = self.request.GET
        if params.get("property"):
            qs = qs.filter(property_id=params["property"])
        if params.get("category"):
            qs = qs.filter(category_id=params["category"])
        if params.get("date_from"):
            qs = qs.filter(date__gte=params["date_from"])
        if params.get("date_to"):
            qs = qs.filter(date__lte=params["date_to"])
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["properties"] = Property.objects.all()
        context["categories"] = ExpenseCategory.objects.all()
        return context


class ExpenseCreateView(LoginRequiredMixin, CreateView):
    model = Expense
    form_class = ExpenseForm
    template_name = "generic_form.html"
    success_url = reverse_lazy("expense_list")
    extra_context = {"title": "Record expense"}

    def form_valid(self, form):
        form.instance.recorded_by = self.request.user
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        return super().get_context_data(**kwargs, **self.extra_context)


class ExpenseUpdateView(LoginRequiredMixin, UpdateView):
    model = Expense
    form_class = ExpenseForm
    template_name = "generic_form.html"
    success_url = reverse_lazy("expense_list")

    def get_context_data(self, **kwargs):
        return super().get_context_data(**kwargs, title="Edit expense")


class ExpenseDeleteView(LoginRequiredMixin, DeleteView):
    model = Expense
    template_name = "generic_confirm_delete.html"
    success_url = reverse_lazy("expense_list")


class ExpenseCategoryListView(LoginRequiredMixin, ListView):
    model = ExpenseCategory
    template_name = "expenses/category_list.html"
    context_object_name = "categories"


class ExpenseCategoryCreateView(LoginRequiredMixin, CreateView):
    model = ExpenseCategory
    form_class = ExpenseCategoryForm
    template_name = "generic_form.html"
    success_url = reverse_lazy("expense_category_list")
    extra_context = {"title": "Add expense category"}

    def get_context_data(self, **kwargs):
        return super().get_context_data(**kwargs, **self.extra_context)


class ExpenseCategoryUpdateView(LoginRequiredMixin, UpdateView):
    model = ExpenseCategory
    form_class = ExpenseCategoryForm
    template_name = "generic_form.html"
    success_url = reverse_lazy("expense_category_list")

    def get_context_data(self, **kwargs):
        return super().get_context_data(**kwargs, title="Edit expense category")


class ExpenseCategoryDeleteView(LoginRequiredMixin, DeleteView):
    model = ExpenseCategory
    template_name = "generic_confirm_delete.html"
    success_url = reverse_lazy("expense_category_list")
