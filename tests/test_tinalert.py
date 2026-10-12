from pathlib import Path

import pytest

from cogs.tinalert import fetch_upozorneni

FIXTURE = Path(__file__).parent / "fixtures" / "tin.html"
UL_ANCHOR = "Aktuální upozornění</H2>\n<UL>"


def parse(html: bytes | str) -> str:
    return fetch_upozorneni(html)


@pytest.fixture
def page() -> str:
    return FIXTURE.read_text(encoding="utf-8")


def test_comment_content_is_ignored(page: str) -> None:
    # Celý obsah <ul> je zabaleny v komentáři, takze výsledek je prázdný.
    assert parse(page) == ""


def test_edit_inside_comment_is_not_a_change(page: str) -> None:
    edited = page.replace("Kotek", "Kotek ZMENA")
    assert parse(page) == parse(edited)


def test_added_real_content_is_a_change(page: str) -> None:
    edited = page.replace(
        UL_ANCHOR,
        UL_ANCHOR + "\n<LI> 1. test se kona v patek 3.10. od 10:00.",
    )
    assert parse(page) != parse(edited)


def test_real_content_is_extracted(page: str) -> None:
    edited = page.replace(
        UL_ANCHOR,
        UL_ANCHOR + "\n<LI> 1. test se kona v patek 3.10. od 10:00.",
    )
    assert parse(edited) == "1. test se kona v patek 3.10. od 10:00."


def test_empty_ul() -> None:
    html = "<HTML><BODY><H2>Aktuální upozornění</H2><UL></UL><HR></BODY></HTML>"
    assert parse(html) == ""


def test_missing_heading_raises(page: str) -> None:
    without_h2 = page.replace("Aktuální upozornění", "Jiný nadpis")
    with pytest.raises(StopIteration):
        parse(without_h2)
