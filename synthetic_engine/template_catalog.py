from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List


@dataclass(frozen=True)
class TemplateDefinition:
    template_id: str
    family: str
    renderer: str
    path: Path
    description: str
    default: bool


class TemplateCatalog:
    def __init__(self, manifest_path: Path) -> None:
        self.manifest_path = manifest_path
        self.root = manifest_path.parent
        self._manifest = self._load_manifest()
        self._templates = self._parse_templates(self._manifest)

    @classmethod
    def from_default_location(cls) -> "TemplateCatalog":
        root = Path(__file__).resolve().parent.parent
        return cls(root / "template-catalog" / "manifest.json")

    def _load_manifest(self) -> Dict[str, object]:
        if not self.manifest_path.exists():
            raise FileNotFoundError(f"Template manifest not found: {self.manifest_path}")
        with self.manifest_path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def _parse_templates(self, manifest: Dict[str, object]) -> List[TemplateDefinition]:
        out: List[TemplateDefinition] = []
        templates = manifest.get("templates", [])
        if not isinstance(templates, list):
            raise ValueError("manifest.templates must be a list")
        for item in templates:
            if not isinstance(item, dict):
                continue
            path = self.root / str(item.get("path", ""))
            out.append(
                TemplateDefinition(
                    template_id=str(item.get("template_id", "")),
                    family=str(item.get("family", "")),
                    renderer=str(item.get("renderer", "")),
                    path=path,
                    description=str(item.get("description", "")),
                    default=bool(item.get("default", False)),
                )
            )
        return out

    def list_families(self) -> List[str]:
        fams = sorted({t.family for t in self._templates if t.family})
        return fams

    def templates_for_family(self, family: str) -> List[TemplateDefinition]:
        return [t for t in self._templates if t.family == family]

    def default_template(self, family: str) -> TemplateDefinition:
        options = self.templates_for_family(family)
        if not options:
            raise KeyError(f"No templates registered for family '{family}'")
        for t in options:
            if t.default:
                return t
        return options[0]

    def profile_families(self, profile_name: str) -> List[str]:
        profiles = self._manifest.get("profiles", {})
        if not isinstance(profiles, dict):
            raise ValueError("manifest.profiles must be an object")
        raw = profiles.get(profile_name)
        if raw is None:
            raise KeyError(f"Unknown profile '{profile_name}'")
        if not isinstance(raw, list):
            raise ValueError(f"Profile '{profile_name}' must be a list")
        return [str(x) for x in raw]

    def load_template_payload(self, template: TemplateDefinition) -> Dict[str, object]:
        if not template.path.exists():
            raise FileNotFoundError(f"Template file missing: {template.path}")
        with template.path.open("r", encoding="utf-8") as f:
            payload = json.load(f)
        if not isinstance(payload, dict):
            raise ValueError(f"Template JSON must be an object: {template.path}")
        return payload
