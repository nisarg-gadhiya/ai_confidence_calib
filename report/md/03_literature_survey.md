# Literature Survey

This chapter reviews the published work closest to the project's question, paper by paper. For each paper it gives the publication details, the problem the paper addresses, its proposed solution, its results, the gap or limitation relevant to this project, and its relevance to Calibra. The papers fall into five groups: post-hoc calibration of classifiers (Sections 3.1–3.3), confidence estimation for language models (Sections 3.4–3.9), step-level verification of reasoning (Sections 3.10–3.11), external verification of claims and deductions (Sections 3.12–3.14), and the benchmarks used in this project (Sections 3.15–3.16). The chapter closes with a comparison of all surveyed works against Calibra's features.

## Paper 1: On Calibration of Modern Neural Networks

**Publication Details:**

- Authors: Chuan Guo, Geoff Pleiss, Yu Sun, Kilian Q. Weinberger
- Venue: Proceedings of the 34th International Conference on Machine Learning (ICML), PMLR vol. 70, pp. 1321–1330, 2017
- Identifier: arXiv:1706.04599

**Introduction:** Classifiers used in decision-making must say not only what they predict but how likely the prediction is to be right. The paper observes that, unlike earlier networks, modern deep networks are poorly calibrated: their confidence is systematically higher than their accuracy [@guo2017].

**Proposed Solution:** The authors study which training factors (depth, width, batch normalisation, weight decay) drive miscalibration, and compare post-hoc calibration methods on held-out data: histogram binning, isotonic regression, Bayesian binning, matrix and vector scaling, and *temperature scaling*, a single-parameter variant of Platt scaling that divides all logits by one learned temperature before the softmax.

**Results:** Across image and text classification benchmarks, increasing capacity and reducing regularisation worsen calibration even as accuracy improves. Temperature scaling, despite having a single parameter and leaving the predicted class unchanged, was the most effective method on most datasets, and the paper popularised the reliability diagram and the expected calibration error as standard evaluation tools.

**Gap / Limitation:** The work concerns classifiers with a fixed label set and a single prediction per input. It has nothing to say about open-ended generation, where many outputs can be correct, nor about multi-step outputs, where a single confidence cannot indicate which part of an answer is unreliable. As a monotone rescaling, temperature scaling cannot improve the ranking of correct over incorrect predictions.

**Relevance:** This paper supplies the vocabulary and metrics (reliability diagrams, ECE) used throughout this report, and the fixed sigmoid in Calibra's factual and logical pipelines has the same functional form as the scaling methods it studies (Chapter 10). Its central lesson, that a confidence must be checked against outcomes rather than trusted, motivates the calibration-status labels in Calibra.

## Paper 2: Improving Multi-Class Calibration through Normalization-Aware Isotonic Techniques

**Publication Details:**

- Authors: Alon Arad, Saharon Rosset
- Venue: Proceedings of the 42nd International Conference on Machine Learning (ICML), PMLR vol. 267, 2025
- Identifier: arXiv:2512.09054

**Introduction:** Isotonic regression is an effective non-parametric calibrator for binary problems, but its usual extension to many classes, one-vs-rest calibration followed by renormalisation, performs worse than parametric methods such as temperature scaling, which has limited its adoption [@arad2025].

**Proposed Solution:** The authors propose two isotonic methods that account for the fact that class probabilities must sum to one. NA-FIR (normalisation-aware flattened isotonic regression) fits a single monotone map shared across classes and incorporates the normalisation into the optimisation itself; because the normalised objective is no longer convex, it is initialised with the pool-adjacent-violators algorithm and refined by a stochastic search. SCIR (sorted cumulative isotonic regression) instead treats the sorted cumulative class probabilities as a bivariate isotonic problem, using the ranking of classes as additional structure.

**Results:** On image (CIFAR-10, CIFAR-100, Food-101, ImageNet-1k) and text (R52, NG20, Yelp Review) datasets, across 75 trained models, both methods achieved state-of-the-art negative log-likelihood and confidence-ECE. SCIR most often gave the best confidence-ECE but could produce poor NLL because of near-zero probabilities; NA-FIR was the most stable. The methods are slower than temperature scaling: NA-FIR took about 15 minutes on the largest datasets and SCIR about two hours on ImageNet-1k.

