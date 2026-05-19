from __future__ import annotations

import logging
import time
from typing import Any

import requests
from django.conf import settings

from ..schemas import (
    BlockSchema,
    BlockType,
    DatabaseSchema,
    NotionTemplate,
    PropertyDef,
    PropertyType,
)
from .decoration import guess_icon, enhance_block_emoji

logger = logging.getLogger(__name__)

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"
RATE_LIMIT_DELAY: float = 0.4

_SELECT_COLORS = [
    "default", "gray", "brown", "orange", "yellow", "green",
    "blue", "purple", "pink", "red",
]


def _build_simple_payload(prop: PropertyDef) -> dict[str, Any]:
    """Build Notion property payload for basic types (non-relation/formula/rollup)."""
    t = prop.type
    if t == PropertyType.TITLE:
        return {"title": {}}
    if t == PropertyType.RICH_TEXT:
        return {"rich_text": {}}
    if t == PropertyType.NUMBER:
        return {"number": {"format": prop.number_format or "number"}}
    if t == PropertyType.SELECT:
        options = [
            {"name": opt, "color": _SELECT_COLORS[i % len(_SELECT_COLORS)]}
            for i, opt in enumerate(prop.options or [])
        ]
        return {"select": {"options": options}}
    if t == PropertyType.MULTI_SELECT:
        options = [
            {"name": opt, "color": _SELECT_COLORS[i % len(_SELECT_COLORS)]}
            for i, opt in enumerate(prop.options or [])
        ]
        return {"multi_select": {"options": options}}
    if t == PropertyType.DATE:
        return {"date": {}}
    if t == PropertyType.CHECKBOX:
        return {"checkbox": {}}
    if t == PropertyType.URL:
        return {"url": {}}
    if t == PropertyType.EMAIL:
        return {"email": {}}
    if t == PropertyType.PHONE_NUMBER:
        return {"phone_number": {}}
    if t == PropertyType.STATUS:
        options = [
            {"name": opt, "color": _SELECT_COLORS[i % len(_SELECT_COLORS)]}
            for i, opt in enumerate(prop.options or [])
        ]
        return {"status": {"options": options}} if options else {"status": {}}
    return {"rich_text": {}}


def _build_relation_payload(db_id: str) -> dict[str, Any]:
    return {"relation": {"database_id": db_id, "single_property": {}}}


def _build_formula_payload(expression: str) -> dict[str, Any]:
    return {"formula": {"expression": expression}}


def _build_rollup_payload(
    relation_prop_name: str,
    rollup_prop_name: str,
    function: str,
) -> dict[str, Any]:
    return {
        "rollup": {
            "rollup_property_name": rollup_prop_name,
            "relation_property_name": relation_prop_name,
            "function": function,
        }
    }


