"""
LoRATrainer – kick off LoRA fine-tuning (placeholder).
"""
from __future__ import annotations
from pathlib import Path
from typing import List, Tuple
from hippoium.core.training.pair_builder import PairBuilder
import json


class LoRATrainer:
    def __init__(self, output_dir: str = "lora_corpus"):
        self.out = Path(output_dir)
        self.out.mkdir(exist_ok=True)

    def prepare_dataset(self, pairs: List[Tuple[str, str]], shard: str = "train"):
        path = self.out / f"{shard}.jsonl"
        with path.open("w", encoding="utf-8") as fp:
            for p, c in pairs:
                fp.write(json.dumps({"prompt": p, "completion": c}, ensure_ascii=False) + "\n")

    def train(self):
        # TODO: integrate with PEFT / Hugging Face LoRA pipeline
        print("LoRA fine-tuning stub – dataset ready at", self.out)






















