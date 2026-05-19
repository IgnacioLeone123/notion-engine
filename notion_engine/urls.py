"""
Notion Engine — URL Routing
=============================
Rutas del módulo montadas bajo /api/v1/notion/ (ver config/urls.py).
"""
from django.urls import path

from .views import HealthCheckView, TemplateGeneratorView, TemplatePreviewView, deploy_crm, deploy_finance, save_settings

app_name = "notion_engine"

urlpatterns = [
    path("generate/", TemplateGeneratorView.as_view(), name="generate"),
    path("preview/", TemplatePreviewView.as_view(), name="preview"),
    path("health/", HealthCheckView.as_view(), name="health"),
    path("deploy-crm/", deploy_crm, name="deploy-crm"),
    path("deploy-finance/", deploy_finance, name="deploy-finance"),
    path("save-settings/", save_settings, name="save-settings"),
]
