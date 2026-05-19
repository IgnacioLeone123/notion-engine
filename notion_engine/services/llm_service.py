"""
Notion Engine — LLM Service
=============================
Orquesta la comunicación con el LLM para transformar texto plano
del usuario en un NotionTemplate JSON validado por Pydantic.

Compatible con OpenAI y proveedores locales (Ollama, LiteLLM).
"""
from __future__ import annotations

import json
import logging
import re

from django.conf import settings
from openai import OpenAI
from pydantic import ValidationError

from ..schemas import NotionTemplate

logger = logging.getLogger(__name__)

# ── System Prompt para el LLM ────────────────────────────
_SYSTEM_PROMPT = """Sos un experto en Notion. Generá una plantilla JSON.

REGLAS:
1. Respondé SOLO con JSON válido, nada más.
2. Usá esta estructura exacta:
{
  "template_name": "Nombre del template",
  "databases": [
    {
      "name": "Nombre BD",
      "properties": {
        "Nombre": "title",
        "Estado": "select",
        "Fecha": "date"
      }
    }
  ],
  "blocks": [
    {"block_type": "heading_1", "content": "Titulo"},
    {"block_type": "paragraph", "content": "Descripcion"},
    {"block_type": "divider", "content": ""}
  ]
}
3. Cada DB necesita al menos una propiedad "title".
4. Tipos de propiedad: title, rich_text, number, select, multi_select, date, checkbox, url, email, phone_number, status, relation.
5. Tipos de bloque: heading_1, heading_2, heading_3, paragraph, bulleted_list_item, numbered_list_item, to_do, toggle, callout, quote, divider.
6. Los divider usan content vacio.
7. USA EMOJIS en todos los nombres de DB, nombres de propiedades y contenidos de bloques. Cada base de datos debe tener un emoji representativo al inicio de su nombre.
8. Los callouts deben comenzar con emoji relevante.
9. Usa bloques heading_1 y heading_2 para estructurar secciones, divider para separar areas, y callout para tips o bienvenida.
10. Genera algo profesional, estetico y completo segun lo que pida el usuario."""


def _get_client(api_key: str | None = None, base_url: str | None = None) -> OpenAI:
    return OpenAI(
        api_key=api_key or settings.OPENAI_API_KEY,
        base_url=base_url or settings.OPENAI_BASE_URL,
    )


def _extract_json(text: str) -> dict:
    """
    Extrae y parsea JSON del texto del LLM tolerando:
    - Markdown ```json ... ``` blocks
    - Texto extra antes/después del JSON
    - Single quotes en vez de double quotes
    - Trailing commas
    """
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if match:
        text = match.group(1).strip()

    brace_start = text.find("{")
    brace_end = text.rfind("}")
    if brace_start != -1 and brace_end != -1:
        text = text[brace_start : brace_end + 1]

    for attempt in range(3):
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            if attempt == 2:
                pos = exc.pos
                ctx_start = max(0, pos - 60)
                ctx_end = min(len(text), pos + 60)
                raise ValueError(
                    f"Error parseando JSON en posición {pos}: {exc.msg}\n"
                    f"Contexto: ...{text[ctx_start:ctx_end]}..."
                ) from exc
        if attempt == 0:
            text = text.replace("'", '"')
        elif attempt == 1:
            text = re.sub(r",\s*([\]}])", r"\1", text)


_BLOCK_TYPE_ALIASES = {
    "bullet": "bulleted_list_item",
    "number": "numbered_list_item",
    "todo": "to_do",
    "heading": "heading_1",
    "h1": "heading_1",
    "h2": "heading_2",
    "h3": "heading_3",
}