**Gap / Limitation:** The methods calibrate the class-probability vector of a classifier's single prediction. They do not apply to free-form generation or to the internal steps of an answer, and they require labelled calibration data for the output being calibrated.

**Relevance:** Calibra does not implement NA-FIR or SCIR, and its outputs are binary step correctness rather than multi-class distributions. The paper is relevant as the state of the art in non-parametric post-hoc calibration: once step-level labels exist, an isotonic calibrator is a natural alternative to the fixed sigmoid for mapping fused step scores to probabilities. Its finding that methods differ in NLL and ECE also supports reporting several calibration metrics rather than one.

## Paper 3: Temperature Scaling Is Not Enough: Calibration Gaps Under Human Label Distributions

**Publication Details:**

- Authors: Wisdom Dogah
- Venue: arXiv preprint, July 2026
- Identifier: arXiv:2607.13423

**Introduction:** Temperature scaling implicitly assumes that the ground truth is a single, deterministic label. Many real tasks have genuinely ambiguous inputs on which human annotators disagree, so the correct target is a distribution over labels [@dogah2026].

**Proposed Solution:** The paper defines a *soft-label calibration gap*: the difference in Brier score, measured against human label distributions, between temperature scaling fitted on hard labels and an oracle fitted directly on the soft labels. It measures the gap on CIFAR-10H (about 51 annotations per image) and ChaosNLI (100 judgements per instance) for three model sizes per modality (ResNet-18/50/101; DistilBERT, BERT-base, BERT-large), and repeats the analysis with multiclass isotonic regression.

**Results:** The gap was positive in all nine configurations, with Brier-score gaps between 0.002 and 0.134. It grew with model size for vision and for the SNLI-derived split, and was much larger for language (mean 0.079) than for vision (mean 0.003). Isotonic regression showed the same qualitative pattern.

**Gap / Limitation:** The study concerns classifiers and the definition of the calibration target, not generative models or reasoning. The models studied are small (up to 340 million parameters), the paper is a single-author preprint, and the language annotations come from English-speaking participants.

**Relevance:** Calibra's step-correctness labels are binary, so the soft-label gap is not addressed. The paper is relevant for two reasons. First, it shows that calibration quality depends on *what* the confidence is compared against, which mirrors the finding in Chapter 14 that the logical confidence measured the queried statement rather than the answer. Second, factual questions can have legitimately disputed answers, where a binary label overstates certainty.

## Paper 4: Language Models (Mostly) Know What They Know

**Publication Details:**

- Authors: Saurav Kadavath and co-authors (Anthropic)
- Venue: arXiv preprint, 2022
- Identifier: arXiv:2207.05221

**Introduction:** For language models to be honest, they must be able to evaluate the validity of their own claims. The paper asks whether large models can estimate the probability that their answers are correct [@kadavath2022].

**Proposed Solution:** The authors study calibration on multiple-choice and true/false questions, then introduce *self-evaluation*: the model proposes an answer and is then asked for the probability "P(True)" that the answer is correct. They show that self-evaluation improves when the model is first shown several of its own sampled answers. They also train models to predict "P(IK)", the probability that they know the answer, before answering.

**Results:** Larger models were well calibrated on suitably formatted multiple-choice and true/false questions. Self-evaluation worked well for open-ended tasks and improved with sampled context, and P(IK) predictions partially generalised across tasks, although calibration on new tasks was weaker.

**Gap / Limitation:** Self-evaluation is applied to a complete answer. It also inherits the model's knowledge: where the model does not know the answer, it is often also unable to recognise its mistake. The study relies on access to the model's own probabilities for P(True).

**Relevance:** Calibra's step verifier is a direct step-level application of this idea: the verifier sees the fixed preceding steps and the K sampled continuations before judging one step, and returns `p_true` (Chapter 7). The limitation it documents is visible in the pilots, where `p_true` averaged 0.984 on GSM8K steps and varied little.

## Paper 5: Can LLMs Express Their Uncertainty? An Empirical Evaluation of Confidence Elicitation in LLMs

**Publication Details:**

