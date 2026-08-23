"""
Metricas de avaliacao (IMPLEMENTATION CHOICE, secao 26 e 47 do PLANO.md).

Accuracy e usada como metrica operacional M(t) para o calculo de drift
(Equacao 7). Precision/Recall sao reportadas em paralelo para comparacao,
mas nao substituem a M(t) especificada pela implementacao.
"""
from __future__ import annotations
from typing import List, Tuple


def confusion_counts(y_true: List[int], y_pred: List[int]) -> Tuple[int, int, int, int]:
    tp = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 1)
    tn = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 0)
    fp = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 1)
    fn = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 0)
    return tp, tn, fp, fn


def accuracy(y_true: List[int], y_pred: List[int]) -> float:
    if not y_true:
        return 0.0
    tp, tn, fp, fn = confusion_counts(y_true, y_pred)
    return (tp + tn) / len(y_true)


def precision(y_true: List[int], y_pred: List[int]) -> float:
    tp, tn, fp, fn = confusion_counts(y_true, y_pred)
    return tp / (tp + fp) if (tp + fp) else 0.0


def recall(y_true: List[int], y_pred: List[int]) -> float:
    tp, tn, fp, fn = confusion_counts(y_true, y_pred)
    return tp / (tp + fn) if (tp + fn) else 0.0


def false_positive_rate(y_true: List[int], y_pred: List[int]) -> float:
    tp, tn, fp, fn = confusion_counts(y_true, y_pred)
    return fp / (fp + tn) if (fp + tn) else 0.0


def false_negative_rate(y_true: List[int], y_pred: List[int]) -> float:
    tp, tn, fp, fn = confusion_counts(y_true, y_pred)
    return fn / (fn + tp) if (fn + tp) else 0.0
