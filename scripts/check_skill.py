"""Validate the files needed to install and display this Skill."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

import yaml

SKILL_SUBDIR = "."
EXPECTED_NAME = "learn-flow-skill"


def read_text(path: Path) -> str:
    if not path.is_file():
        raise ValueError(f"Missing required file: {path}")
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        raise ValueError(f"Required file is empty: {path}")
    return text


def require_mapping(value: object, label: str) -> dict:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a YAML mapping")
    return value


def require_string(data: dict, field: str, label: str) -> str:
    value = data.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label}.{field} must be a non-empty string")
    return value


def check(root: Path) -> None:
    for filename in ("README.md", "LICENSE"):
        read_text(root / filename)

    skill_dir = (root / SKILL_SUBDIR).resolve()
    skill_text = read_text(skill_dir / "SKILL.md")
    lines = skill_text.splitlines()
    if lines[0] != "---" or "---" not in lines[1:]:
        raise ValueError("SKILL.md must begin with YAML front matter between --- lines")
    end = lines.index("---", 1)
    metadata = require_mapping(yaml.safe_load("\n".join(lines[1:end])), "SKILL.md")
    name = require_string(metadata, "name", "SKILL.md")
    if name != EXPECTED_NAME:
        raise ValueError(f"Skill name must be {EXPECTED_NAME!r}, got {name!r}")
    require_string(metadata, "description", "SKILL.md")
    if not "\n".join(lines[end + 1:]).strip():
        raise ValueError("SKILL.md must contain instructions after its front matter")

    config = require_mapping(
        yaml.safe_load(read_text(skill_dir / "agents" / "openai.yaml")),
        "agents/openai.yaml",
    )
    interface = require_mapping(config.get("interface"), "interface")
    for field in ("display_name", "short_description", "default_prompt"):
        require_string(interface, field, "interface")
    if f"${EXPECTED_NAME}" not in interface["default_prompt"]:
        raise ValueError("interface.default_prompt must reference this Skill using $name")

    if "policy" in config:
        policy = require_mapping(config["policy"], "policy")
        if "allow_implicit_invocation" in policy:
            if not isinstance(policy["allow_implicit_invocation"], bool):
                raise ValueError("policy.allow_implicit_invocation must be true or false")

    for field in ("icon_small", "icon_large"):
        if field not in interface:
            continue
        relative = require_string(interface, field, "interface")
        icon = (skill_dir / relative).resolve()
        if Path(relative).is_absolute() or not icon.is_relative_to(skill_dir):
            raise ValueError(f"interface.{field} must point inside the Skill directory")
        if not icon.is_file() or not icon.read_bytes():
            raise ValueError(f"Missing or empty icon: {relative}")
        if icon.suffix.lower() == ".svg":
            if ET.parse(icon).getroot().tag != "{http://www.w3.org/2000/svg}svg":
                raise ValueError(f"Icon is not a namespaced SVG document: {relative}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[1],
        help="Repository directory to validate (defaults to this script's repository)",
    )
    args = parser.parse_args()
    try:
        check(args.root.resolve())
    except (OSError, ValueError, yaml.YAMLError, ET.ParseError) as error:
        print(f"Skill check failed: {error}", file=sys.stderr)
        return 1
    print(f"Skill check passed: {EXPECTED_NAME}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