- Authors: Miao Xiong, Zhiyuan Hu, Xinyang Lu, Yifei Li, Jie Fu, Junxian He, Bryan Hooi
- Venue: Proceedings of the 12th International Conference on Learning Representations (ICLR), 2024
- Identifier: arXiv:2306.13063

**Introduction:** Many deployed models are available only as black boxes, without access to token probabilities. The paper asks how well confidence can be elicited from such models through prompting and sampling alone [@xiong2024].

**Proposed Solution:** The authors define a framework with three components: prompting strategies for eliciting verbalised confidence, sampling strategies for generating multiple answers, and aggregation strategies for combining verbalised confidence with consistency across samples. They evaluate it on calibration and failure prediction across commonsense, arithmetic, symbolic and professional-knowledge tasks.

**Results:** Verbalised confidence was generally over-confident, often clustering at high values. Combining it with consistency across samples improved both calibration and failure prediction, but the overall ability to distinguish right from wrong answers remained limited, and performance varied by task.

**Gap / Limitation:** Confidence is elicited and evaluated for whole answers. The framework treats all tasks with the same method and uses no evidence from outside the model.

**Relevance:** The finding that self-reported confidence and sampling consistency are complementary is the basis for fusing them in Calibra. Calibra extends the combination with type-specific external evidence and applies it per step.

## Paper 6: Semantic Uncertainty: Linguistic Invariances for Uncertainty Estimation in Natural Language Generation

**Publication Details:**

- Authors: Lorenz Kuhn, Yarin Gal, Sebastian Farquhar
- Venue: Proceedings of the 11th International Conference on Learning Representations (ICLR), 2023
- Identifier: arXiv:2302.09664

**Introduction:** Uncertainty in generated text is hard to measure because different sentences can mean the same thing. Token-level entropy counts "Paris" and "It is Paris" as different answers, overstating uncertainty [@kuhn2023].

**Proposed Solution:** *Semantic entropy* samples several answers, groups them into clusters of equivalent meaning using bidirectional entailment judged by a natural-language-inference model, and computes entropy over the clusters rather than over strings. The method needs no training and uses only the model's samples and likelihoods.

**Results:** On free-form question answering (TriviaQA and CoQA) with OPT models, semantic entropy predicted answer correctness better (higher AUROC) than predictive entropy, length-normalised entropy, lexical similarity and verbalised P(True) baselines. A follow-up in *Nature* showed that semantic entropy detects confabulations across domains, including biographies and mathematical problems [@farquhar2024].

**Gap / Limitation:** Semantic entropy is computed over complete answers sampled from the question. It cannot say which part of a multi-step answer is uncertain, and like all consistency methods it cannot detect a meaning that the model produces consistently but wrongly. The NLI model used for clustering adds a further component whose errors affect the result.

**Relevance:** Calibra applies semantic grouping at every step boundary instead of to whole answers: the K next-step continuations are grouped by meaning, and consistency and normalised semantic entropy are computed from the clusters (Chapter 7). In the GSM8K pilot, semantic grouping gave a mean consistency of 0.525 against 0.356 for exact matching, confirming that wording differences would otherwise be mistaken for disagreement.

## Paper 7: Semantic-Level Confidence Calibration of Language Models via Temperature Scaling

**Publication Details:**

- Authors: Tom A. Lamb, Desi Ivanova, Philip H. S. Torr, Tim G. J. Rudner
- Venue: 1st Workshop on Quantify Uncertainty and Hallucination in Foundation Models: The Next Frontier in Reliable AI, at ICLR 2025
- Identifier: workshop paper (OpenReview)

**Introduction:** Semantic uncertainty methods summarise the distribution over meanings, but it has not been asked whether that distribution is itself *calibrated*: whether a model's confidence in a meaning matches how often that meaning is correct [@lamb2025].

**Proposed Solution:** The authors define a framework of semantic confidence measures computed from clusters of sampled answers: empirical (E-SC, the share of samples in a cluster), likelihood-based (L-SC), mean-likelihood (ML-SC) and Bayesian (B-SC). They compare these with a single-generation confidence, and study how temperature scaling (scalar temperatures fitted with NLL or a selective-smoothing loss, and an adaptive temperature head) affects semantic calibration.

