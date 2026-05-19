from __future__ import annotations

import json
import logging
from typing import Any

from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .services.llm_service import generate_template
from .services.notion_service import NotionClient

logger = logging.getLogger(__name__)


def _creds(request):
    s = request.session
    body = getattr(request, "data", {})
    return {
        "notion_token": body.get("notion_token") or s.get("notion_token") or None,
        "page_id": body.get("page_id") or s.get("page_id") or None,
        "openai_key": body.get("openai_key") or s.get("openai_key") or None,
        "openai_base": s.get("openai_base") or None,
        "llm_model": s.get("llm_model") or None,
    }


def dashboard(request):
    return render(request, "notion_engine/dashboard.html")


@api_view(["POST"])
def save_settings(request):
    s = request.session
    s["notion_token"] = request.data.get("notion_token", "")
    s["page_id"] = request.data.get("page_id", "")
    s["openai_key"] = request.data.get("openai_key", "")
    s["openai_base"] = request.data.get("openai_base", "https://api.groq.com/openai/v1")
    s["llm_model"] = request.data.get("llm_model", "llama-3.3-70b-versatile")
    return Response({"status": "ok"})


class TemplateGeneratorView(APIView):
    def post(self, request: Request) -> Response:
        creds = _creds(request)
        prompt = request.data.get("prompt")
        if not prompt or not prompt.strip():
            return Response(
                {"status": "error", "message": "El campo 'prompt' es requerido."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            template = generate_template(
                prompt.strip(),
                openai_key=creds["openai_key"],
                openai_base=creds["openai_base"],
                llm_model=creds["llm_model"],
            )
        except ValueError as exc:
            return Response(
                {"status": "error", "phase": "llm_generation", "message": str(exc)},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        except Exception as exc:
            logger.exception("Error inesperado en LLM")
            return Response(
                {"status": "error", "phase": "llm_generation", "message": f"Error de comunicación con el LLM: {exc}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        try:
            client = NotionClient(token=creds["notion_token"], page_id=creds["page_id"])
            deploy_result = client.deploy_template(template)
        except ValueError as exc:
            return Response(
                {"status": "error", "phase": "notion_config", "message": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except Exception as exc:
            logger.exception("Error al desplegar en Notion")
            return Response(
                {"status": "error", "phase": "notion_deploy", "message": f"Error al desplegar en Notion: {exc}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response({"status": "success", **deploy_result}, status=status.HTTP_201_CREATED)


class TemplatePreviewView(APIView):
    def post(self, request: Request) -> Response:
        creds = _creds(request)
        prompt = request.data.get("prompt")
        if not prompt or not prompt.strip():
            return Response(
                {"status": "error", "message": "El campo 'prompt' es requerido."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            template = generate_template(
                prompt.strip(),
                openai_key=creds["openai_key"],
                openai_base=creds["openai_base"],
                llm_model=creds["llm_model"],
            )
        except ValueError as exc:
            return Response({"status": "error", "message": str(exc)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        except Exception as exc:
            return Response({"status": "error", "message": f"Error LLM: {exc}"}, status=status.HTTP_502_BAD_GATEWAY)

        return Response({"status": "preview", "template": template.model_dump(mode="json")}, status=status.HTTP_200_OK)


class HealthCheckView(APIView):
    def get(self, request: Request) -> Response:
        return Response({"status": "healthy", "service": "Notion Template Engine", "version": "1.0.0"}, status=status.HTTP_200_OK)


def _deploy_common(request, build_fn):
    creds = _creds(request)
    try:
        template = build_fn()
        client = NotionClient(token=creds["notion_token"], page_id=creds["page_id"])
        result = client.deploy_template(template)
        return Response({"status": "success", **result}, status=status.HTTP_201_CREATED)
    except Exception as exc:
        logger.exception("Error al desplegar plantilla")
        return Response({"status": "error", "message": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
@csrf_exempt
def deploy_crm(request):
    from .services.crm_definition import build_crm
    return _deploy_common(request, build_crm)


@api_view(["POST"])
@csrf_exempt
def deploy_finance(request):
    from .services.finance_definition import build_finance_system
    return _deploy_common(request, build_finance_system)
