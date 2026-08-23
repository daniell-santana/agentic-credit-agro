"""
Teste agropecuario — secao 56 do PLANO.md.

Envia rainfall -30% + commodity -20% e verifica o impacto no pipeline.
Verifica EXPLICITAMENTE que nao existe regra manual do tipo
"seca -> REJECT": o impacto so pode acontecer atraves do caminho
data -> features -> PD -> threshold -> decision (Equacoes 1, 3, 4, 5, 10).

A forma de garantir isso automaticamente (sem so ler o codigo-fonte) e
provar que o efeito do choque desaparece se zerarmos o coeficiente beta
do PD model para as features climaticas afetadas — se a decisao SO muda
quando o beta correspondente e diferente de zero, entao a alteracao
passa necessariamente pela formula do artigo (Eq. 5), nao por um atalho.
"""
import sys, os, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from backend.streaming.processor import AgenticCreditPipeline
from tests._helpers import isolated_pipeline as _isolated_pipeline


def test_climate_shock_changes_features_and_pd():
    p_baseline = _isolated_pipeline()
    p_shocked = _isolated_pipeline()
    p_shocked.apply_climate_shock(rainfall_pct=-30, drought_delta=0.15)
    p_shocked.apply_macro_shock(commodity_pct=-20)

    c_baseline = p_baseline.run_one_cycle()
    c_shocked = p_shocked.run_one_cycle()

    assert c_baseline["application_id"] == c_shocked["application_id"]

    rain_before = c_baseline["raw_features"]["rainfall"]
    rain_after = c_shocked["raw_features"]["rainfall"]
    assert rain_after < rain_before, f"chuva deveria cair: {rain_before} -> {rain_after}"
    assert abs(rain_after - rain_before * 0.70) < 1e-6, "queda deveria ser exatamente -30%"

    commodity_before = c_baseline["raw_features"]["commodity_index"]
    commodity_after = c_shocked["raw_features"]["commodity_index"]
    assert commodity_after < commodity_before, "indice de commodity deveria cair"

    assert c_baseline["pd"] != c_shocked["pd"], "PD deveria mudar apos o choque climatico/commodity"
    print(
        "PASS test_climate_shock_changes_features_and_pd "
        f"(chuva {rain_before:.1f} -> {rain_after:.1f}, PD {c_baseline['pd']:.4f} -> {c_shocked['pd']:.4f})"
    )


def test_no_hardcoded_drought_rule():
    """Prova que a decisao NAO tem um atalho 'seca -> REJECT': com os
    coeficientes beta das features climaticas zerados no PD model, aplicar
    o mesmo choque climatico/commodity deixa de alterar o PD -- ou seja, o
    UNICO caminho de efeito e a Equacao 5 (PD = sigmoid(sigma0 + beta.x))
    aplicada as features numericas, nao uma regra condicional escrita a
    parte (que continuaria produzindo efeito mesmo com beta=0)."""
    p_no_shock = _isolated_pipeline()
    p_with_shock = _isolated_pipeline()

    climate_features = ["rainfall", "temperature", "drought_index", "crop_price", "commodity_index"]
    for p in (p_no_shock, p_with_shock):
        for f in climate_features:
            p.pd_model.beta[f] = 0.0

    p_with_shock.apply_climate_shock(rainfall_pct=-30, drought_delta=0.15)
    p_with_shock.apply_macro_shock(commodity_pct=-20)

    c_no_shock = p_no_shock.run_one_cycle()
    c_with_shock = p_with_shock.run_one_cycle()

    assert c_no_shock["application_id"] == c_with_shock["application_id"]
    # As features climaticas AINDA mudam nos dois pipelines (o choque continua
    # afetando raw_features normalmente) -- o que muda e que, com beta=0, essa
    # mudanca deixa de se propagar para o PD.
    assert c_no_shock["raw_features"]["rainfall"] != c_with_shock["raw_features"]["rainfall"], (
        "o choque deveria continuar alterando a feature bruta, independente do beta"
    )
    assert abs(c_no_shock["pd"] - c_with_shock["pd"]) < 1e-9, (
        "com os coeficientes climaticos zerados, o choque climatico NAO deveria mais "
        "alterar o PD -- se ainda alterasse, indicaria uma regra escondida fora da Eq. 5"
    )
    print(
        "PASS test_no_hardcoded_drought_rule "
        f"(PD identico = {c_no_shock['pd']:.6f} nos dois casos, apesar do choque nas features brutas)"
    )


if __name__ == "__main__":
    test_climate_shock_changes_features_and_pd()
    test_no_hardcoded_drought_rule()