**Results:** Using Llama-3.1-8B-Instruct, Ministral-8B-Instruct and Qwen-2.5-7B-Instruct with ten samples per question, on closed-book (TriviaQA, Natural Questions) and open-book (CoQA, SQuAD) QA, temperature scaling generally improved the calibration of semantic confidence measures and their discrimination. The adaptive temperature head gave the lowest ECE on the open-book data (0.080 for ML-SC on CoQA and 0.078 on SQuAD). The effect was robust to model size (Qwen-2.5 at 1.5, 3 and 7 billion parameters) and to the number of samples.

**Gap / Limitation:** Calibration is at the level of the whole answer, for short-answer QA. The method requires fine-tuning and calibration training on the model (access to logits and the ability to train a temperature head), an NLI model, and several samples per question. It uses semantic consistency alone, without external evidence.

**Relevance:** This is the work closest to Calibra's arithmetic pipeline. Calibra's consistency signal is E-SC computed at a step boundary instead of over whole answers. Calibra cannot apply temperature scaling to the hosted model, but it adds verification and external evidence, and it targets error localisation, which response-level semantic calibration cannot provide. The paper also shows how semantic confidence might later be recalibrated once step labels exist.

## Paper 8: SelfCheckGPT: Zero-Resource Black-Box Hallucination Detection for Generative Large Language Models

**Publication Details:**

- Authors: Potsawee Manakul, Adian Liusie, Mark J. F. Gales
- Venue: Proceedings of the 2023 Conference on Empirical Methods in Natural Language Processing (EMNLP), pp. 9004–9017, 2023
- Identifier: arXiv:2303.08896

**Introduction:** Hallucination detection usually requires either access to the model's probabilities or an external database. The paper proposes detection with neither [@manakul2023].

**Proposed Solution:** If a model knows a fact, independently sampled responses will state it consistently; if it is hallucinating, the samples will diverge. SelfCheckGPT samples several responses and scores each sentence of the main response by its consistency with the samples, using BERTScore, question answering, n-gram models, NLI or prompting an LLM.

**Results:** On a dataset of GPT-3 generated Wikipedia-style biographies annotated at sentence level, SelfCheckGPT detected non-factual sentences and ranked passages by factuality better than grey-box baselines that use token probabilities, with the prompt-based and NLI variants performing best.

**Gap / Limitation:** Being consistency-based, it cannot detect errors that the model repeats in every sample. Its sentences are scored against samples of the whole response, not against samples conditioned on the preceding content, and no external evidence is used.

**Relevance:** SelfCheckGPT operates at sentence level, the closest prior work to step-level scoring, and it is the standard black-box baseline named in the project proposal. Calibra differs in conditioning each step's samples on the fixed preceding steps, and in adding external evidence precisely to cover the "consistently wrong" blind spot.

## Paper 9: Self-Consistency Improves Chain of Thought Reasoning in Language Models

**Publication Details:**

- Authors: Xuezhi Wang, Jason Wei, Dale Schuurmans, Quoc Le, Ed Chi, Sharan Narang, Aakanksha Chowdhery, Denny Zhou
- Venue: Proceedings of the 11th International Conference on Learning Representations (ICLR), 2023
- Identifier: arXiv:2203.11171

**Introduction:** Chain-of-thought prompting [@wei2022] improves reasoning but uses a single greedy reasoning path, which can go wrong at any step [@wang2023].

**Proposed Solution:** *Self-consistency* samples a diverse set of reasoning paths and selects the most consistent final answer by majority vote, on the intuition that a complex problem admits several ways of reaching the unique correct answer.

**Results:** Self-consistency improved chain-of-thought accuracy substantially across benchmarks, for example by 17.9 percentage points on GSM8K, 11.0 on SVAMP, 12.2 on AQuA, 6.4 on StrategyQA and 3.9 on ARC-challenge.

**Gap / Limitation:** Agreement is measured over final answers only; the method does not assess individual steps, and it is a decoding strategy for accuracy rather than a calibrated confidence. Paths that reach the same answer by different reasoning are treated identically.

**Relevance:** Self-consistency established answer agreement under sampling as a reliability signal for reasoning, and GSM8K as its main testbed. Calibra moves the agreement test from final answers to individual steps, conditioned on a fixed prefix, so that instability can be located.

