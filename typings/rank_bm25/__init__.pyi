# rank-bm25 ships no types; this declares the one class raglab.retrieve.bm25 uses.
from collections.abc import Sequence

import numpy as np
from numpy.typing import NDArray

class BM25Okapi:
    def __init__(
        self,
        corpus: Sequence[Sequence[str]],
        tokenizer: None = None,
        k1: float = 1.5,
        b: float = 0.75,
        epsilon: float = 0.25,
    ) -> None: ...
    def get_scores(self, query: Sequence[str]) -> NDArray[np.float64]: ...