_EMOJI_SHORTCODES: dict[str, str] = {
    ":star:": "⭐", ":rocket:": "🚀", ":heart:": "❤️", ":thought_balloon:": "💭",
    ":bulb:": "💡", ":warning:": "⚠️", ":check:": "✅", ":x:": "❌",
    ":fire:": "🔥", ":muscle:": "💪", ":tada:": "🎉", ":clap:": "👏",
    ":ok_hand:": "👍", ":thumbsup:": "👍", ":thumbsdown:": "👎",
    ":smile:": "😊", ":sweat_smile:": "😅", ":joy:": "😂", ":cry:": "😢",
    ":pensive:": "😔", ":angry:": "😠", ":heart_eyes:": "😍",
    ":calendar:": "📅", ":clock:": "🕐", ":alarm_clock:": "⏰",
    ":book:": "📖", ":books:": "📚", ":notebook:": "📓", ":page_facing_up:": "📄",
    ":clipboard:": "📋", ":file_folder:": "📁", ":open_file_folder:": "📂",
    ":computer:": "💻", ":desktop:": "🖥️", ":phone:": "📱", ":iphone:": "📱",
    ":email:": "📧", ":envelope:": "✉️", ":inbox_tray:": "📥", ":outbox_tray:": "📤",
    ":chart:": "📊", ":bar_chart:": "📊", ":line_chart:": "📈", ":chart_with_upwards_trend:": "📈",
    ":moneybag:": "💰", ":dollar:": "💵", ":credit_card:": "💳",
    ":house:": "🏠", ":office:": "🏢", ":school:": "🏫",
    ":bike:": "🚲", ":car:": "🚗", ":airplane:": "✈️",
    ":dog:": "🐶", ":cat:": "🐱", ":fox:": "🦊", ":bear:": "🐻",
    ":sunny:": "☀️", ":cloud:": "☁️", ":rain:": "🌧️", ":snowflake:": "❄️",
    ":moon:": "🌙", ":earth:": "🌍", ":globe:": "🌐",
    ":checkered_flag:": "🏁", ":flag:": "🚩", ":trophy:": "🏆",
    ":medal:": "🥇", ":gift:": "🎁", ":balloon:": "🎈",
    ":pencil:": "✏️", ":memo:": "📝", ":pen:": "🖊️",
    ":link:": "🔗", ":gear:": "⚙️", ":wrench:": "🔧", ":hammer:": "🔨",
    ":lock:": "🔒", ":unlock:": "🔓", ":key:": "🔑",
    ":mag:": "🔍", ":magnifying_glass:": "🔍", ":binoculars:": "🔭",
    ":cog:": "⚙️", ":tools:": "🛠️", ":wastebasket:": "🗑️",
    ":speech_balloon:": "💬", ":thought_balloon:": "💭", ":zzz:": "💤",
    ":wave:": "👋", ":pray:": "🙏", ":folded_hands:": "🙏",
    ":100:": "💯", ":sparkles:": "✨", ":dizzy:": "💫", ":boom:": "💥",
    ":exclamation:": "❗", ":question:": "❓", ":grey_exclamation:": "❕", ":grey_question:": "❔",
    ":heavy_check_mark:": "✔️", ":heavy_multiplication_x:": "✖️",
    ":arrows_clockwise:": "🔄", ":arrows_counterclockwise:": "🔄",
    ":white_check_mark:": "✅", ":ballot_box_with_check:": "☑️",
    ":zap:": "⚡", ":electric_plug:": "🔌", ":bulb:": "💡",
    ":bath:": "🛀", ":bathtub:": "🛁", ":shower:": "🚿",
    ":two_men_holding_hands:": "👬", ":two_women_holding_hands:": "👭",
    ":couple:": "👫", ":family:": "👪", ":man-woman-boy:": "👨‍👩‍👦",
    ":heart:": "❤️", ":blue_heart:": "💙", ":green_heart:": "💚",
    ":yellow_heart:": "💛", ":purple_heart:": "💜", ":black_heart:": "🖤",
    ":broken_heart:": "💔", ":two_hearts:": "💕", ":sparkling_heart:": "💖",
    ":pensar:": "🤔", ":think:": "🤔", ":thinking:": "🤔",
    ":corazon:": "❤️", ":corazón:": "❤️", ":emoji:": "😊",
    ":brain:": "🧠", ":mind:": "🧠", ":exploding_head:": "🤯",
    ":nerd:": "🤓", ":nerd_face:": "🤓", ":star_struck:": "🤩",
    ":smiling_face_with_3_hearts:": "🥰", ":hug:": "🤗", ":kissing_heart:": "😘",
    ":see_no_evil:": "🙈", ":hear_no_evil:": "🙉", ":speak_no_evil:": "🙊",
    ":raised_hands:": "🙌", ":handshake:": "🤝", ":fist:": "✊",
    ":muscle:": "💪", ":flexed_biceps:": "💪", ":leg:": "🦵", ":foot:": "🦶",
    ":ear:": "👂", ":nose:": "👃", ":eye:": "👁️", ":eyes:": "👀",
    ":tongue:": "👅", ":lips:": "👄", ":skull:": "💀", ":ghost:": "👻",
    ":alien:": "👽", ":robot:": "🤖", ":smiley:": "😃",
    ":grinning:": "😀", ":grin:": "😁", ":joy:": "😂",
    ":rofl:": "🤣", ":smile:": "😊", ":sweat_smile:": "😅",
    ":laughing:": "😆", ":wink:": "😉", ":blush:": "😊",
    ":innocent:": "😇", ":angel:": "😇", ":slightly_smiling:": "🙂",
    ":upside_down:": "🙃", ":relieved:": "😌", ":heart_eyes:": "😍",
    ":kissing:": "😗", ":kissing_closed_eyes:": "😚", ":kissing_smiling_eyes:": "😙",
    ":yum:": "😋", ":stuck_out_tongue:": "😛", ":stuck_out_tongue_winking_eye:": "😜",
    ":stuck_out_tongue_closed_eyes:": "😝", ":money_mouth:": "🤑",
    ":hugging:": "🤗", ":thinking_face:": "🤔", ":face_with_raised_eyebrow:": "🤨",
    ":neutral_face:": "😐", ":expressionless:": "😑", ":no_mouth:": "😶",
    ":face_with_rolling_eyes:": "🙄", ":smirk:": "😏", ":persevere:": "😣",
    ":disappointed_relieved:": "😥", ":open_mouth:": "😮", ":zipper_mouth:": "🤐",
    ":hushed:": "😯", ":sleepy:": "😪", ":tired_face:": "😫",
    ":sleeping:": "😴", ":mask:": "😷", ":face_with_thermometer:": "🤒",
    ":face_with_head_bandage:": "🤕", ":nauseated_face:": "🤢",
    ":sneezing_face:": "🤧", ":dizzy_face:": "😵", ":woozy:": "🥴",
    ":face_with_cowboy_hat:": "🤠", ":sunglasses:": "😎", ":nerd_face:": "🤓",
    ":confused:": "😕", ":worried:": "😟", ":slightly_frowning:": "🙁",
    ":white_frowning_face:": "☹️", ":frowning:": "😦", ":anguished:": "😧",
    ":fearful:": "😨", ":cold_sweat:": "😰", ":disappointed:": "😞",
    ":cry:": "😢", ":sob:": "😭", ":scream:": "😱",
    ":astonished:": "😲", ":flushed:": "😳", ":face_with_medical_mask:": "😷",
    ":hot_face:": "🥵", ":cold_face:": "🥶", ":pleading_face:": "🥺",
    ":liar:": "🤥", ":shushing_face:": "🤫", ":face_with_hand_over_mouth:": "🤭",
    ":yawning_face:": "🥱",     ":drooling_face:": "🤤", ":face_in_clouds:": "😶‍🌫️",
}


