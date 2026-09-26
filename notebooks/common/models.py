from lightgbm import LGBMClassifier
from xgboost import XGBClassifier
from catboost import CatBoostClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.compose import ColumnTransformer, make_column_selector
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
import enum


def _preprocessor(scale: bool) -> ColumnTransformer:
    """rf / lr 용 전처리: 범주형은 원-핫, 수치형은 결측 대체(+ lr은 표준화).
    트리 부스팅 모델(lgb/xgb/cat)은 category 타입과 NaN을 직접 처리하므로 필요 없음."""
    num_steps = [SimpleImputer(strategy="median")]
    if scale:
        num_steps.append(StandardScaler())
    return ColumnTransformer([
        ("cat", make_pipeline(SimpleImputer(strategy="most_frequent"),
                              OneHotEncoder(handle_unknown="ignore")),
         make_column_selector(dtype_include="category")),
        ("num", make_pipeline(*num_steps),
         make_column_selector(dtype_exclude="category")),
    ])


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
                                "thread_count": -1,
                                "allow_writing_files": False,   # catboost_info 폴더 안 만듦
                                # ── 속도 설정 (기본값 대비 약 10배 빠름, 성능 거의 동일) ──
                                "iterations": 300,              # 기본 1000 → 300 (대신 학습률 올림)
                                "learning_rate": 0.1,
                                "depth": 6,
                                "one_hot_max_size": 255,        # 범주 수 적은 컬럼은 원-핫 처리 (CTR 계산 생략)
                                "max_ctr_complexity": 1,        # 범주형 조합 피처 생성 안 함
                                "border_count": 64})            # 수치형 분할 후보 254 → 64
    rf  = (RandomForestClassifier, {"n_jobs": -1})
    lr  = (LogisticRegression, {"max_iter": 1000})

    def __init__(self, model_cls, defaults):
        self.model_cls = model_cls
        self.defaults = defaults

    def create(self, seed, **params):
        model = self.model_cls(**{"random_state": seed, **self.defaults, **params})
        # rf / lr 은 category 타입·결측치를 못 받으므로 전처리 파이프라인으로 감싼다
        if self.name in ("rf", "lr"):
            return make_pipeline(_preprocessor(scale=(self.name == "lr")), model)
        return model
