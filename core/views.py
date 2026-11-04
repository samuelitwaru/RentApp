from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView, View

from .forms import LandlordProfileForm, PropertyForm, UnitForm, UserDetailsForm, UserProfileForm
from .models import LandlordProfile, Property, Unit, UserProfile


class HomeView(View):
    def get(self, request):
        if request.user.is_authenticated:
            return redirect("dashboard")
        return redirect("login")


class LandlordSettingsView(LoginRequiredMixin, View):
    template_name = "generic_form.html"

    def get(self, request):
        form = LandlordProfileForm(instance=LandlordProfile.get_solo())
        return self._render(request, form)

    def post(self, request):
        form = LandlordProfileForm(request.POST, request.FILES, instance=LandlordProfile.get_solo())
        if form.is_valid():
            form.save()
            messages.success(request, "Settings updated.")
            return redirect("landlord_settings")
        return self._render(request, form)

    def _render(self, request, form):
        from django.shortcuts import render

        return render(
            request,
            self.template_name,
            {"form": form, "title": "Landlord settings", "cancel_url": reverse("dashboard")},
        )


class ProfileView(LoginRequiredMixin, View):
    template_name = "core/profile.html"

    def get(self, request):
        profile = UserProfile.get_for_user(request.user)
        user_form = UserDetailsForm(instance=request.user)
        profile_form = UserProfileForm(instance=profile)
        return self._render(request, user_form, profile_form, profile)

    def post(self, request):
        profile = UserProfile.get_for_user(request.user)
        user_form = UserDetailsForm(request.POST, instance=request.user)
        profile_form = UserProfileForm(request.POST, request.FILES, instance=profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, "Profile updated.")
            return redirect("profile")
        return self._render(request, user_form, profile_form, profile)

    def _render(self, request, user_form, profile_form, profile):
        from django.shortcuts import render

        return render(
            request,
            self.template_name,
            {"user_form": user_form, "profile_form": profile_form, "profile": profile},
        )


class PropertyListView(LoginRequiredMixin, ListView):
    model = Property
    template_name = "core/property_list.html"
    context_object_name = "properties"

    def get_queryset(self):
        qs = super().get_queryset().prefetch_related("units")
        search = self.request.GET.get("q")
        if search:
            qs = qs.filter(name__icontains=search)
        return qs


class PropertyDetailView(LoginRequiredMixin, DetailView):
    model = Property
    template_name = "core/property_detail.html"
    context_object_name = "property"


class PropertyCreateView(LoginRequiredMixin, CreateView):
    model = Property
    form_class = PropertyForm
    template_name = "generic_form.html"
    success_url = reverse_lazy("property_list")
    extra_context = {"title": "Add property"}

    def get_context_data(self, **kwargs):
        return super().get_context_data(**kwargs, **self.extra_context)


class PropertyUpdateView(LoginRequiredMixin, UpdateView):
    model = Property
    form_class = PropertyForm
    template_name = "generic_form.html"

    def get_success_url(self):
        return reverse("property_detail", args=[self.object.pk])

    def get_context_data(self, **kwargs):
        return super().get_context_data(**kwargs, title=f"Edit {self.object.name}")


class PropertyDeleteView(LoginRequiredMixin, DeleteView):
    model = Property
    template_name = "generic_confirm_delete.html"
    success_url = reverse_lazy("property_list")


class UnitCreateView(LoginRequiredMixin, CreateView):
    model = Unit
    form_class = UnitForm
    template_name = "generic_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.property = get_object_or_404(Property, pk=kwargs["property_pk"])
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.property = self.property
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("property_detail", args=[self.property.pk])

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            **kwargs, title=f"Add unit to {self.property.name}", cancel_url=self.get_success_url()
        )


class UnitUpdateView(LoginRequiredMixin, UpdateView):
    model = Unit
    form_class = UnitForm
    template_name = "generic_form.html"

    def get_success_url(self):
        return reverse("property_detail", args=[self.object.property.pk])

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            **kwargs, title=f"Edit {self.object}", cancel_url=self.get_success_url()
        )


class UnitDeleteView(LoginRequiredMixin, DeleteView):
    model = Unit
    template_name = "generic_confirm_delete.html"

    def get_success_url(self):
        return reverse("property_detail", args=[self.object.property.pk])
