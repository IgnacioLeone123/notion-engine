"""
Notion Engine — Root URL Configuration
========================================
Punto de entrada único que delega al router de notion_engine.
"""
from django.urls import path, include

from notion_engine.views import dashboard

urlpatterns = [
    path("", dashboard, name="dashboard"),
    path("api/v1/notion/", include("notion_engine.urls")),
]
