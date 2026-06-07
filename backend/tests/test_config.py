from __future__ import annotations

import pytest

from app.core.config import Settings


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("postgres://u:p@h:5432/db", "postgresql+psycopg://u:p@h:5432/db"),
        ("postgresql://u:p@h/db", "postgresql+psycopg://u:p@h/db"),
        ("postgresql+psycopg://u:p@h/db", "postgresql+psycopg://u:p@h/db"),
    ],
)
def test_database_url_normalized_for_psycopg(raw: str, expected: str) -> None:
    assert Settings(database_url=raw).database_url == expected


def test_cors_origin_list_parsing() -> None:
    assert Settings(cors_origins="*").cors_origin_list == ["*"]
    assert Settings(cors_origins="  ").cors_origin_list == ["*"]
    assert Settings(cors_origins="https://a.com, https://b.com").cors_origin_list == [
        "https://a.com",
        "https://b.com",
    ]
