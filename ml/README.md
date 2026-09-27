# Step-level calibration experiment

The inference API exposes step features but uses a type-adaptive weighted proxy
until a supervised artifact is trained. The XGBoost model predicts
`P(step_correct)` and uses step type as a one-hot feature.

Training data is newline-delimited JSON, one step per record:

```json
{"question_id":"gsm8k-test-0001","step_correct":1,"features":{"step_type":"arithmetic","verification_score":0.91,"consistency_score":0.8,"sample_agreement_score":0.6,"semantic_entropy":0.3,"mean_token_logprob":-0.18,"token_entropy":0.24}}
```

Labels must come from ground truth or controlled error injection, not from the
confidence signals being trained. The trainer holds out whole `question_id`
groups, reports ECE, MCE, Brier score, NLL, AUROC, and reliability bins, then
saves the model:

```powershell
python -m ml.experiments.train_step_calibrator --data data/step_features.jsonl --output ml/artifacts/step_calibrator.json
```

Set `STEP_CALIBRATOR_PATH=ml/artifacts/step_calibrator.json` in the root `.env`
to use the trained model in the API. Without that artifact, the API reports
`type_adaptive_weighted_proxy`; it must not be described as trained or
probability-calibrated.

The OpenAI API exposes generated-token log probabilities but not hidden states
or attention tensors. Those latent signals require the local-model experiment
planned in the project proposal and are not inferred or imputed by this API.
