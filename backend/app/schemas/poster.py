from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PosterGenerateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    poster_type: str | None = Field(None, alias="posterType")
    template_id: int | None = Field(None, alias="templateId")
    related_id: int | None = Field(None, alias="relatedId")
    custom_data: dict[str, Any] | None = Field(None, alias="customData")
