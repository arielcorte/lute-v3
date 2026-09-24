"Theming routes."

from flask import Blueprint, Response, jsonify, request

from lute.themes.service import Service
from lute.models.repositories import UserSettingRepository
from lute.settings.current import current_settings, refresh_global_settings
from lute.db import db

bp = Blueprint("themes", __name__, url_prefix="/theme")


@bp.route("/current", methods=["GET"])
def current_theme():
    "Return current css."
    service = Service(db.session)
    response = Response(service.get_current_css(), 200)
    response.content_type = "text/css; charset=utf-8"
    return response


@bp.route("/custom_styles", methods=["GET"])
def custom_styles():
    """
    Return the custom settings for inclusion in the base.html.
    """
    repo = UserSettingRepository(db.session)
    css = repo.get_value("custom_styles")
    response = Response(css, 200)
    response.content_type = "text/css; charset=utf-8"
    return response


@bp.route("/next", methods=["POST"])
def set_next_theme():
    "Go to next theme."
    service = Service(db.session)
    service.next_theme()
    return jsonify("ok")


@bp.route("/overrides", methods=["POST"])
def set_overrides():
    """
    Set or clear the font/background colour overrides from the
    reading menu.

    JSON body: {"font_color": "#rrggbb", "background_color": "#rrggbb"}
    (either key optional), or {"reset": true} to use the theme colours.

    Returns the new override css so the page can apply it without a reload.
    """
    data = request.get_json(silent=True) or {}
    service = Service(db.session)
    try:
        if data.get("reset", False):
            service.clear_color_overrides()
        else:
            service.set_color_overrides(
                font_color=data.get("font_color"),
                background_color=data.get("background_color"),
            )
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    refresh_global_settings(db.session)
    active = (
        current_settings["override_font_color"]
        or current_settings["override_background_color"]
    )
    return jsonify({"css": service.get_override_css(), "overrides_active": active})


@bp.route("/toggle_highlight", methods=["POST"])
def toggle_highlight():
    "Fix the highlight."
    new_setting = not current_settings["show_highlights"]
    repo = UserSettingRepository(db.session)
    repo.set_value("show_highlights", new_setting)
    db.session.commit()
    current_settings["show_highlights"] = new_setting
    return jsonify("ok")