class NotionClient:
    def __init__(self, token: str | None = None, page_id: str | None = None) -> None:
        self.token = token or settings.NOTION_TOKEN
        self.page_id = page_id or settings.NOTION_PAGE_ID
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Notion-Version": NOTION_VERSION,
        })
        if not self.token:
            raise ValueError("NOTION_TOKEN no configurado.")
        if not self.page_id:
            raise ValueError("NOTION_PAGE_ID no configurado.")

    def _request(
        self,
        method: str,
        endpoint: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{NOTION_API_BASE}{endpoint}"
        logger.debug("%s %s", method, url)
        response = self.session.request(method, url, json=payload)
        if response.status_code == 429:
            retry_after = float(response.headers.get("Retry-After", 1))
            logger.warning("Rate limit (429). Esperando %.1fs...", retry_after)
            time.sleep(retry_after)
            response = self.session.request(method, url, json=payload)
        if response.status_code >= 400:
            logger.error(
                "Notion API error %s: %s",
                response.status_code,
                response.text[:1000],
            )
        response.raise_for_status()
        return response.json()

    def create_database(self, schema: DatabaseSchema) -> dict[str, Any]:
        properties: dict[str, Any] = {}
        for prop_name, prop_def in schema.properties.items():
            if prop_def.type in (PropertyType.RELATION, PropertyType.FORMULA, PropertyType.ROLLUP):
                continue
            properties[prop_name] = _build_simple_payload(prop_def)

        icon_emoji = guess_icon(schema.name)
        payload = {
            "parent": {"type": "page_id", "page_id": self.page_id},
            "icon": {"type": "emoji", "emoji": icon_emoji},
            "title": [{"type": "text", "text": {"content": schema.name}}],
            "properties": properties,
        }

        logger.info("Creando DB '%s' con %d propiedades...", schema.name, len(properties))
        result = self._request("POST", "/databases", payload)
        logger.info("DB creada: %s (ID: %s)", schema.name, result.get("id", "?"))
        return result

    def _patch_properties(
        self, db_id: str, db_name: str, props: dict[str, Any],
    ) -> dict[str, Any]:
        if not props:
            return {}
        payload = {"properties": props}
        logger.info("Actualizando DB '%s' con payload: %s", db_name, payload)
        try:
            result = self._request("PATCH", f"/databases/{db_id}", payload)
            return result
        except requests.HTTPError as exc:
            logger.error(
                "Error al actualizar DB '%s': %s - %s",
                db_name, exc, exc.response.text if exc.response else "",
            )
            raise

    def update_database_properties(
        self,
        db_id: str,
        db_name: str,
        properties: dict[str, PropertyDef],
        db_name_to_id: dict[str, str],
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []

        relations: dict[str, Any] = {}
        formulas: dict[str, Any] = {}
        rollups: dict[str, Any] = {}

        for prop_name, prop_def in properties.items():
            if prop_def.type == PropertyType.RELATION:
                target_id = db_name_to_id.get(prop_def.relation_database, "")
                if target_id:
                    relations[prop_name] = _build_relation_payload(target_id)
                else:
                    relations[prop_name] = {"rich_text": {}}
                    logger.warning(
                        "DB target '%s' no encontrada para relación '%s'. Usando rich_text.",
                        prop_def.relation_database, prop_name,
                    )
            elif prop_def.type == PropertyType.FORMULA:
                if prop_def.formula_expression:
                    formulas[prop_name] = _build_formula_payload(prop_def.formula_expression)
            elif prop_def.type == PropertyType.ROLLUP:
                if prop_def.rollup_relation_property and prop_def.rollup_property:
                    rollups[prop_name] = _build_rollup_payload(
                        prop_def.rollup_relation_property,
                        prop_def.rollup_property,
                        prop_def.rollup_function,
                    )

        results.append(self._patch_properties(db_id, db_name, relations))
        time.sleep(RATE_LIMIT_DELAY)
        results.append(self._patch_properties(db_id, db_name, formulas))
        time.sleep(RATE_LIMIT_DELAY)
        results.append(self._patch_properties(db_id, db_name, rollups))

        return results

    def append_blocks(self, blocks: list[BlockSchema]) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        total = len(blocks)
        for idx, block in enumerate(blocks, start=1):
            enhanced_content = enhance_block_emoji(block.content, block.block_type.value)
            enhanced_block = BlockSchema(block_type=block.block_type, content=enhanced_content) if enhanced_content != block.content else block
            notion_block = self._build_block_payload(enhanced_block)
            payload = {"children": [notion_block]}
            logger.info("Insertando bloque %d/%d [%s]...", idx, total, block.block_type.value)
            result = self._request("PATCH", f"/blocks/{self.page_id}/children", payload)
            results.append(result)
            if idx < total:
                time.sleep(RATE_LIMIT_DELAY)
        logger.info("%d bloques insertados.", total)
        return results

    @staticmethod
    def _build_block_payload(block: BlockSchema) -> dict[str, Any]:
        block_type = block.block_type.value
        if block.block_type == BlockType.DIVIDER:
            return {"object": "block", "type": "divider", "divider": {}}
        if block.block_type == BlockType.TABLE_OF_CONTENTS:
            return {"object": "block", "type": "table_of_contents", "table_of_contents": {}}
        if block.block_type == BlockType.TO_DO:
            return {
                "object": "block", "type": "to_do",
                "to_do": {"rich_text": [{"type": "text", "text": {"content": block.content}}], "checked": False},
            }
        if block.block_type == BlockType.CALLOUT:
            callout_icon = "💡"
            content_lower = block.content.lower()
            if any(w in content_lower for w in ["bienvenido", "welcome", "hola"]):
                callout_icon = "🚀"
            elif any(w in content_lower for w in ["tip", "consejo", "sugerencia"]):
                callout_icon = "💡"
            elif any(w in content_lower for w in ["error", "problema", "cuidado"]):
                callout_icon = "⚠️"
            elif any(w in content_lower for w in ["éxito", "logro", "completado"]):
                callout_icon = "✅"
            elif any(w in content_lower for w in ["dato", "info", "información"]):
                callout_icon = "ℹ️"
            return {
                "object": "block", "type": "callout",
                "callout": {"rich_text": [{"type": "text", "text": {"content": block.content}}], "icon": {"type": "emoji", "emoji": callout_icon}},
            }
        return {
            "object": "block", "type": block_type,
            block_type: {"rich_text": [{"type": "text", "text": {"content": block.content}}]},
        }

    def deploy_template(self, template: NotionTemplate) -> dict[str, Any]:
        logger.info("Desplegando template '%s'...", template.template_name)
        result: dict[str, Any] = {
            "template_name": template.template_name,
            "databases_created": [],
            "blocks_inserted": 0,
        }

        db_name_to_id: dict[str, str] = {}

        for db_schema in template.databases:
            db_result = self.create_database(db_schema)
            db_id = db_result.get("id", "")
            db_name_to_id[db_schema.name] = db_id
            result["databases_created"].append({
                "name": db_schema.name,
                "id": db_id,
                "url": db_result.get("url"),
            })
            time.sleep(RATE_LIMIT_DELAY)

        for db_schema in template.databases:
            db_id = db_name_to_id.get(db_schema.name, "")
            if not db_id:
                continue
            self.update_database_properties(
                db_id, db_schema.name, db_schema.properties, db_name_to_id,
            )
            time.sleep(RATE_LIMIT_DELAY)

        if template.blocks:
            self.append_blocks(template.blocks)
            result["blocks_inserted"] = len(template.blocks)

        logger.info("Template desplegado: %d DBs, %d bloques", len(result["databases_created"]), result["blocks_inserted"])
        return result