## Paper 10: INSIDE: LLMs' Internal States Retain the Power of Hallucination Detection

**Publication Details:**

- Authors: Chao Chen, Kai Liu, Ze Chen, Yi Gu, Yue Wu, Mingyuan Tao, Zhihang Fu, Jieping Ye
- Venue: Proceedings of the 12th International Conference on Learning Representations (ICLR), 2024
- Identifier: arXiv:2402.03744

**Introduction:** Output-level uncertainty measures lose information that is present in the model's internal representations [@chen2024inside].

**Proposed Solution:** The *EigenScore* measures the semantic diversity of several sampled responses through the eigenvalues of the covariance matrix of their sentence embeddings taken from the model's hidden states. A feature-clipping step truncates extreme activations at test time to reduce over-confident generations.

**Results:** On question-answering benchmarks (CoQA, SQuAD, TriviaQA, Natural Questions) with open models, EigenScore detected hallucinations better than output-based baselines such as predictive and semantic entropy.

**Gap / Limitation:** The method requires access to hidden states, which hosted APIs do not expose, and it scores whole responses.

**Relevance:** The original project design included a hidden-state signal per step inspired by this family of methods. Because Calibra uses a hosted model, latent signals could not be implemented; this remains future work with a locally hosted model (Chapter 17).

## Paper 11: Let's Verify Step by Step

**Publication Details:**

- Authors: Hunter Lightman and co-authors (OpenAI)
- Venue: Proceedings of the 12th International Conference on Learning Representations (ICLR), 2024
- Identifier: arXiv:2305.20050

**Introduction:** Reward models used to train and select reasoning chains can be trained on the final outcome (outcome supervision) or on each intermediate step (process supervision). The paper compares the two [@lightman2023], extending earlier work on process- and outcome-based feedback for math word problems [@uesato2022].

**Proposed Solution:** The authors collect PRM800K, a dataset of 800,000 step-level human correctness labels on model-generated solutions to problems from the MATH dataset, and train a process-supervised reward model that scores each step. Solutions are selected by the reward model's score.

**Results:** Process supervision significantly outperformed outcome supervision: the process-supervised model solved 78% of problems from a representative subset of the MATH test set when selecting among sampled solutions. Active learning made the collection of step labels more efficient.

**Gap / Limitation:** Step-level scoring is achieved by training a dedicated reward model on a large set of human step labels, which is expensive and specific to mathematics. The scores are used to rank solutions, not as calibrated confidences, and the approach does not cover factual or logical reasoning.

**Relevance:** This work shows that step-level judgements carry more information than outcome-level ones, which supports Calibra's premise. Calibra pursues the same granularity without a trained reward model, using signals available at inference time, and its step-correctness labels (Chapter 13) are the inference-time analogue of PRM800K.

## Paper 12: FActScore: Fine-grained Atomic Evaluation of Factual Precision in Long Form Text Generation

**Publication Details:**

- Authors: Sewon Min, Kalpesh Krishna, Xinxi Lyu, Mike Lewis, Wen-tau Yih, Pang Wei Koh, Mohit Iyyer, Luke Zettlemoyer, Hannaneh Hajishirzi
- Venue: Proceedings of the 2023 Conference on Empirical Methods in Natural Language Processing (EMNLP), pp. 12076–12100, 2023
- Identifier: arXiv:2305.14251

**Introduction:** Long generated texts mix true and false statements, so judging them as wholly right or wrong is uninformative [@min2023].

**Proposed Solution:** FActScore breaks a generation into *atomic facts*, short statements each conveying one piece of information, and computes the percentage of atomic facts supported by a reliable knowledge source. The authors collect human annotations for biographies generated by several commercial models and build an automated estimator that retrieves evidence and judges support with a language model.

**Results:** Human evaluation showed that biographies from commercial models contained many unsupported atomic facts, increasingly so for rarer entities. The automated estimator approximated human FActScores with an error rate below 2%, making large-scale evaluation possible.

**Gap / Limitation:** FActScore measures factual precision for evaluation; it produces a score per text, not a calibrated confidence per claim, and it assumes a single trusted knowledge source (Wikipedia) without weighting sources by reliability.

