import numpy as np
import optuna
from optuna.samplers import TPESampler
from sklearn.model_selection import StratifiedKFold, cross_val_score
from .models import ModelType


class CatObjective:
    def __init__(self, x_train, y_train, seed, cat_features,
                 iterations=None, lr=None, depth=None, l2=None):
        self.x_train = x_train
        self.y_train = y_train
        self.seed = seed
        self.cat_features = cat_features
        num_folds = 5
        self.cv = StratifiedKFold(n_splits=num_folds, shuffle=True, random_state=self.seed)
        self.iterations, self.lr, self.depth, self.l2 = iterations, lr, depth, l2

    def __call__(self, trial):
        hp = {}
        # 범위를 넣은 것만 탐색, 안 넣은 건 모델 기본값
        if self.iterations:
            hp["iterations"] = trial.suggest_int("iterations", *self.iterations, step=100)
        if self.lr:
            hp["learning_rate"] = trial.suggest_float("learning_rate", *self.lr, log=True)  # 학습률은 로그 스케일로 탐색
        if self.depth:
            hp["depth"] = trial.suggest_int("depth", *self.depth)
        if self.l2:
            hp["l2_leaf_reg"] = trial.suggest_float("l2_leaf_reg", *self.l2)

        # model
        model = ModelType.cat.create(self.seed, **hp)
        # cross validation
        scores = cross_val_score(model, self.x_train, self.y_train, cv=self.cv,
                                 scoring="roc_auc",
                                 params={"cat_features": self.cat_features})
        return np.mean(scores)


class LgbObjective:
    def __init__(self, x_train, y_train, seed,
                 n_estimators=None, lr=None, num_leaves=None, min_child=None):
        self.x_train = x_train
        self.y_train = y_train
        self.seed = seed
        num_folds = 5
        self.cv = StratifiedKFold(n_splits=num_folds, shuffle=True, random_state=self.seed)
        self.n_estimators, self.lr, self.num_leaves, self.min_child = n_estimators, lr, num_leaves, min_child

    def __call__(self, trial):
        hp = {}
        if self.n_estimators:
            hp["n_estimators"] = trial.suggest_int("n_estimators", *self.n_estimators, step=100)
        if self.lr:
            hp["learning_rate"] = trial.suggest_float("learning_rate", *self.lr, log=True)  # 학습률은 로그 스케일로 탐색
        if self.num_leaves:
            hp["num_leaves"] = trial.suggest_int("num_leaves", *self.num_leaves)
        if self.min_child:
            hp["min_child_samples"] = trial.suggest_int("min_child_samples", *self.min_child)

        # model
        model = ModelType.lgb.create(self.seed, **hp)
        # cross validation
        scores = cross_val_score(model, self.x_train, self.y_train, cv=self.cv, scoring="roc_auc")
        return np.mean(scores)


class XgbObjective:
    def __init__(self, x_train, y_train, seed,
                 n_estimators=None, lr=None, max_depth=None, min_child=None):
        self.x_train = x_train
        self.y_train = y_train
        self.seed = seed
        num_folds = 5
        self.cv = StratifiedKFold(n_splits=num_folds, shuffle=True, random_state=self.seed)
        self.n_estimators, self.lr, self.max_depth, self.min_child = n_estimators, lr, max_depth, min_child

    def __call__(self, trial):
        hp = {}
        if self.n_estimators:
            hp["n_estimators"] = trial.suggest_int("n_estimators", *self.n_estimators, step=100)
        if self.lr:
            hp["learning_rate"] = trial.suggest_float("learning_rate", *self.lr, log=True)  # 학습률은 로그 스케일로 탐색
        if self.max_depth:
            hp["max_depth"] = trial.suggest_int("max_depth", *self.max_depth)
        if self.min_child:
            hp["min_child_weight"] = trial.suggest_int("min_child_weight", *self.min_child)

        # model
        model = ModelType.xgb.create(self.seed, **hp)
        # cross validation
        scores = cross_val_score(model, self.x_train, self.y_train, cv=self.cv, scoring="roc_auc")
        return np.mean(scores)


def run_study(objective, seed, n_trials=30, timeout=None):
    """주의: study.best_value는 여러 trial 중 '최고값'이라 낙관적으로 부풀려져 있다.
    기본 설정과 공정하게 비교하려면 cross_validation.cv_evaluate로
    튜닝 때와 다른 fold(seed)에서 기본값·최적값을 다시 평가할 것."""

    optuna.logging.disable_default_handler()

    sampler = TPESampler(seed=seed)                 # 대체모델 부분
    study = optuna.create_study(
        direction="maximize",                       # ROC-AUC 최대화
        sampler=sampler
    )
    study.optimize(objective, n_trials=n_trials, timeout=timeout)

    print("Best Score:", study.best_value)          # 교차 검증 평균 ROC-AUC
    print("Best hp", study.best_params)             # 찾은 최적 파라미터
    return study