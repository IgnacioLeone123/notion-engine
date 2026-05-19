from __future__ import annotations

from enum import Enum
from typing import Annotated, Union

from pydantic import BaseModel, Field, model_validator


class PropertyType(str, Enum):
    TITLE = "title"
    RICH_TEXT = "rich_text"
    NUMBER = "number"
    SELECT = "select"
    MULTI_SELECT = "multi_select"
    DATE = "date"
    CHECKBOX = "checkbox"
    URL = "url"
    EMAIL = "email"
    PHONE_NUMBER = "phone_number"
    STATUS = "status"
    RELATION = "relation"
    FORMULA = "formula"
    ROLLUP = "rollup"


class BlockType(str, Enum):
    HEADING_1 = "heading_1"
    HEADING_2 = "heading_2"
    HEADING_3 = "heading_3"
    PARAGRAPH = "paragraph"
    BULLETED_LIST_ITEM = "bulleted_list_item"
    NUMBERED_LIST_ITEM = "numbered_list_item"
    TO_DO = "to_do"
    TOGGLE = "toggle"
    CALLOUT = "callout"
    QUOTE = "quote"
    DIVIDER = "divider"
    TABLE_OF_CONTENTS = "table_of_contents"


class PropertyDef(BaseModel):
    type: PropertyType
    options: list[str] = Field(default_factory=list)
    relation_database: str = ""
    formula_expression: str = ""
    rollup_database: str = ""
    rollup_property: str = ""
    rollup_relation_property: str = ""
    rollup_function: str = "sum"
    number_format: str = "number"


class DatabaseSchema(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=100)]
    properties: Annotated[dict[str, Union[str, PropertyDef]], Field(min_length=1)]

    @model_validator(mode="after")
    def normalize_and_validate(self) -> "DatabaseSchema":
        normalized = {}
        for name, value in self.properties.items():
            if isinstance(value, str):
                normalized[name] = PropertyDef(type=PropertyType(value))
            else:
                normalized[name] = value
        self.properties = normalized

        has_title = any(
            p.type == PropertyType.TITLE for p in self.properties.values()
        )
        if not has_title:
            self.properties = {
                "Nombre": PropertyDef(type=PropertyType.TITLE),
                **self.properties,
            }
        return self

    def get_property_def(self, name: str) -> PropertyDef | None:
        val = self.properties.get(name)
        if isinstance(val, PropertyDef):
            return val
        return None


class BlockSchema(BaseModel):
    block_type: Annotated[BlockType, Field()]
    content: Annotated[str, Field(default="", max_length=2000)]

    @model_validator(mode="after")
    def validate_content_required(self) -> "BlockSchema":
        no_content_types = {BlockType.DIVIDER, BlockType.TABLE_OF_CONTENTS}
        if self.block_type not in no_content_types and not self.content.strip():
            raise ValueError(
                f"El bloque '{self.block_type.value}' requiere contenido no vacío."
            )
        return self


class NotionTemplate(BaseModel):
    template_name: Annotated[str, Field(min_length=1, max_length=200)]
    databases: Annotated[list[DatabaseSchema], Field(default_factory=list)]
    blocks: Annotated[list[BlockSchema], Field(default_factory=list)]

    @model_validator(mode="after")
    def ensure_not_empty(self) -> "NotionTemplate":
        if not self.databases and not self.blocks:
            raise ValueError(
                "El template debe contener al menos una base de datos o un bloque."
            )
        return self