**Relevance:** Calibra's factual pipeline adopts the atomic-claim decomposition. It extends it with open web retrieval, a source-reliability policy, several verification signals per claim, and a confidence rather than a binary support decision (Chapter 8). The pilot's finding that 70% of its "claims" were instructions illustrates the importance of the quality of decomposition that FActScore emphasises.

## Paper 13: Logic-LM: Empowering Large Language Models with Symbolic Solvers for Faithful Logical Reasoning

**Publication Details:**

- Authors: Liangming Pan, Alon Albalak, Xinyi Wang, William Yang Wang
- Venue: Findings of the Association for Computational Linguistics: EMNLP 2023
- Identifier: arXiv:2305.12295

**Introduction:** LLMs reason over natural-language premises unreliably, producing conclusions that do not follow [@pan2023logiclm].

**Proposed Solution:** Logic-LM uses the LLM only to translate a problem into a symbolic formulation (logic programming, first-order logic, constraint satisfaction or SAT), then runs a deterministic symbolic solver, and finally interprets the solver's result. A self-refinement step feeds solver error messages back to the LLM to repair formulations that fail to execute.

**Results:** On five logical reasoning benchmarks (ProofWriter, PrOntoQA, FOLIO, LogicalDeduction and AR-LSAT), Logic-LM improved performance by 39.2% on average over the LLM alone with standard prompting and by 18.4% over chain-of-thought prompting.

**Gap / Limitation:** The method produces an answer, not a confidence, and offers no per-step assessment. When the translation into logic fails or is subtly wrong, the solver's answer is wrong with full certainty.

**Relevance:** Calibra's logical pipeline follows the same division of labour, with a parser translating premises into first-order logic for Z3 (Chapter 9). Calibra adds per-step confidence and keeps the model's own signals alongside the solver. Chapter 14 shows why this matters: when Calibra's parser failed, the model's self-verification disagreed with the solver in exactly the affected questions.

## Paper 14: Z3: An Efficient SMT Solver

**Publication Details:**

- Authors: Leonardo de Moura, Nikolaj Bjørner
- Venue: Tools and Algorithms for the Construction and Analysis of Systems (TACAS), Lecture Notes in Computer Science vol. 4963, pp. 337–340, Springer, 2008
- DOI: 10.1007/978-3-540-78800-3_24

**Introduction:** Many verification and analysis problems reduce to deciding whether a logical formula, over theories such as arithmetic, arrays and uninterpreted functions, is satisfiable [@demoura2008].

**Proposed Solution:** The paper presents Z3, an SMT solver that combines a SAT-solving core with decision procedures for multiple theories and with quantifier instantiation, accessible through programmatic APIs.

**Results:** Z3 was presented as efficient and competitive with the leading SMT solvers of its time, and it has since become one of the most widely used solvers in program verification and analysis.

**Gap / Limitation:** A solver decides formulas; it does not translate natural language into formulas, which is where errors in an LLM–solver system arise. Satisfiability with quantifiers is undecidable in general, so a timeout or "unknown" result must be handled.

**Relevance:** Z3 is Calibra's authoritative logical verifier. Calibra relies on its unsatisfiable cores to report the premises and rules a proof used, and handles its "unknown" results conservatively (Chapter 9).

## Paper 15: Training Verifiers to Solve Math Word Problems

**Publication Details:**

- Authors: Karl Cobbe and co-authors (OpenAI)
- Venue: arXiv preprint, 2021
- Identifier: arXiv:2110.14168

**Introduction:** Even large language models struggle with multi-step mathematical reasoning, because a single error anywhere in a solution makes the answer wrong [@cobbe2021].

**Proposed Solution:** The paper introduces GSM8K, a dataset of about 8,500 linguistically diverse grade-school math word problems with natural-language solutions, and proposes training *verifiers* that judge the correctness of model-generated solutions; at test time many candidate solutions are generated and the one ranked highest by the verifier is chosen.

**Results:** Verification significantly improved performance over fine-tuning alone: a 6-billion-parameter verifier slightly outperformed a fine-tuned 175-billion-parameter model, a gain roughly equivalent to a 30-fold increase in model size, and verification scaled better with more training data.

