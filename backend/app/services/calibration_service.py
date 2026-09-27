from functools import lru_cache
from pathlib import Path

from app.services.calibration_features import encode_feature_rows


def predict_step_confidence(
    features: dict[str, object],
    model_path: str | None,
) -> float | None:
    if not model_path:
        return None

    path = Path(model_path)
    if not path.is_absolute():
        path = Path(__file__).resolve().parents[3] / path
    path = path.resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Step calibrator not found: {path}")

    model = _load_model(str(path))
    probability = model.predict_proba(encode_feature_rows([features]))[0][1]
    return max(0.0, min(1.0, float(probability)))


@lru_cache(maxsize=2)
def _load_model(path: str):
    from xgboost import XGBClassifier

    model = XGBClassifier()
    model.load_model(path)
    return model