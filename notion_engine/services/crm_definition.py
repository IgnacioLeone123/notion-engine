from ..schemas import (
    BlockSchema,
    BlockType,
    DatabaseSchema,
    NotionTemplate,
    PropertyDef,
    PropertyType,
)


def build_crm() -> NotionTemplate:
    empresas_props = {
        "Nombre": PropertyDef(type=PropertyType.TITLE),
        "Industria": PropertyDef(type=PropertyType.SELECT, options=[
            "Tecnología", "Finanzas", "Salud", "Educación", "Comercio", "Consultoría", "Otro",
        ]),
        "Sitio Web": PropertyDef(type=PropertyType.URL),
        "Tamaño": PropertyDef(type=PropertyType.SELECT, options=[
            "1-10", "11-50", "51-200", "201-1000", "1000+",
        ]),
        "Contactos": PropertyDef(
            type=PropertyType.RELATION, relation_database="Contactos",
        ),
        "Oportunidades en Pipeline": PropertyDef(
            type=PropertyType.RELATION, relation_database="Pipeline de Ventas",
        ),
        "Total Oportunidades": PropertyDef(
            type=PropertyType.ROLLUP,
            rollup_database="Pipeline de Ventas",
            rollup_property="Valor Estimado",
            rollup_relation_property="Oportunidades en Pipeline",
            rollup_function="sum",
        ),
    }

    contactos_props = {
        "Nombre Completo": PropertyDef(type=PropertyType.TITLE),
        "Cargo": PropertyDef(type=PropertyType.RICH_TEXT),
        "Email": PropertyDef(type=PropertyType.EMAIL),
        "Teléfono": PropertyDef(type=PropertyType.PHONE_NUMBER),
        "Último Contacto": PropertyDef(
            type=PropertyType.ROLLUP,
            rollup_database="Historial de Interacciones",
            rollup_property="Fecha",
            rollup_relation_property="Interacciones",
            rollup_function="max",
        ),
        "Interacciones": PropertyDef(
            type=PropertyType.RELATION, relation_database="Historial de Interacciones",
        ),
    }

    pipeline_props = {
        "Nombre de la Oportunidad": PropertyDef(type=PropertyType.TITLE),
        "Etapa": PropertyDef(type=PropertyType.STATUS, options=[
            "Calificado", "Propuesta", "Negociación", "Cerrado Ganado", "Cerrado Perdido",
        ]),
        "Valor Estimado": PropertyDef(type=PropertyType.NUMBER, number_format="dollar"),
        "Fecha de Cierre Estimada": PropertyDef(type=PropertyType.DATE),
        "Valor Ponderado": PropertyDef(
            type=PropertyType.FORMULA,
            formula_expression='prop("Valor Estimado") * 0.5',
        ),
    }

    interacciones_props = {
        "Asunto": PropertyDef(type=PropertyType.TITLE),
        "Tipo": PropertyDef(type=PropertyType.SELECT, options=[
            "Reunión", "Llamada", "Email",
        ]),
        "Fecha": PropertyDef(type=PropertyType.DATE),
        "Notas": PropertyDef(type=PropertyType.RICH_TEXT),
    }

    databases = [
        DatabaseSchema(name="Empresas", properties=empresas_props),
        DatabaseSchema(name="Contactos", properties=contactos_props),
        DatabaseSchema(name="Pipeline de Ventas", properties=pipeline_props),
        DatabaseSchema(name="Historial de Interacciones", properties=interacciones_props),
    ]

    blocks = [
        BlockSchema(block_type=BlockType.CALLOUT, content="🚀 Bienvenido a tu CRM de Ventas — gestioná clientes, oportunidades e interacciones desde un solo lugar."),
        BlockSchema(block_type=BlockType.DIVIDER, content=""),
        BlockSchema(block_type=BlockType.HEADING_1, content="📊 Dashboard"),
        BlockSchema(block_type=BlockType.HEADING_2, content="📈 Totales del Pipeline"),
        BlockSchema(block_type=BlockType.PARAGRAPH, content="Vista rápida de oportunidades activas y valor estimado total."),
        BlockSchema(block_type=BlockType.DIVIDER, content=""),
        BlockSchema(block_type=BlockType.HEADING_2, content="🏢 Empresas"),
        BlockSchema(block_type=BlockType.PARAGRAPH, content="Gestioná tus cuentas, industrias y contactos vinculados."),
        BlockSchema(block_type=BlockType.HEADING_2, content="👥 Contactos"),
        BlockSchema(block_type=BlockType.PARAGRAPH, content="Base de leads y clientes con historial de interacciones."),
        BlockSchema(block_type=BlockType.HEADING_2, content="💼 Pipeline de Ventas"),
        BlockSchema(block_type=BlockType.PARAGRAPH, content="Seguimiento de oportunidades por etapa con valor ponderado."),
        BlockSchema(block_type=BlockType.HEADING_2, content="📅 Próximas Interacciones"),
        BlockSchema(block_type=BlockType.PARAGRAPH, content="Reuniones, llamadas y emails agendados."),
        BlockSchema(block_type=BlockType.DIVIDER, content=""),
        BlockSchema(block_type=BlockType.CALLOUT, content="💡 Tip: Agregá vistas Kanban al Pipeline agrupando por 'Etapa' para visualizar tu embudo de ventas."),
    ]

    return NotionTemplate(
        template_name="CRM de Ventas Completo",
        databases=databases,
        blocks=blocks,
    )