**Gap / Limitation:** The verifier judges complete solutions and needs task-specific training data. It ranks solutions; its scores are not evaluated as calibrated confidences and do not identify the erroneous step.

**Relevance:** GSM8K is the benchmark of Calibra's arithmetic pilot, and its `#### answer` format provides the correctness labels (Chapter 13). The paper's idea of verifying generated reasoning is applied in Calibra per step and without task-specific training.

## Paper 16: Transformers as Soft Reasoners over Language

**Publication Details:**

- Authors: Peter Clark, Oyvind Tafjord, Kyle Richardson
- Venue: Proceedings of the 29th International Joint Conference on Artificial Intelligence (IJCAI), pp. 3882–3890, 2020
- Identifier: arXiv:2002.05867

**Introduction:** Can a transformer learn to reason deductively over rules stated in natural language, without a formal representation [@clark2020]?

**Proposed Solution:** The authors generate synthetic datasets (RuleTaker) of facts and rules in controlled English, with statements labelled as provable or not under a closed-world assumption, at increasing reasoning depths, and train transformer models to predict the labels directly from the text.

**Results:** The models reached very high accuracy on test questions at depths seen in training, generalised partly to deeper questions and to paraphrased rule language, suggesting that transformers can emulate rule-based reasoning over language. Follow-up work generated explicit proofs [@tafjord2021].

**Gap / Limitation:** The models give an answer without a guarantee of soundness, and the labels assume a closed world, in which anything unprovable is false; this differs from the open-world semantics usually appropriate when information may be missing.

**Relevance:** RuleTaker is the benchmark of Calibra's logical pilot. Its closed-world labelling explains all 11 of the pilot's remaining misses after the parser fix (Chapter 14).

## Comparison with Calibra {#sec:lit-comparison}

@tab:lit-comparison compares the surveyed works with Calibra on six features: whether confidence or verification is computed per step or claim; whether several signals are fused; whether evidence from outside the model is used; whether the method adapts to the type of reasoning; whether it localises errors; and whether calibration is fitted or evaluated. "Partial" marks a feature present in a limited form, explained in the paper's entry above.

Table: Comparison of surveyed works with Calibra. {#tab:lit-comparison}

| Work | Step / claim level | Multi-signal fusion | External evidence | Type-adaptive | Error localisation | Calibration fitted / evaluated |
|---|---|---|---|---|---|---|
| Guo et al. (2017) | No | No | No | No | No | Yes |
| Arad & Rosset (2025) | No | No | No | No | No | Yes |
| Dogah (2026) | No | No | No | No | No | Yes |
| Kadavath et al. (2022) | No | Partial | No | No | No | Yes |
| Xiong et al. (2024) | No | Yes | No | No | No | Yes |
| Kuhn et al. (2023) | No | No | No | No | No | Partial |
| Lamb et al. (2025) | No | No | No | No | No | Yes |
| Manakul et al. (2023) | Sentence | No | No | No | Partial | Partial |
| Wang et al. (2023) | No | No | No | No | No | No |
| Chen et al. (2024) | No | No | No | No | No | Partial |
| Lightman et al. (2024) | Yes | No | No | No | Partial | No |
| Min et al. (2023) | Claim | No | Yes | No | Partial | No |
| Pan et al. (2023) | No | No | Yes (solver) | No | No | No |
| de Moura & Bjørner (2008) | — | — | Solver | — | — | — |
| Cobbe et al. (2021) | No | No | No | No | No | No |
| Clark et al. (2020) | No | No | No | No | No | No |
| **Calibra** | **Yes** | **Yes** | **Yes (web, solver)** | **Yes** | **Yes** | **Partial (metrics and calibrator implemented; fitting pending)** |

No surveyed work combines step-level confidence, multi-signal fusion, type-specific external evidence and error localisation. The calibration literature (Papers 1–3, 7) fits and evaluates confidence but treats each output as one unit; the LLM-confidence literature (Papers 4–10) estimates confidence for whole answers or sentences from the model's own signals; the step-level and verification literature (Papers 11–14) checks steps or claims but does not produce calibrated confidences. Chapter 4 turns these observations into the specific gaps that Calibra addresses, and states honestly which it does not.
