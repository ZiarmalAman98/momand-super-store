from django.urls import reverse_lazy
from django.views.generic import FormView, TemplateView

from .forms import ContactMessageForm


class HomeView(TemplateView):
    template_name = "storefront/home.html"


class ServicesView(TemplateView):
    template_name = "storefront/services.html"


class ContactView(FormView):
    template_name = "storefront/contact.html"
    form_class = ContactMessageForm
    success_url = reverse_lazy("storefront:contact_success")

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)


class ContactSuccessView(TemplateView):
    template_name = "storefront/contact_success.html"
