from django.core.management.base import BaseCommand

from notion_engine.services.crm_definition import build_crm
from notion_engine.services.notion_service import NotionClient


class Command(BaseCommand):
    help = "Despliega el CRM de Ventas completo en Notion"

    def handle(self, *args, **options):
        self.stdout.write("Construyendo CRM de Ventas...")
        template = build_crm()
        self.stdout.write(f"Template: {template.template_name}")
        self.stdout.write(f"Bases de datos: {len(template.databases)}")
        self.stdout.write(f"Bloques: {len(template.blocks)}")

        self.stdout.write("\nDesplegando en Notion...")
        client = NotionClient()
        result = client.deploy_template(template)

        self.stdout.write(self.style.SUCCESS("\n✅ CRM desplegado exitosamente!"))
        for db in result["databases_created"]:
            self.stdout.write(f"  📦 {db['name']}: {db['url']}")
        self.stdout.write(f"  📝 Bloques insertados: {result['blocks_inserted']}")
