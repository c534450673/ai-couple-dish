from datetime import datetime

import pytest

from app.core.errors import BusinessError
from app.db import models
from app.schemas.poster import PosterGenerateRequest
from app.services import poster


def test_poster_models_match_existing_tables_without_schema_changes() -> None:
    template_columns = set(models.PosterTemplate.__table__.columns.keys())
    poster_columns = set(models.UserPoster.__table__.columns.keys())

    assert template_columns == {
        "id",
        "template_code",
        "template_name",
        "template_type",
        "template_config",
        "preview_url",
        "is_active",
        "create_time",
    }
    assert poster_columns == {
        "id",
        "user_id",
        "couple_id",
        "poster_type",
        "template_id",
        "poster_url",
        "invite_code",
        "is_deleted",
        "create_time",
    }


def test_generate_schema_preserves_spring_camel_case_contract() -> None:
    request = PosterGenerateRequest.model_validate(
        {
            "posterType": "annual",
            "templateId": 9,
            "relatedId": 2026,
            "customData": {"title": "我们的 2026", "futureKey": {"accepted": True}},
        }
    )

    assert request.model_dump(by_alias=True) == {
        "posterType": "annual",
        "templateId": 9,
        "relatedId": 2026,
        "customData": {"title": "我们的 2026", "futureKey": {"accepted": True}},
    }


def test_generate_input_requires_type_or_template_and_validates_known_fields() -> None:
    with pytest.raises(BusinessError) as empty:
        poster.validate_generate_input(PosterGenerateRequest(), current_year=2026)
    assert (empty.value.code, empty.value.message) == (9001, "参数无效")

    valid = poster.validate_generate_input(
        PosterGenerateRequest(
            posterType="annual",
            relatedId=2026,
            customData={
                "title": "我们的 2026",
                "subtitle": "一起走过的这一年",
                "imageUrl": "/api/uploads/user/1/year.png",
                "unknown": "ignored",
            },
        ),
        current_year=2026,
    )
    assert valid.poster_type == "annual"
    assert valid.related_id == 2026
    assert valid.title == "我们的 2026"
    assert valid.subtitle == "一起走过的这一年"
    assert valid.image_url == "/api/uploads/user/1/year.png"


@pytest.mark.parametrize(
    "payload",
    [
        PosterGenerateRequest(posterType="unknown"),
        PosterGenerateRequest(posterType="annual", templateId=0),
        PosterGenerateRequest(posterType="annual", relatedId=1999),
        PosterGenerateRequest(posterType="annual", relatedId=2027),
        PosterGenerateRequest(posterType="annual", customData={str(i): i for i in range(33)}),
        PosterGenerateRequest(
            posterType="annual", customData={"a": {"b": {"c": {"d": "too deep"}}}}
        ),
        PosterGenerateRequest(posterType="annual", customData={"title": "字" * 41}),
        PosterGenerateRequest(posterType="annual", customData={"subtitle": "字" * 81}),
        PosterGenerateRequest(posterType="annual", customData={"imageUrl": "x" * 513}),
        PosterGenerateRequest(posterType="annual", customData={"title": 123}),
        PosterGenerateRequest(posterType="annual", customData={"payload": "x" * 8200}),
    ],
)
def test_generate_input_rejects_bounded_resource_violations(
    payload: PosterGenerateRequest,
) -> None:
    with pytest.raises(BusinessError) as error:
        poster.validate_generate_input(payload, current_year=2026)

    assert (error.value.code, error.value.message) == (9001, "参数无效")


def test_poster_dto_uses_resolved_template_and_stable_type_names() -> None:
    item = models.UserPoster(
        id=88,
        user_id=7,
        couple_id=3,
        poster_type="anniversary",
        template_id=11,
        poster_url="/api/uploads/poster/user/7/2026/07/26/id.png",
        invite_code="A1B2C3D4",
        is_deleted=0,
        create_time=datetime(2026, 7, 26, 9, 30, 0),
    )

    assert poster.poster_dto(item, {11: "纪念日模板"}) == {
        "id": 88,
        "posterType": "anniversary",
        "posterTypeName": "纪念日",
        "templateId": 11,
        "templateName": "纪念日模板",
        "posterUrl": "/api/uploads/poster/user/7/2026/07/26/id.png",
        "inviteCode": "A1B2C3D4",
        "createTime": "2026-07-26T09:30:00",
    }


def test_invite_code_is_eight_uppercase_alphanumeric_characters() -> None:
    values = {poster.generate_invite_code() for _ in range(32)}

    assert len(values) > 1
    assert all(len(value) == 8 and value.isalnum() and value == value.upper() for value in values)
