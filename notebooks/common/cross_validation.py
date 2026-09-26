import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold, cross_val_score
from .models import ModelType


def fit_params_for(name, cat_features=None):
    """catboost에만 cat_features를 넘긴다 (다른 모델은 빈 dict)."""
    return {"cat_features": cat_features} if name == "cat" and cat_features else {}


def cv_evaluate(name, x_train, y_train, seed, cat_features=None, **params):
    """모델 하나를 주어진 파라미터로 5-fold 교차 검증해 fold별 ROC-AUC를 반환."""
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=seed)
    model = ModelType[name].create(seed, **params)
    return cross_val_score(model, x_train, y_train, scoring="roc_auc", cv=skf,
                           params=fit_params_for(name, cat_features))


def cv_compare(model_names, x_train, y_train, seed, cat_features=None):
    cv_scores = {}
    for name in model_names:
        scores = cv_evaluate(name, x_train, y_train, seed, cat_features)
        cv_scores[name] = scores
        print(f"{name} 교차 검증 평균 점수: {np.mean(scores):.4f} (±{np.std(scores):.4f})")

    return pd.DataFrame(cv_scores)


def cv_feature_sets(name, feature_sets, x_train, y_train, seed, categories=None):
    """피처 조합별 교차 검증 ROC-AUC 비교 (ablation).
    feature_sets: {"조합 이름": [컬럼, ...]}"""
    rows = {}
    for set_name, cols in feature_sets.items():
        cats = [c for c in (categories or []) if c in cols]
        scores = cv_evaluate(name, x_train[cols], y_train, seed, cats)
        rows[set_name] = {"피처 수": len(cols),
                          "ROC-AUC 평균": scores.mean(),
                          "표준편차": scores.std()}
        print(f"{set_name}: {scores.mean():.4f} (±{scores.std():.4f})")
    result = pd.DataFrame(rows).T
    result["피처 수"] = result["피처 수"].astype(int)
    base = result["ROC-AUC 평균"].iloc[0]
    result["기본 대비"] = result["ROC-AUC 평균"] - base
    return result
