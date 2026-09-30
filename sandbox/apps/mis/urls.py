from django.urls import path

from . import views

app_name = "mis"

urlpatterns = [path("", views.dashboard, name="dashboard")]