def _replace_shortcodes(text: str) -> str:
    for code, emoji in _EMOJI_SHORTCODES.items():
        text = text.replace(code, emoji)
    return text


_PROPERTY_ALIASES = {
    "text": "rich_text",
    "paragraph": "rich_text",
    "parrafo": "rich_text",
    "richtext": "rich_text",
    "phone": "phone_number",
    "tel": "phone_number",
    "telefono": "phone_number",
    "multi": "multi_select",
    "multiple": "multi_select",
    "check": "checkbox",
    "bool": "checkbox",
    "boolean": "checkbox",
    "true/false": "checkbox",
    "int": "number",
    "float": "number",
    "currency": "number",
    "moneda": "number",
    "money": "number",
    "dollar": "number",
    "pesos": "number",
    "porcentaje": "number",
    "percent": "number",
    "relation": "relation",
    "relacion": "relation",
    "vinculo": "relation",
    "person": "rich_text",
    "people": "rich_text",
    "persona": "rich_text",
    "personas": "rich_text",
    "tag": "multi_select",
    "etiqueta": "multi_select",
    "label": "select",
    "category": "select",
    "categoria": "select",
    "tipo": "select",
    "type": "select",
    "priority": "select",
    "prioridad": "select",
    "frequency": "select",
    "frecuencia": "select",
    "progress": "number",
    "progreso": "number",
    "percentage": "number",
    "score": "number",
    "puntuacion": "number",
    "rating": "number",
    "calificacion": "number",
    "count": "number",
    "conteo": "number",
    "quantity": "number",
    "cantidad": "number",
    "duration": "number",
    "duracion": "number",
    "hours": "number",
    "horas": "number",
    "minutes": "number",
    "minutos": "number",
    "link": "url",
    "enlace": "url",
    "website": "url",
    "web": "url",
    "site": "url",
    "pagina": "url",
}


