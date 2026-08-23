"""Helper compartilhado pelos testes: cada teste usa seu proprio diretorio
temporario para state_path e outcome_path, para nunca poluir
data/adaptive_state.json nem data/outcomes.json (usados pelo servidor real)
e para nunca interferir entre testes que rodam na mesma sessao."""
import os
import tempfile

from backend.streaming.processor import AgenticCreditPipeline


def isolated_pipeline(prefix: str = "farmtech_test_") -> AgenticCreditPipeline:
    tmp_dir = tempfile.mkdtemp(prefix=prefix)
    return AgenticCreditPipeline(
        state_path=os.path.join(tmp_dir, "adaptive_state.json"),
        outcome_path=os.path.join(tmp_dir, "outcomes.json"),
    )
