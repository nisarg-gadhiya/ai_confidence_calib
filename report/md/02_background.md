# Background and Motivation

This chapter introduces the ideas the rest of the report builds on: how large language models reason and how they fail, what it means for a confidence to be calibrated and how calibration is measured, the main families of methods for estimating a model's confidence, and the verification tools (retrieval, LLM judges and SMT solvers) that Calibra combines. It closes by arguing why a single, generic confidence heuristic is not enough across different kinds of reasoning.

## How Language Models Reason and Fail {#sec:bg-llm}

A large language model (LLM) generates text one token at a time, each token sampled from a probability distribution conditioned on everything before it. Prompting a model to write intermediate steps before its answer, known as chain-of-thought prompting, substantially improves performance on multi-step problems [@wei2022], and has become the standard way to elicit reasoning. The steps are themselves generated text, however, and nothing in the generation process guarantees that they are correct.

Three failure modes matter for this project, one for each pipeline:

- **Arithmetic slips.** The model sets up a calculation correctly and then produces a wrong intermediate result ("15 × 4 = 50"), after which every later step builds on the error. GSM8K was introduced precisely because such multi-step word problems remained hard for strong models [@cobbe2021].
- **Hallucinated facts.** The model asserts a fact that is false or unsupported, in the same fluent and confident style as a true one. Hallucination is pervasive across generation tasks [@ji2023], and the tone of the text carries no information about its truth.
- **Invalid deductions.** The model draws a conclusion that does not follow from the given premises, for example by affirming the consequent or by inventing a premise. Benchmarks of deduction over natural-language rules, such as RuleTaker, were built to test whether models can follow rules faithfully [@clark2020; @tafjord2021].

In each case the error is located in a specific step, while the rest of the chain may be sound. This observation motivates step-level confidence: an answer-level score can say that something is wrong, but only a step-level profile can say where.

### Sources of uncertainty

Uncertainty in a model's answer has two sources [@kuhn2023]. *Aleatoric* uncertainty belongs to the question: an ambiguous or under-specified question has several acceptable answers, and no model can remove that ambiguity. *Epistemic* uncertainty belongs to the model: it lacks the knowledge or reasoning ability to answer reliably. Epistemic uncertainty is the one associated with hallucination, and the one a confidence estimate can usefully expose. The questions in Calibra's benchmarks have definite answers, so the uncertainty measured is predominantly epistemic.

## Calibration {#sec:bg-calibration}

A model's confidence is *calibrated* if, among all predictions made with confidence $p$, a fraction $p$ is correct. Formally, for a confidence $\hat{p}$ and a correctness indicator $Y \in \{0, 1\}$:

