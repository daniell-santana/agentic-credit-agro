"""
Hiperparametros de implementacao (IMPLEMENTATION CHOICE — nao especificados
pelo artigo, conforme secoes 17, 20, 26 do PLANO.md).
"""
FEATURE_NAMES = [
    "requested_amount", "term_months", "interest_rate", "collateral_value",
    "annual_revenue", "annual_cost", "equity", "debt", "farm_size_ha",
    "years_farming", "rainfall", "temperature", "drought_index",
    "crop_price", "selic", "inflation", "usd_brl", "commodity_index",
]

TAU_0 = 0.5          # threshold inicial (IMPLEMENTATION CHOICE)
ETA = 0.08            # taxa de adaptacao do threshold, Equacao 6 (IMPLEMENTATION CHOICE)
GAMMA = 0.03          # limiar de drift, Equacao 7 (IMPLEMENTATION CHOICE)
MC_SAMPLES = 12        # amostras Monte Carlo para Var(PD), Equacao 9 (IMPLEMENTATION CHOICE)
NOISE_STD = 0.03       # ruido gaussiano nas features ponderadas para MC (IMPLEMENTATION CHOICE)
SEED = 42
