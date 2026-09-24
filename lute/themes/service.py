"""
Theming service.

Themes are stored in the css folder, current theme in UserSetting.

Users can also override a few things (font colour, background
colour, font) on the reading page, on top of whatever theme is
active; those are stored in UserSettings and rendered as css
after the theme.
"""

import os
import re
from glob import glob
from flask import current_app
from lute.models.repositories import UserSettingRepository

default_entry = ("-", "(default)")

HEX_COLOR_REGEX = r"^#[0-9a-fA-F]{6}$"

# Characters allowed in a user-supplied font-family value.
_FONT_FAMILY_ALLOWED = r"[^A-Za-z0-9 ,'\"_-]"


def is_hex_color(value):
    "True if value is a #rrggbb string."
    return isinstance(value, str) and re.match(HEX_COLOR_REGEX, value) is not None


def clean_font_family(value):
    "Strip anything that isn't a plain font name, quote, comma or space."
    return re.sub(_FONT_FAMILY_ALLOWED, "", value or "").strip(" ,")


def _is_on(value):
    "Setting flags are stored as strings, but may already be bools."
    return value in (True, 1, "1")


def build_override_css(settings):
    """
    Build the css for the user's appearance overrides.

    settings is a dict of user settings (e.g. current_settings).
    Only overrides whose "override_" flag is set, and whose value is
    valid, are included.  Returns "" if nothing is overridden.
    """
    body_rules = []
    if _is_on(settings.get("override_background_color")):
        c = settings.get("background_color")
        if is_hex_color(c):
            body_rules.append(f"  --background-color: {c};")
            body_rules.append(f"  background-color: {c};")

    # Rules for the body and the reading text.  span.textitem is
    # targeted explicitly as themes set its font and colour.
    text_rules = []
    if _is_on(settings.get("override_font_color")):
        c = settings.get("font_color")
        if is_hex_color(c):
            text_rules.append(f"  color: {c};")
    if _is_on(settings.get("override_font_family")):
        ff = clean_font_family(settings.get("font_family"))
        if ff != "":
            text_rules.append(f"  font-family: {ff};")

    if len(body_rules) == 0 and len(text_rules) == 0:
        return ""

    lines = ["/* User appearance overrides (Settings > Appearance). */"]
    if len(body_rules) > 0:
        lines += ["body {"] + body_rules + ["}"]
    if len(text_rules) > 0:
        lines += ["body, span.textitem {"] + text_rules + ["}"]
    if any(r.startswith("  color:") for r in text_rules):
        # Highlighted terms keep the theme's font colour: the theme's
        # highlight colours were chosen for it, not for the override.
        # --font-color is deliberately not overridden for this reason.
        lines += [
            "span.textitem.status0, span.textitem.status1, span.textitem.status2,",
            "span.textitem.status3, span.textitem.status4, span.textitem.status5,",
            "span.textitem.newmultiterm {",
            "  color: var(--font-color);",
            "}",
        ]
    return "\n".join(lines) + "\n"


class Service:
    "Service."

    def __init__(self, session):
        self.session = session

    def _css_path(self):
        """
        Path to css in this folder.
        """
        thisdir = os.path.dirname(__file__)
        theme_dir = os.path.join(thisdir, "css")
        return os.path.abspath(theme_dir)

    def list_themes(self):
        """
        List of theme file names and user-readable name.
        """

        def _make_display_name(s):
            ret = os.path.basename(s)
            ret = ret.replace(".css", "").replace("_", " ")
            return ret

        g = glob(os.path.join(self._css_path(), "*.css"))
        themes = [(os.path.basename(f), _make_display_name(f)) for f in g]
        theme_basenames = [t[0] for t in themes]

        g = glob(os.path.join(current_app.env_config.userthemespath, "*.css"))
        additional_user_themes = [
            (os.path.basename(f), _make_display_name(f))
            for f in g
            if os.path.basename(f) not in theme_basenames
        ]

        themes += additional_user_themes
        sorted_themes = sorted(themes, key=lambda x: x[1])
        return [default_entry] + sorted_themes

    def get_current_css(self):
        """
        Return the current css pointed at by the current_theme user setting.
        """
        repo = UserSettingRepository(self.session)
        current_theme = repo.get_value("current_theme")
        if current_theme == default_entry[0]:
            return ""

        def _get_theme_css_in_dir(d):
            "Get css, or '' if no file."
            fname = os.path.join(d, current_theme)
            if not os.path.exists(fname):
                return ""
            with open(fname, "r", encoding="utf-8") as f:
                return f.read()

        ret = _get_theme_css_in_dir(self._css_path())
        add = _get_theme_css_in_dir(current_app.env_config.userthemespath)
        if add != "":
            ret += f"\n\n/* Additional user css */\n\n{add}"
        return ret

    def get_override_css(self):
        "Return the css for the user's appearance overrides."
        repo = UserSettingRepository(self.session)
        keys = [
            "override_background_color",
            "background_color",
            "override_font_color",
            "font_color",
            "override_font_family",
            "font_family",
        ]
        settings = {k: repo.get_value(k) for k in keys}
        return build_override_css(settings)

    def set_color_overrides(self, font_color=None, background_color=None):
        """
        Set the font and/or background colour overrides, and
        switch them on.  Raises ValueError for bad colours.
        """
        repo = UserSettingRepository(self.session)
        for key, val in [
            ("font_color", font_color),
            ("background_color", background_color),
        ]:
            if val is None:
                continue
            if not is_hex_color(val):
                raise ValueError(f"Invalid colour {val}")
            repo.set_value(key, val)
            repo.set_value(f"override_{key}", True)
        self.session.commit()

    def clear_color_overrides(self):
        "Switch off the colour overrides; the theme colours are used again."
        repo = UserSettingRepository(self.session)
        repo.set_value("override_font_color", False)
        repo.set_value("override_background_color", False)
        self.session.commit()

    def next_theme(self):
        """
        Move to the next theme in the list of themes.
        """
        repo = UserSettingRepository(self.session)
        current_theme = repo.get_value("current_theme")
        themes = [t[0] for t in self.list_themes()]
        themes.append(default_entry[0])
        for i in range(0, len(themes)):  # pylint: disable=consider-using-enumerate
            if themes[i] == current_theme:
                new_index = i + 1
                break
        repo.set_value("current_theme", themes[new_index])
        self.session.commit()
