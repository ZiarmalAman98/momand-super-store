from django.urls import path

from . import views

app_name = "storefront"

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path("services/", views.ServicesView.as_view(), name="services"),
    path("contact/", views.ContactView.as_view(), name="contact"),
    path("contact/sent/", views.ContactSuccessView.as_view(), name="contact_success"),
]
