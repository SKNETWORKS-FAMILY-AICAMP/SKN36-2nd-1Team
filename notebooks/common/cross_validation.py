import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold, cross_val_score
from .models import ModelType


def cv_compare(model_names, x_train, y_train, seed, cat_features=None):
    num_folds = 5
    skf = StratifiedKFold(n_splits=num_folds, shuffle=True, random_state=seed)

    cv_scores = {}
    for name in model_names:
        model = ModelType[name].create(seed)
        fit_params = {"cat_features": cat_features} if name == "cat" else {}   # catboost에만 적용
        scores = cross_val_score(model, x_train, y_train,
                                 scoring="roc_auc", cv=skf, params=fit_params)
        cv_scores[name] = scores
        print(f"{name} 교차 검증 평균 점수: {np.mean(scores):.4f} (±{np.std(scores):.4f})")

    return pd.DataFrame(cv_scores)