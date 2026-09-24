"""
Theme service tests.
"""

import os
import pytest
from lute.themes.service import Service, build_override_css
from lute.db import db
from lute.models.repositories import UserSettingRepository


def test_list_themes(app_context):
    "Smoke test only."
    svc = Service(db.session)
    lst = svc.list_themes()
    assert len(lst) > 0, "have themes"
    assert lst[0][0] == "-", "No theme"
    assert lst[0][1] == "(default)"

    assert ("Apple_Books.css", "Apple Books") in lst


def test_default_theme_is_blank_css(app_context):
    "UserSetting starts off with blank css."
    repo = UserSettingRepository(db.session)
    assert repo.get_value("current_theme") == "-"
    svc = Service(db.session)
    assert svc.get_current_css() == "", "Default = empty string."


def test_bad_setting_returns_blank_css(app_context):
    "Just in case."
    repo = UserSettingRepository(db.session)
    repo.set_value("current_theme", "_missing_file.css")
    db.session.commit()
    svc = Service(db.session)
    assert svc.get_current_css() == "", "Missing = empty string."


def test_setting_a_theme_returns_its_css(app_context):
    "User choice is used."
    repo = UserSettingRepository(db.session)
    repo.set_value("current_theme", "Apple_Books.css")
    db.session.commit()
    svc = Service(db.session)
    assert "Georgia" in svc.get_current_css(), "font specified"


def test_next_theme_cycles_themes(app_context):
    """
    Users should be able to move the 'next' theme quickly
    while reading, via a hotkey.
    """
    svc = Service(db.session)
    lst = svc.list_themes()
    repo = UserSettingRepository(db.session)
    assert repo.get_value("current_theme") == lst[0][0]
    svc.next_theme()
    assert repo.get_value("current_theme") == lst[1][0]
    for _ in range(0, len(lst) + 10):  # pylint: disable=consider-using-enumerate
        svc.next_theme()
        svc.next_theme()
    # OK


def _delete_custom_theme_files(theme_dir):
    "Delete custom file."
    for filename in os.listdir(theme_dir):
        filepath = os.path.join(theme_dir, filename)
        if os.path.isfile(filepath):
            os.remove(filepath)


def test_custom_theme_in_theme_dir_is_available(app, app_context):
    "Can use .css file in theme dir."
    theme_dir = app.env_config.userthemespath
    _delete_custom_theme_files(theme_dir)

    mytheme_content = "p { font-size: 30pt; }"
    themefile = os.path.join(theme_dir, "my_theme.css")
    with open(themefile, "w", encoding="utf-8") as f:
        f.write(mytheme_content)

    svc = Service(db.session)
    lst = svc.list_themes()
    assert ("my_theme.css", "my theme") in lst, "Have my theme"

    repo = UserSettingRepository(db.session)
    repo.set_value("current_theme", "my_theme.css")
    db.session.commit()
    assert mytheme_content in svc.get_current_css(), "my theme used"


def test_custom_theme_in_theme_dir_appends_to_existing_theme(app, app_context):
    "Can use .css file in theme dir."
    theme_dir = app.env_config.userthemespath
    _delete_custom_theme_files(theme_dir)

    svc = Service(db.session)
    lst = svc.list_themes()
    assert ("Apple_Books.css", "Apple Books") in lst
    repo = UserSettingRepository(db.session)
    repo.set_value("current_theme", "Apple_Books.css")
    db.session.commit()
    old_content = svc.get_current_css()

    mytheme_content = "p { font-size: 30pt; }"
    themefile = os.path.join(theme_dir, "Apple_Books.css")
    with open(themefile, "w", encoding="utf-8") as f:
        f.write(mytheme_content)

    lst = svc.list_themes()
    assert ("Apple_Books.css", "Apple Books") in lst, "Have my theme"

    repo.set_value("current_theme", "Apple_Books.css")
    db.session.commit()

    new_css = old_content + "\n\n/* Additional user css */\n\n" + mytheme_content
    new_content = svc.get_current_css()
    assert new_css in new_content, "my theme used in addition to built-in"


# Appearance overrides (font colour, background colour, font).


def test_no_overrides_gives_blank_css(app_context):
    "Default settings = nothing overridden."
    svc = Service(db.session)
    assert svc.get_override_css() == ""


def test_override_css_only_includes_checked_items():
    "Unchecked items are ignored, even if they have a value."
    settings = {
        "override_font_color": True,
        "font_color": "#112233",
        "override_background_color": False,
        "background_color": "#abcdef",
    }
    css = build_override_css(settings)
    assert "body, span.textitem {\n  color: #112233;\n}" in css
    assert "--font-color:" not in css, "theme font colour kept for highlights"
    assert "span.textitem.status1" in css, "highlighted terms use theme colour"
    assert "#abcdef" not in css, "not checked"
    assert "font-family" not in css, "not checked"


def test_override_css_flags_may_be_db_strings():
    "Flags are stored as '1'/'0' strings in the db."
    settings = {"override_background_color": "1", "background_color": "#abcdef"}
    css = build_override_css(settings)
    assert "--background-color: #abcdef;" in css
    assert "background-color: #abcdef;" in css
    assert "span.textitem.status1" not in css, "only needed for font colour"

    settings = {"override_background_color": "0", "background_color": "#abcdef"}
    assert build_override_css(settings) == ""


def test_override_css_ignores_bad_colours():
    "Only #rrggbb values are rendered."
    for bad in ["red", "#abc", "#12345g", "", None, "#123456; } body { x"]:
        settings = {"override_font_color": True, "font_color": bad}
        assert build_override_css(settings) == "", bad


def test_override_css_font_family_is_cleaned():
    "Font family applies to the body and reading text; css chars stripped."
    settings = {
        "override_font_family": True,
        "font_family": 'Georgia, "Times New Roman"',
    }
    css = build_override_css(settings)
    assert 'body, span.textitem {\n  font-family: Georgia, "Times New Roman";\n}' in css

    settings = {"override_font_family": True, "font_family": "Georgia; } body { x: y"}
    css = build_override_css(settings)
    assert ";" not in css.replace("font-family: Georgia  body  x y;", "")
    assert "{ x" not in css

    settings = {"override_font_family": True, "font_family": "  "}
    assert build_override_css(settings) == "", "blank font = nothing"


def test_set_color_overrides_saves_and_switches_on(app_context):
    "Setting a colour from the reading menu switches its override on."
    svc = Service(db.session)
    svc.set_color_overrides(background_color="#abcdef")
    repo = UserSettingRepository(db.session)
    assert repo.get_value("background_color") == "#abcdef"
    assert repo.get_value("override_background_color") == "1"
    assert repo.get_value("override_font_color") == "0", "untouched"
    assert "#abcdef" in svc.get_override_css()

    svc.set_color_overrides(font_color="#112233")
    css = svc.get_override_css()
    assert "#abcdef" in css and "#112233" in css, "both kept"


def test_set_color_overrides_rejects_bad_colour(app_context):
    "Bad values raise, nothing saved."
    svc = Service(db.session)
    with pytest.raises(ValueError):
        svc.set_color_overrides(font_color="red")
    assert svc.get_override_css() == ""


def test_clear_color_overrides_keeps_colours_but_switches_off(app_context):
    "Reset = theme colours again; the last picked colours are kept."
    svc = Service(db.session)
    svc.set_color_overrides(font_color="#112233", background_color="#abcdef")
    svc.clear_color_overrides()
    assert svc.get_override_css() == ""
    repo = UserSettingRepository(db.session)
    assert repo.get_value("font_color") == "#112233"
    assert repo.get_value("override_font_color") == "0"
