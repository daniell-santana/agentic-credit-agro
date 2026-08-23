"""
Persistencia do estado adaptativo entre reinicializacoes do processo
(secao 43 do PLANO.md).

Guarda em disco: normalization mean/std, weights (Eq.3), threshold
(Eq.6), coeficientes do PD model (sigma0/beta), eta, gamma,
previous_loss, previous_metric, iteration, contadores. O outcome_store
(secao 25) ja persiste separadamente em data/outcomes.json e nao e
duplicado aqui.

Classificacao: IMPLEMENTATION CHOICE — o artigo nao especifica um
mecanismo de persistencia; a MVP usa um arquivo JSON local (write
atomico via os.replace) por simplicidade e auditabilidade (o arquivo
pode ser aberto e lido por um humano a qualquer momento).
"""
from __future__ import annotations
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

DEFAULT_PATH = os.path.join("data", "adaptive_state.json")


def load(path: str = DEFAULT_PATH) -> Optional[Dict[str, Any]]:
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        # Estado corrompido/ilegivel nunca deve derrubar o pipeline: a MVP
        # simplesmente reinicia com o estado padrao (equivalente a "cold start").
        return None


def save(state: Dict[str, Any], path: str = DEFAULT_PATH) -> None:
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)
    payload = dict(state)
    payload["saved_at"] = datetime.now(timezone.utc).isoformat()
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)  # write atomico: nunca deixa o arquivo pela metade


def reset(path: str = DEFAULT_PATH) -> bool:
    """Remove o estado persistido. Retorna True se havia arquivo para remover."""
    if os.path.exists(path):
        os.remove(path)
        return True
    return False
