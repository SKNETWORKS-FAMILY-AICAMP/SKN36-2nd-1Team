from lightgbm import LGBMClassifier
from xgboost import XGBClassifier
from catboost import CatBoostClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
import enum


#분류 모델 클래스
class ModelType(enum.Enum):
    lgb = (LGBMClassifier, {
        "verbosity" : -1,
        "n_jobs" : -1,
        "importance_type" : "gain" 
    })

    xgb = (XGBClassifier, 
            {"tree_method" : 'hist',
             "enable_categorical" : True})

    cat = (CatBoostClassifier, {"verbose": 0, 
                                "thread_count": -1})
    rf  = (RandomForestClassifier, {"n_jobs": -1})
    lr  = (LogisticRegression, {"max_iter": 1000})

    def __init__(self, model_cls, defaults):
        self.model_cls = model_cls
        self.defaults = defaults

    def create(self, seed, **params):
        return self.model_cls(**{"random_state": seed, **self.defaults, **params})