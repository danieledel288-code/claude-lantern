"""Generate the hal/john/guy presets and their Claude Code color themes.

Edit LANTERNS below, then run: python build_presets.py
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
PRESETS = os.path.join(HERE, "presets")
CC_THEMES = os.path.join(HERE, "cc-themes")
USAGE = {"show_remaining": True, "five_hour": "ring power", "seven_day": "lantern battery",
         "cost_suffix": "willpower spent"}
LABELS = {"model": "corps: ", "dir": "sector: "}

# 4-row emblems rasterized with quarter blocks (2x2 sub-pixels per cell) so
# the ring comes out round; emblem.py generates the ring, and each Lantern
# changes only its inside.
HAL_ART = ["▀▀▀▀▀██████▀▀▀▀▀", "    ▟▛    ▜▙    ", "    ▜▙    ▟▛    ", "▄▄▄▄▄██████▄▄▄▄▄"]
JOHN_ART = ["▀▀▀▀▀██████▀▀▀▀▀", "    ▟▛ ▄▄ ▜▙    ", "    ▜▙ ▀▀ ▟▛    ", "▄▄▄▄▄██████▄▄▄▄▄"]  # solid core
GUY_ART = ["▀▀▀▀▀██████▀▀▀▀▀", "    ▟▛ ▛▀ ▜▙    ", "    ▜▙ ▙█ ▟▛    ", "▄▄▄▄▄██████▄▄▄▄▄"]  # his G

ANNOUNCEMENT = ("In brightest day, in blackest night, no evil shall escape my sight."
                " ~ If you can will it, create it.")

LANTERNS = {
    "hal": {
        "description": "Hal Jordan: fearless test pilot, classic ring, emerald with a turquoise edge",
        "cc": {"name": "Hal Jordan", "accent": "#1aff8c", "border": "#109a55", "soft": "#8cffc4"},
        "colors": {"text": "38;5;48", "separator": "38;5;29"},
        "wave": [26, 255, 140],
        # The classic emblem: two bars and a hollow ring.
        "art": HAL_ART,
        "verbs": ["Flying by the seat of my pants", "Ignoring the Guardians", "Going full throttle",
                  "Test-piloting", "Pulling a barrel roll", "Overcoming great fear",
                  "Breaking protocol", "Pushing past Mach 3", "Charging the ring",
                  "Reciting the oath", "Winging it", "Patrolling Sector 2814"],
        "moods": {
            "critical": "\U0001F6A8 running on fumes, back to the lantern (/handoff)",
            "warning": "⚠️ constructs flickering",
            "starting": "\U0001F48D suiting up",
            "blasting": "\U0001F4A5 full throttle, no fear",
            "busy": "✈️ flying on instinct",
            "working": "✨ winging it",
            "idle": "\U0001F30C patrolling sector 2814",
        },
    },
    "john": {
        "description": "John Stewart: the architect, solid never-hollow constructs, turquoise",
        "cc": {"name": "John Stewart", "accent": "#14e0c0", "border": "#0a8a76", "soft": "#8ff2e2"},
        "colors": {"text": "38;5;43", "separator": "38;5;30"},
        "wave": [20, 224, 192],
        # His constructs are never hollow, so the ring gets a solid core.
        "art": JOHN_ART,
        "verbs": ["Drafting blueprints", "Building it bolt by bolt", "Measuring twice",
                  "Laying the foundation", "Engineering a construct", "Reinforcing load-bearing walls",
                  "Running the numbers", "Following the Marine playbook", "Surveying the site",
                  "Filling in every rivet", "Raising the frame", "Holding the line"],
        "moods": {
            "critical": "\U0001F6A8 structure failing, rebuild at the lantern (/handoff)",
            "warning": "⚠️ nearing load limit",
            "starting": "\U0001F4D0 reviewing the blueprints",
            "blasting": "\U0001F3D7️ raising the whole skyline",
            "busy": "\U0001F9F1 constructing, bolt by bolt",
            "working": "\U0001F4CF drafting",
            "idle": "\U0001F6E1️ standing watch over sector 2814",
        },
    },
    "guy": {
        "description": "Guy Gardner: loudmouth ex-sergeant, G-marked ring, acid lime",
        "cc": {"name": "Guy Gardner", "accent": "#9dff00", "border": "#5c9400", "soft": "#d4ff8a"},
        "colors": {"text": "38;5;118", "separator": "38;5;64"},
        "wave": [157, 255, 0],
        # His ring carries a G.
        "art": GUY_ART,
        "verbs": ["Mouthing off", "Picking a fight", "Throwing a construct punch",
                  "Being the best Lantern", "Out-yelling Hal", "Not taking orders",
                  "Busting heads", "Showing the rookies how it's done", "Cracking knuckles",
                  "Ignoring the chain of command", "Flexing", "Running Warriors"],
        "moods": {
            "critical": "\U0001F6A8 ring's gassed, somebody get me a lantern (/handoff)",
            "warning": "⚠️ this ring's getting cranky",
            "starting": "\U0001F624 who woke me up",
            "blasting": "\U0001F44A kicking everybody's butt",
            "busy": "\U0001F4AA showing Hal how it's done",
            "working": "\U0001F94A throwing punches",
            "idle": "\U0001F37A kicking back at Warriors",
        },
    },
}

for slug, L in LANTERNS.items():
    preset = {
        "description": L["description"],
        "cliTheme": f"custom:{slug}",
        "spinnerVerbs": L["verbs"],
        "colors": L["colors"],
        "wave": L["wave"],
        "moods": L["moods"],
        "usage": USAGE,
        "labels": LABELS,
        "corner_art": L["art"],
        "announcement": ANNOUNCEMENT,
    }
    with open(os.path.join(PRESETS, f"{slug}.json"), "w", encoding="utf-8") as f:
        json.dump(preset, f, indent=2, ensure_ascii=False)

    c = L["cc"]
    cc_theme = {
        "name": c["name"],
        "base": "dark",
        "overrides": {
            "claude": c["accent"],
            "claudeShimmer": c["soft"],  # lighter half of the spinner-word shimmer
            "clawd_body": c["accent"],  # the mascot (undocumented token, found in the binary)
            "promptBorder": c["border"],
            "permission": c["accent"],
            "suggestion": c["soft"],
            "remember": c["border"],
            "rate_limit_fill": c["accent"],
            "success": c["accent"],
        },
    }
    with open(os.path.join(CC_THEMES, f"{slug}.json"), "w", encoding="utf-8") as f:
        json.dump(cc_theme, f, indent=2, ensure_ascii=False)

print("presets written")
