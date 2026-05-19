from ..schemas import (
    BlockSchema,
    BlockType,
    DatabaseSchema,
    NotionTemplate,
    PropertyDef,
    PropertyType,
)


def build_finance_system() -> NotionTemplate:
    ingresos_props = {
        "Nombre": PropertyDef(type=PropertyType.TITLE),
        "Monto": PropertyDef(type=PropertyType.NUMBER, number_format="dollar"),
        "Categoría": PropertyDef(type=PropertyType.SELECT, options=[
            "Sueldo", "Freelance", "Inversiones",
        ]),
        "Fecha": PropertyDef(type=PropertyType.DATE),
    }

    gastos_props = {
        "Nombre": PropertyDef(type=PropertyType.TITLE),
        "Monto": PropertyDef(type=PropertyType.NUMBER, number_format="dollar"),
        "Categoría": PropertyDef(type=PropertyType.SELECT, options=[
            "Comida", "Transporte", "Ocio",
        ]),
        "Pagado": PropertyDef(type=PropertyType.CHECKBOX),
    }

    metas_props = {
        "Nombre": PropertyDef(type=PropertyType.TITLE),
        "Monto Actual": PropertyDef(type=PropertyType.NUMBER, number_format="dollar"),
        "Monto Objetivo": PropertyDef(type=PropertyType.NUMBER, number_format="dollar"),
        "Progreso": PropertyDef(
            type=PropertyType.FORMULA,
            formula_expression='concat(format(round(prop("Monto Actual") / prop("Monto Objetivo") * 100)), "%")',
        ),
        "Fecha Límite": PropertyDef(type=PropertyType.DATE),
    }

    databases = [
        DatabaseSchema(name="💰 Registro de Ingresos", properties=ingresos_props),
        DatabaseSchema(name="💸 Control de Gastos", properties=gastos_props),
        DatabaseSchema(name="🎯 Metas de Ahorro", properties=metas_props),
    ]

    blocks = [
        BlockSchema(block_type=BlockType.CALLOUT, content="💡 CENTRO DE CONTROL FINANCIERO — Gestioná ingresos, gastos y metas desde un único dashboard inteligente."),
        BlockSchema(block_type=BlockType.DIVIDER, content=""),
        BlockSchema(block_type=BlockType.HEADING_1, content="📊 Dashboard Principal"),
        BlockSchema(block_type=BlockType.PARAGRAPH, content="Resumen financiero inteligente con métricas clave y progreso de ahorro."),
        BlockSchema(block_type=BlockType.DIVIDER, content=""),
        BlockSchema(block_type=BlockType.HEADING_2, content="💰 Balance Total"),
        BlockSchema(block_type=BlockType.PARAGRAPH, content="Suma de todos tus ingresos menos gastos. Mantené un balance positivo."),
        BlockSchema(block_type=BlockType.DIVIDER, content=""),
        BlockSchema(block_type=BlockType.HEADING_2, content="💸 Gastos del Mes"),
        BlockSchema(block_type=BlockType.PARAGRAPH, content="Controlá tus gastos por categoría y mantené tu presupuesto."),
        BlockSchema(block_type=BlockType.DIVIDER, content=""),
        BlockSchema(block_type=BlockType.HEADING_2, content="🎯 Progreso de Ahorro"),
        BlockSchema(block_type=BlockType.PARAGRAPH, content="Seguimiento visual de tus metas financieras con porcentaje completado."),
        BlockSchema(block_type=BlockType.DIVIDER, content=""),
        BlockSchema(block_type=BlockType.HEADING_3, content="📋 Resumen de Bases de Datos"),
        BlockSchema(block_type=BlockType.PARAGRAPH, content="Usá las bases de datos de abajo para registrar ingresos, gastos y metas."),
        BlockSchema(block_type=BlockType.DIVIDER, content=""),
        BlockSchema(block_type=BlockType.CALLOUT, content="💡 Tip: Actualizá 'Monto Actual' en cada meta para ver tu progreso automáticamente."),
    ]

    return NotionTemplate(
        template_name="Sistema Inteligente de Finanzas Personales",
        databases=databases,
        blocks=blocks,
    )