def _normalize_raw_data(data: dict) -> dict:
    for db in data.get("databases", []):
        db["name"] = _replace_shortcodes(db.get("name", ""))
        normalized = {}
        for name, value in db.get("properties", {}).items():
            clean_name = _replace_shortcodes(name)
            if isinstance(value, dict):
                type_val = value.get("type", "")
                mapped = _PROPERTY_ALIASES.get(type_val.lower(), type_val) if type_val else str(value)
                normalized[clean_name] = mapped
            else:
                mapped = _PROPERTY_ALIASES.get(value.lower(), value) if isinstance(value, str) else value
                normalized[clean_name] = mapped
        db["properties"] = normalized

    for block in data.get("blocks", []):
        bt = block.get("block_type", "")
        if bt in _BLOCK_TYPE_ALIASES:
            block["block_type"] = _BLOCK_TYPE_ALIASES[bt]
        content = block.get("content", "")
        block["content"] = _replace_shortcodes(content) if content else content
        if not block.get("content", "").strip() and block.get("block_type") not in ("divider", "table_of_contents"):
            block["content"] = block["block_type"].replace("_", " ").title()
        if "icon" in block:
            del block["icon"]

    return data


def generate_template(
    user_prompt: str,
    openai_key: str | None = None,
    openai_base: str | None = None,
    llm_model: str | None = None,
) -> NotionTemplate:
    """
    Envía el prompt del usuario al LLM y devuelve un NotionTemplate validado.
    """
    client = _get_client(api_key=openai_key, base_url=openai_base)
    model = llm_model or settings.LLM_MODEL
    logger.info("Enviando prompt al LLM (modelo=%s): %.100s...", model, user_prompt)

    response = client.chat.completions.create(
        model=model,
        temperature=0.7,
        max_tokens=8192,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )

    raw_content = response.choices[0].message.content
    if not raw_content:
        raise ValueError("El LLM devolvió una respuesta vacía.")

    logger.info("Respuesta cruda del LLM (primeros 300 chars): %.300s", raw_content)

    raw_data = _extract_json(raw_content)
    raw_data = _normalize_raw_data(raw_data)

    try:
        template = NotionTemplate.model_validate(raw_data)
    except ValidationError as exc:
        logger.error("Validación Pydantic falló para raw_data: %s", raw_data)
        raise ValueError(
            f"El JSON del LLM no cumple el esquema requerido:\n{exc}"
        ) from exc

    logger.info(
        "Template '%s' generado: %d DBs, %d bloques",
        template.template_name,
        len(template.databases),
        len(template.blocks),
    )
    return template
