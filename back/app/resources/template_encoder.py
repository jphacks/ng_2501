from __future__ import annotations

from typing import Optional

import numpy as np
import torch
from transformers import AutoModel, AutoTokenizer


def _mean_pool(
    last_hidden_state: torch.Tensor, attention_mask: torch.Tensor
) -> torch.Tensor:
    """
    アテンションマスクを考慮した平均プーリングを行う。
    """
    mask = attention_mask.unsqueeze(-1).type_as(last_hidden_state)
    summed = (last_hidden_state * mask).sum(dim=1)
    counts = mask.sum(dim=1).clamp(min=1e-9)
    return summed / counts


class TemplateEncoder:
    """
    テンプレートテキストを埋め込みベクトルへ変換するエンコーダ。
    """

    DEFAULT_MODEL_NAME = "cl-nagoya/ruri-v3-30m"

    def __init__(self, model_name: Optional[str] = None, *, device: str = "cpu") -> None:
        self.model_name = model_name or self.DEFAULT_MODEL_NAME
        self.device = device

        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModel.from_pretrained(self.model_name).to(self.device)
        self.model.eval()

    @torch.no_grad()
    def encode(self, text: str, *, max_length: int = 256) -> np.ndarray:
        """
        テキストをエンコードし、正規化済みの文ベクトルを返す。
        """
        encoded = self.tokenizer(
            [text],
            padding=True,
            truncation=True,
            max_length=max_length,
            return_tensors="pt",
        )
        encoded = {k: v.to(self.device) for k, v in encoded.items()}
        model_output = self.model(**encoded)
        sentence_vector = _mean_pool(
            model_output.last_hidden_state, encoded["attention_mask"]
        )
        sentence_vector = torch.nn.functional.normalize(sentence_vector, p=2, dim=1)
        return sentence_vector.cpu().numpy()[0]
