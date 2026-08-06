from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict


@dataclass(frozen=True)
class RenderContext:
    seed: int
    output_dir: Path


@dataclass(frozen=True)
class RenderRequest:
    family: str
    renderer_name: str
    template_id: str
    template_data: Dict[str, Any]
    payload: Dict[str, Any]
    output_pdf: Path
    context: RenderContext


@dataclass(frozen=True)
class RenderResult:
    output_pdf: Path
    renderer_name: str
    metadata: Dict[str, Any]


class Renderer:
    mode: str

    def render(self, request: RenderRequest) -> RenderResult:
        raise NotImplementedError
