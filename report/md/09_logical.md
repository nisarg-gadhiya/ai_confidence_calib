# Methodology III: Logical Pipeline

The logical pipeline answers questions whose answer must be *deduced* from premises given in the question, as in the RuleTaker benchmark [@clark2020]: a set of facts ("Anne is red"), a set of rules ("All red things are round") and a query ("Is Anne round?"). For such questions there is a ground truth that does not depend on any model: the query either follows from the premises, its negation follows, or neither does. Calibra therefore does not ask a language model whether the answer is right. It translates the premises into first-order logic and lets the Z3 SMT solver [@demoura2008] decide, uses a forward-chaining engine to build a human-readable proof, and then scores each proof step. This combination of an LLM front end with a symbolic solver follows the approach of Logic-LM [@pan2023logiclm], with the addition of step-level confidence. @fig:logical-flow gives the overview.

![Logical pipeline. The solver decides the verdict; the rule engine supplies the proof steps that are scored.](logical_pipeline.png){#fig:logical-flow}

## Premise and Target Extraction {#sec:logical-premises}

The question text is split into sentences at terminal punctuation and line breaks. Sentences that end in a question mark are queries; the last one is the *target*. Sentences that start with an instruction verb ("Identify", "Determine", "Suppose", …) are dropped. Every remaining sentence becomes a premise with an identifier `p1`, `p2`, …, in order. The target question is turned into a statement by removing the leading auxiliary verb ("Is", "Are", "Does", …) and the word "necessarily"; for example "Is Anne round?" becomes "Anne round", which is parsed into the atom round(anne).

### Atoms

Sentences are parsed into *atoms*, the basic propositions of the logic. An atom has a subject, a predicate, an optional object and a polarity (@tab:atoms). Words are lower-cased, articles are removed, a few irregular forms are mapped to a base form ("studies" → "study", "is" → "be"), and plural nouns of five or more letters lose a final "s" so that "mammals" and "mammal" match. Relations such as "taller than" and "before" become binary predicates. Sentences of the form "P is true / false" or a single capital letter become propositional atoms, which supports textbook-style propositional questions.

Table: Atom forms recognised by the parser (`logical/rules/extractor.py`). {#tab:atoms}

| Sentence | Atom | Logic form |
|---|---|---|
| Anne is red. | subject `anne`, predicate `red` | red(anne) |
| Bob is not kind. | subject `bob`, predicate `kind`, negated | ¬kind(bob) |
| Tom is a cat. | subject `tom`, predicate `cat` | cat(tom) |
| Alice is taller than Bob. | subject `alice`, predicate `taller_than`, object `bob` | taller_than(alice, bob) |
| P is true. / Q | propositional | P, Q |
| something is cold (inside a rule) | subject variable `$x` | cold(x) |

## Rule Extraction {#sec:logical-rules}

A premise is treated as a rule if it is a universal statement, a conditional, a symbolic implication or a disjunction; otherwise it is a fact. The extractor recognises:

- **Universals**: "All A are B", including generic plurals with a head noun ("All furry things are round", "Kind, young people are nice") and bare generic plurals without *all* ("Red things are big"). The qualifiers before the head noun (*things*, *people*, *ones*, …) become the conditions, and the predicate after *are* becomes the conclusion: ∀x (furry(x) → round(x)). Comma- or *and*-separated qualifiers become a conjunction: "All rough, green things are not nice" is ∀x (rough(x) ∧ green(x) → ¬nice(x)).
- **Conditionals**: "If A then B" or "If A, B". Conjunctions in the condition share a subject: in "If something is green and cold then it is furry", the bare clause "cold" receives the subject of the clause before it, giving green(x) ∧ cold(x) → furry(x).
- **Variables and pronouns**: indefinite subjects (*someone*, *something*, *anyone*, *everything*, …) and *they/he/she* become the variable x. Inside a rule whose condition contains the variable, the pronouns *it*, *them*, *him*, *her* in any clause are bound to the same variable. A plain fact such as "It is raining" keeps its literal subject.
- **Symbolic implications**: "A -> B", "A => B", "A implies B".
- **Disjunctions**: "A or B" as a fact, and "If A then B or C" with a disjunctive conclusion.

### The parser defect found by the pilot

The original extractor knew *someone* and *they* as variables but not *something* and *it*, which RuleTaker uses almost exclusively; it kept the head noun of generic plurals, so "All furry things are round" required the predicate "furry thing", which no fact ever has; it dropped bare generic plurals ("Red things are big") entirely; and it gave the second clause of a conjunction the subject `$prop`. On the example in @fig:z3-example, eight rule sentences produced only seven rules, none of which could ever fire, and the forward-chaining engine derived nothing. Every proof therefore consisted of the target alone, and every query that needed a rule was answered UNKNOWN. The defect was found by inspecting why the RuleTaker pilot produced one-step proofs for nearly every question; fixing it raised verdict accuracy on the 44 completed pilot questions from 29 to 33 (Chapter 14). Regression tests for each case were added (Chapter 15).

## Z3 Encoding and Verdicts {#sec:logical-z3}

The solver (`logical/rules/solver.py`) encodes the knowledge base in first-order logic over an uninterpreted sort `Entity`:

- each constant (anne, bob, …) is a Z3 constant of sort `Entity`;
- each unary predicate is a function `Entity → Bool`, and each binary relation a function `Entity × Entity → Bool`;
- each propositional symbol is a Boolean constant;
- a fact is asserted directly, negated if needed;
- a rule is asserted as a universally quantified implication, ∀x (antecedents → consequents), with a conjunction or disjunction of consequents as appropriate; a rule without variables is asserted without the quantifier;
- for every transitive relation that appears (*taller than*, *before*, …), a transitivity axiom ∀x ∀y ∀z (R(x, y) ∧ R(y, z) → R(x, z)) is added.

Each premise and rule is asserted with `assert_and_track` under its own tracking label, so that when the solver proves unsatisfiability it can report an *unsat core*, the subset of premises and rules that the proof needed. A solver timeout of 5 seconds bounds every check. Sentences that look like rules but could not be parsed are recorded as *unsupported premises*; if any exist, every query returns UNKNOWN with the reason "Some premise syntax could not be represented safely", because answering from a partial encoding could be unsound.

### Checking a claim

Let $\Gamma$ be the encoded premises and rules and $\varphi$ the claim. The solver first checks that $\Gamma$ is satisfiable; if it is not, the premises are *inconsistent* (anything follows), the unsat core identifies the conflicting premises and rules, and the pipeline returns "The supplied premises are inconsistent" without a confidence. Otherwise:

$$\mathrm{verdict}(\varphi) = \begin{cases} \text{ENTAILED} & \text{if } \Gamma \cup \{\neg\varphi\} \text{ is unsatisfiable} \\ \text{CONTRADICTED} & \text{else if } \Gamma \cup \{\varphi\} \text{ is unsatisfiable} \\ \text{UNKNOWN} & \text{otherwise} \end{cases}$$ {#eq:verdict}

Each check is made in a solver scope (`push` / `pop`) so that the query does not remain asserted. For ENTAILED and CONTRADICTED verdicts the unsat core gives `premises_used` and `rules_used`, which are shown in the interface and stored. @fig:z3-example traces the check for "Is Anne round?" in the example knowledge base.

![Worked Z3 check for the query "Is Anne round?". The negated claim is unsatisfiable with the premises and rules, so the claim is entailed.](z3_example.png){#fig:z3-example}

### Open-world semantics

Z3 decides entailment under *open-world* semantics: a statement that cannot be proved is UNKNOWN, not false. RuleTaker, in contrast, labels questions under a *closed-world* assumption, in which anything that cannot be proved is false. The two disagree exactly on questions such as "Is Bob not quiet?" when nothing about Bob's quietness can be derived: RuleTaker's gold label is *entailment* (Bob is not quiet, because quietness is unprovable), while Calibra answers UNKNOWN. Calibra keeps open-world semantics deliberately, because in real use a missing premise usually means missing information, not a negative fact, and asserting "No" from silence would be unsound. The cost is a systematic disagreement with part of the benchmark's labels, quantified in Chapter 14.

## Proof Construction {#sec:logical-proof}

The solver decides the verdict but does not produce readable steps. A separate forward-chaining rule engine (`logical/rules/rule_engine.py`) builds them. Starting from the facts, it repeatedly matches every rule's conditions against the known facts (unifying the variable x with a constant), instantiates the conclusions, and adds any new fact. It also applies transitivity for transitive relations. Each derived fact records the operation that produced it (`modus_ponens` or `transitivity`), its depth, the premises and rules it depends on, and the facts it was derived from (its parents). The engine stops when a pass adds nothing new, or after a bounded number of passes.

Forward chaining derives *every* consequence of the premises, many of them irrelevant to the query. In the example knowledge base it derives "Anne is round" and "Erin is rough", but only the first matters for "Is Anne round?". The proof steps are therefore restricted to the *proof path*: starting from the target (or its negation, for a CONTRADICTED query), the pipeline walks back through the parent facts and keeps only the derivations it reaches, in derivation order. If the target was not derived (UNKNOWN, or a target stated directly as a premise), the target itself is the single step. Restricting the steps to the proof path also bounds cost, since every step is scored with model calls.

The engine is only an explanation device: the solver is authoritative for the verdict, and the engine's steps are each re-checked by the solver (@sec:logical-scoring).

## Step Scoring {#sec:logical-scoring}

Each proof step is an atom. For every step the pipeline computes three signals.

**Logical validity.** The step's atom is checked by the solver with @eq:verdict. Validity is the fraction of the step's verification checks that pass, which in the current implementation is 1 when the atom is ENTAILED and 0 otherwise:

$$L_i = \begin{cases} 1 & \mathrm{verdict}(\varphi_i) = \text{ENTAILED} \\ 0 & \text{otherwise} \end{cases}$$ {#eq:validity}

**Self-verification and consistency.** As in the arithmetic pipeline, the model generates K next-step continuations from the preceding proof steps (temperature 0.8) and an independent verifier returns `p_true` for the step together with semantic cluster ids for the samples. Consistency is the share of the largest cluster (@eq:consistency); when the knowledge base contains contradictory atoms it is additionally scaled by the share of facts not involved in a contradiction:

$$A'_i = A_i \cdot \frac{\max(0,\; F - 2X)}{F}$$ {#eq:logical-consistency}

where $F$ is the number of known facts and $X$ the number of contradictory atom pairs. If the model proposed a step whose atom matches the engine's step, the model's wording is used for the verifier prompt; otherwise the engine's text is used.

The three signals are fused and calibrated with the same weights and sigmoid as the factual pipeline (@eq:factual-calibration), with logical validity in place of the evidence score: $f = 0.4\,V + 0.3\,A' + 0.3\,L$, $p = \sigma(-1 + 3.2 f)$. The step whose atom is the target is marked *essential*; the answer confidence is the geometric mean over essential claims (@eq:geomean), which with a single target equals the target step's probability. The predicted error step is the step with the lowest probability. The final answer is "Yes. {target}." for ENTAILED, "No. {target} does not follow." for CONTRADICTED, and "It cannot be determined from the supplied premises." for UNKNOWN.

### What the confidence means

The answer confidence of a logical question is, by construction, the calibrated probability of the *target claim*, scored partly by whether the solver entails that claim. When the correct answer is "No" (a CONTRADICTED target) or "cannot be determined" (UNKNOWN), the target claim is not entailed, its validity is 0, and the confidence is low even though the answer may be exactly right. The confidence therefore measures belief that the queried statement holds, not belief that the system's answer is correct. This distinction is the main reason why answer confidence and correctness are poorly aligned in the logical pilot, and Chapter 14 quantifies it. Aligning the two, for example by scoring the claim that the *answer* expresses (the negated target for "No"), is listed as future work.

## Worked Example {#sec:logical-example}

The stored run for "All pilots are crew members. If someone is a crew member and someone is a safety officer then someone is an emergency coordinator. All emergency coordinators are certified operators. Niko is a pilot. Niko is a safety officer. Is Niko a certified operator?" produced the three-step proof Niko is crew member → Niko is emergency coordinator → Niko is certified operator, using rules r1–r3 and premises p4–p5. The solver entailed all three steps (validity 1). The model's sampled continuations agreed on steps 1 and 3 (consistency 1.0 and 0.8) but not on step 2 (0.2), where the verifier also gave `p_true` = 0.4; step 2 therefore received the lowest probability (0.660) and was flagged, although it is logically valid. The answer was "Yes. Niko is certified operator." with confidence 0.882, the probability of the essential step 3. This run is analysed further in Chapter 14 as an example of a *false alarm*: the flag reflects the model's uncertainty about which inference to make next, not an error.

## Limitations of the Logical Pipeline {#sec:logical-limitations}

- **Controlled language only.** The parser handles the sentence patterns of RuleTaker-style text and simple propositional logic. Free-form arguments, quantifiers such as *some* or *most*, and nested clauses are recorded as unsupported, and the query then returns UNKNOWN.
- **Open-world mismatch.** Benchmarks labelled under a closed-world assumption will disagree with Calibra on unprovable negations.
- **Validity is binary.** $L_i$ is 0 or 1, so for valid steps the variation in confidence comes entirely from the model-based signals.
- **Confidence of the claim, not the answer.** As explained above, "No" and "cannot be determined" answers receive low confidence by construction.
- **Sampling suits proofs poorly.** When many inferences are valid at a given point, the K next-step samples legitimately diverge, which lowers consistency for a correct step.
