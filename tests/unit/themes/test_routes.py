"""
Theme route tests: appearance overrides.
"""

import json
import pytest
from lute.db import db
from lute.models.repositories import UserSettingRepository
from lute.settings.current import current_settings
from tests.utils import make_book


def _post_overrides(client, data):
    "Post json to the overrides route."
    return client.post(
        "/theme/overrides", data=json.dumps(data), content_type="application/json"
    )


@pytest.fixture(name="read_page")
def fixture_read_page(app_context, spanish):
    "Url of a reading page."
    b = make_book("Hola", "Hola amigo.", spanish)
    db.session.add(b)
    db.session.commit()
    return f"/read/{b.id}/page/1"


def test_reading_page_renders_override_css_after_theme(client, read_page):
    "The override css is rendered on the reading page, after the theme."
    resp = _post_overrides(client, {"background_color": "#abcdef"})
    assert resp.status_code == 200
    assert resp.json["overrides_active"] is True
    assert "--background-color: #abcdef;" in resp.json["css"]

    resp = client.get(read_page)
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert "--background-color: #abcdef;" in html
    theme_pos = html.index('href="/theme/custom_styles"')
    override_pos = html.index('<style id="user_appearance_overrides">')
    assert override_pos > theme_pos, "overrides after theme and custom styles"


def test_other_pages_keep_the_theme(client):
    "Overrides are for the reading screen only."
    _post_overrides(client, {"background_color": "#abcdef"})
    for url in ["/", "/settings/index"]:
        html = client.get(url).data.decode("utf-8")
        assert "user_appearance_overrides" not in html, url


def test_overrides_are_saved_in_settings(app, client):
    "Colours persist, and the global settings are refreshed."
    _post_overrides(client, {"font_color": "#112233"})
    with app.app_context():
        repo = UserSettingRepository(db.session)
        assert repo.get_value("font_color") == "#112233"
        assert repo.get_value("override_font_color") == "1"
    assert current_settings["override_font_color"] is True
    assert current_settings["font_color"] == "#112233"


def test_reset_overrides(client, read_page):
    "Reset switches the overrides off."
    _post_overrides(client, {"font_color": "#112233", "background_color": "#abcdef"})
    resp = _post_overrides(client, {"reset": True})
    assert resp.status_code == 200
    assert resp.json == {"css": "", "overrides_active": False}
    html = client.get(read_page).data.decode("utf-8")
    assert '<style id="user_appearance_overrides"></style>' in html


def test_bad_colour_is_rejected(client):
    "Bad data = 400, nothing saved."
    resp = _post_overrides(client, {"font_color": "not-a-colour"})
    assert resp.status_code == 400
    assert "Invalid colour" in resp.json["error"]
    assert current_settings["override_font_color"] is False


def test_settings_form_saves_overrides(client, read_page):
    "The settings page saves the override fields."
    resp = client.get("/settings/index")
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert 'type="color"' in html, "colour pickers rendered"

    formdata = {
        "backup_enabled": "y",
        "backup_dir": "/tmp",
        "backup_count": "5",
        "current_theme": "-",
        "custom_styles": "",
        "override_font_color": "y",
        "font_color": "#112233",
        "background_color": "#ffffff",
        "override_font_family": "y",
        "font_family": "Georgia, serif",
        "stats_calc_sample_size": "5",
        "japanese_reading": "hiragana",
        "ankiconnect_url": "http://127.0.0.1:8765",
    }
    resp = client.post("/settings/index", data=formdata)
    assert resp.status_code == 302, "redirect on success"

    html = client.get(read_page).data.decode("utf-8")
    assert "body, span.textitem {\n  color: #112233;" in html
    assert "font-family: Georgia, serif;" in html
    assert "--background-color" not in html, "not checked"
