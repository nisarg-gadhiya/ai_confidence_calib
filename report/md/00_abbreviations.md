# List of Abbreviations

Table: Abbreviations. {#tab:abbreviations}

| Abbreviation | Meaning |
|---|---|
| API | Application Programming Interface |
| ASGI | Asynchronous Server Gateway Interface |
| AUROC | Area Under the Receiver Operating Characteristic curve |
| CoT | Chain of Thought |
| CORS | Cross-Origin Resource Sharing |
| CSS | Cascading Style Sheets |
| CVD | Colour-Vision Deficiency |
| ECE | Expected Calibration Error |
| HTML | HyperText Markup Language |
| HTTP | HyperText Transfer Protocol |
| JSON | JavaScript Object Notation |
| LLM | Large Language Model |
| MCE | Maximum Calibration Error |
| NLI | Natural Language Inference |
| NLL | Negative Log-Likelihood |
| QA | Question Answering |
| RAG | Retrieval-Augmented Generation |
| RQ | Research Question |
| SDK | Software Development Kit |
| SE | Semantic Entropy |
| SMT | Satisfiability Modulo Theories |
| UI | User Interface |
| URL | Uniform Resource Locator |
| UTC | Coordinated Universal Time |
| UUID | Universally Unique Identifier |

**Terms used throughout.**

- **ENTAILED / CONTRADICTED / UNKNOWN**: the logical verdict for a claim. ENTAILED means the premises prove the claim; CONTRADICTED means they prove its negation; UNKNOWN means they prove neither (open-world semantics).
- **SUPPORT / CONTRADICT / UNKNOWN**: the verdict of one evidence source on one factual claim, and the overall verdict of a claim after weighting the sources.
- **KEEP / DOWN_WEIGHT / REJECT**: the status of a retrieved source after the reliability filter: used at full weight (reliability ≥ 0.75), used at reduced weight (≥ 0.45), or discarded.
- **p_true**: the verifier model's estimated probability that a proposed step is correct.
- **Semantic entropy**: the entropy of the distribution of sampled continuations over groups of equal meaning, normalised to [0, 1].
- **Consistency**: the share of independent views (sampled continuations, or source verdicts) that agree with the most common one.
- **Essential claim**: a claim needed to answer the question; only essential claims contribute to the answer confidence.
- **Predicted error step**: the step with the lowest confidence, flagged as the most likely location of an error.
- **Calibration status**: the label attached to every response stating how its confidence was produced, for example `type_adaptive_weighted_proxy` or `fixed_sigmoid_not_empirically_calibrated`.
