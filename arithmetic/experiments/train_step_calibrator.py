import argparse
import json
from pathlib import Path

from arithmetic.fusion.xgboost_model import train_step_calibrator


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Train and evaluate the grouped step-level XGBoost calibrator."
    )
    parser.add_argument("--data", required=True, help="Labeled step feature JSONL")
    parser.add_argument("--output", required=True, help="Output XGBoost JSON model")
    parser.add_argument("--test-size", type=float, default=0.25)
    args = parser.parse_args()

    records = [
        json.loads(line)
        for line in Path(args.data).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    model, report = train_step_calibrator(records, test_size=args.test_size)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    model.save_model(output)
    print(json.dumps({"model": str(output), "metrics": report}, indent=2))


if __name__ == "__main__":
    main()