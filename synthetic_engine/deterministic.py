from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass



def derive_seed(seed: int, label: str) -> int:
    raw = f"{seed}:{label}".encode("utf-8")
    digest = hashlib.sha256(raw).digest()
    return int.from_bytes(digest[:8], "big") & 0x7FFFFFFF


@dataclass(frozen=True)
class SeedBundle:
    base_seed: int

    def for_label(self, label: str) -> int:
        return derive_seed(self.base_seed, label)

    def rng(self, label: str) -> random.Random:
        return random.Random(self.for_label(label))