$$P(Y = 1 \mid \hat{p} = p) = p \quad \text{for all } p \in [0, 1]$$ {#eq:calibration}

Calibration is distinct from accuracy: a model that is right 70% of the time and always says "70%" is perfectly calibrated, but its confidence is useless for telling its right answers from its wrong ones. That second property, *discrimination* (also called sharpness or resolution), is measured separately. A useful confidence needs both. Modern neural networks were shown to be poorly calibrated, typically over-confident, despite high accuracy [@guo2017], and LLMs asked to state their confidence in words are frequently over-confident as well [@xiong2024].

### Metrics

Let $N$ predictions have confidences $p_n$ and correctness labels $y_n$. The following metrics are used throughout the report.

**Reliability diagram and expected calibration error (ECE).** Partition $[0, 1]$ into $M$ equal-width bins $B_1, \dots, B_M$ (we use $M = 10$). For each bin, compare the mean confidence $\mathrm{conf}(B_m)$ with the observed accuracy $\mathrm{acc}(B_m)$; a reliability diagram plots one against the other. ECE is the weighted mean gap [@naeini2015; @guo2017]:

$$\mathrm{ECE} = \sum_{m=1}^{M} \frac{|B_m|}{N}\,\bigl|\mathrm{acc}(B_m) - \mathrm{conf}(B_m)\bigr|$$ {#eq:ece}

**Maximum calibration error (MCE)** is the largest gap over non-empty bins, $\max_m |\mathrm{acc}(B_m) - \mathrm{conf}(B_m)|$. It exposes a single badly calibrated region that ECE's average can hide.

**Brier score** is the mean squared error of the confidence [@brier1950]:

$$\mathrm{Brier} = \frac{1}{N}\sum_{n=1}^{N} (p_n - y_n)^2$$ {#eq:brier}

It rewards both calibration and discrimination; a constant prediction of 0.5 scores 0.25.

**Negative log-likelihood (NLL)** penalises confident mistakes heavily:

$$\mathrm{NLL} = -\frac{1}{N}\sum_{n=1}^{N} \bigl[y_n \log p_n + (1 - y_n)\log(1 - p_n)\bigr]$$ {#eq:nll}

**AUROC**, the area under the receiver operating characteristic curve, measures discrimination only. It equals the probability that a randomly chosen correct prediction receives a higher confidence than a randomly chosen wrong one. AUROC is 0.5 for a random score and 1.0 for a perfect ranking, and it is unchanged by any strictly increasing transformation of the confidence.

ECE has known weaknesses: it depends on the binning, and with few predictions per bin it is noisy. With the small pilots in this report, ECE and AUROC are therefore read together with the reliability diagrams and the raw confidence distributions.

### Post-hoc calibration

A model whose confidence ranks predictions well but is mis-scaled can be repaired after training by fitting a monotone mapping on held-out labelled data:

- **Platt scaling** fits a logistic function $\hat{p} = \sigma(a s + b)$ to a raw score $s$ [@platt1999].
- **Temperature scaling** divides the logits by a single learned temperature $T$ before the softmax, $\hat{p} = \mathrm{softmax}(z / T)$, choosing $T$ to minimise NLL; it is simple and effective for neural classifiers [@guo2017].
- **Isotonic regression** fits a free-form non-decreasing step function, solved by the pool-adjacent-violators algorithm [@zadrozny2002].

All three preserve the ranking of predictions and therefore cannot improve AUROC. They fix the *scale* of a confidence, not its *ordering*. Learned calibrators that take several features as input, such as a gradient-boosted classifier [@chen2016], can change the ordering, because they learn how to combine signals rather than how to rescale one.

## Granularity of Confidence {#sec:bg-granularity}

Confidence can be estimated at different granularities:

- **Token level**: the probability the model assigned to each generated token. It is cheap and available from many APIs, but token probabilities mix uncertainty about *meaning* with uncertainty about *wording*: two paraphrases of the same correct answer split the probability mass between them.
- **Semantic (response) level**: the probability of an answer's *meaning*, estimated by grouping sampled answers that mean the same thing [@kuhn2023]. This removes the wording problem but still treats the whole answer as one unit.
- **Step level**: a confidence for each reasoning step. Process supervision has shown that step-level feedback is more informative than outcome-level feedback for training and verifying mathematical reasoning [@uesato2022; @lightman2023], but step-level *confidence estimation* for arbitrary reasoning, using signals available at inference time, is much less studied. This is the granularity Calibra targets.

## Families of Confidence-Estimation Methods {#sec:bg-families}

The project proposal grouped existing confidence methods into four families (@tab:bg-families). Each has a characteristic blind spot, and Calibra uses signals from three of them.

Table: Families of LLM confidence-estimation methods. {#tab:bg-families}

| Family | Mechanism | Characteristic limitation | Use in Calibra |
|---|---|---|---|
| Verbalised / self-evaluation | Ask the model for its confidence or for the probability that an answer is true | Least reliable where the model's knowledge is weakest; often over-confident | Step verifier `p_true`; claim assessment confidence |
| Latent information | Token probabilities, entropy or hidden states | Measures internal certainty, not truth; hidden states need model access | Span-restricted token probability and entropy (arithmetic) |
| Consistency | Sample several answers; agreement implies confidence | Cannot detect an answer that is consistently wrong | Prefix-conditioned next-step agreement; source-verdict agreement |
| Semantic clustering | Group samples by meaning, measure entropy over groups | Strong at response level but applied only to whole answers | Semantic clusters of next-step samples; semantic entropy |

**Self-evaluation.** Kadavath et al. showed that large models can estimate the probability that a proposed answer is true ("P(True)"), and that this estimate improves when the model first sees several of its own sampled answers [@kadavath2022]. Eliciting a verbalised confidence directly is simple but tends to be over-confident [@xiong2024; @tian2023].

**Latent information.** Token log-probabilities and entropies are the most direct internal signal. Methods that read hidden states, such as INSIDE [@chen2024inside] and semantic-entropy probes [@kossen2024], detect hallucinations from internal representations but require access to the model's activations, which hosted APIs do not provide.

**Consistency.** Self-consistency samples several reasoning paths and takes the majority answer, improving accuracy and giving agreement as a by-product [@wang2023]. SelfCheckGPT uses agreement between sampled responses to detect hallucinated sentences without any access to model internals [@manakul2023]. All consistency methods share a blind spot: a model that makes the same mistake every time appears confident.

**Semantic clustering.** Semantic entropy groups sampled answers by bidirectional entailment and computes entropy over the groups rather than over strings, so that paraphrases count as agreement [@kuhn2023]; it has been shown to detect confabulations across domains [@farquhar2024]. For $M$ meaning clusters with sampled proportions $q_m$:

$$\mathrm{SE} = -\sum_{m=1}^{M} q_m \log q_m$$ {#eq:se}

Calibra applies this idea at each step boundary instead of to whole answers (Chapter 7).

## External Verification {#sec:bg-verification}

Model-internal signals cannot catch a model that is confidently and consistently wrong. External verification brings in information from outside the model.

**Retrieval-augmented verification.** Retrieval-augmented generation conditions a model on retrieved documents to ground its output [@lewis2020]. The same idea can be used after generation: retrieve evidence for each claim and judge whether it supports the claim. FActScore splits long-form text into atomic facts and scores the fraction supported by a knowledge source [@min2023]; Calibra's factual pipeline follows this decomposition and adds source reliability and a confidence per claim.

**LLM-as-judge.** Using a language model to judge outputs, for example to decide whether evidence supports a claim or whether a step is correct, scales well and agrees reasonably with human judgement on many tasks, but it is biased toward verbose answers, toward the first option presented and toward its own outputs [@zheng2023]. Calibra uses LLM judgements throughout and treats them as one signal among several.

**SMT solvers.** A satisfiability-modulo-theories (SMT) solver decides whether a set of logical formulas can all be true together. Z3 [@demoura2008] supports first-order formulas with uninterpreted functions and quantifiers, and can report an *unsatisfiable core*, the subset of formulas responsible for a contradiction. A conclusion $\varphi$ is entailed by premises $\Gamma$ exactly when $\Gamma \cup \{\neg\varphi\}$ is unsatisfiable. Logic-LM showed that translating a problem into a symbolic form and letting a solver reason is more faithful than letting the LLM deduce directly [@pan2023logiclm]. Calibra's logical pipeline uses this approach, so its verdicts do not depend on the model at all.

## Why One Heuristic Is Not Enough {#sec:bg-why}

A single confidence method applied uniformly to every answer fails in predictable ways, because the reasoning types fail differently:

- For a **calculation**, consistency under resampling is informative: if the model is unsure of 17 × 23, independent attempts disagree. External retrieval is useless, since there is nothing to look up.
- For a **factual claim**, consistency is weak: a model that has learned a wrong fact repeats it confidently. Here the decisive signal is external evidence, weighted by how trustworthy its source is.
- For a **deduction**, neither sampling nor retrieval answers the question that matters, which is whether the conclusion follows. A theorem prover answers it exactly.

The proposal therefore argued for adapting *which* signals are trusted to the type of reasoning, per step, since one answer can mix step types. Calibra implements this with a gateway that routes each question to a pipeline built around the right check (Chapter 6) and with step-type-dependent fusion weights in the arithmetic pipeline (Chapter 7). Chapters 3 and 4 review the literature and the gaps this design addresses.
