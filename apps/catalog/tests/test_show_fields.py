import pytest

from ..factories import ShowFactory

pytestmark = pytest.mark.django_db


def test_new_show_fields_are_optional():
    show = ShowFactory()
    show.refresh_from_db()

    assert show.group_name == ""
    assert show.performers == ""
    assert not show.rider_file


def test_show_keeps_group_name_distinct_from_title():
    show = ShowFactory(title="Nuits d'été", group_name="Les Nocturnes", performers="Julie, Marc")
    show.refresh_from_db()

    assert show.title == "Nuits d'été"
    assert show.group_name == "Les Nocturnes"
    assert show.performers == "Julie, Marc"
