# Methodology II: Factual Pipeline

The factual pipeline answers open-domain knowledge questions, such as TriviaQA questions [@joshi2017], and scores every factual claim in its answer against evidence retrieved from the web. Its central idea is borrowed from fine-grained factuality evaluation [@min2023]: a long answer is not simply right or wrong, so it is split into *atomic claims* that can each be checked independently. Calibra adds two things to that idea: every claim receives a confidence built from several signals, not only a verdict, and every piece of evidence is weighted by the reliability of the source it came from. This chapter follows a question through the pipeline (@fig:factual-flow).

![Factual pipeline. Every atomic claim is searched, its sources are scored for reliability, and the evidence is judged and fused into a claim confidence.](factual_pipeline.png){#fig:factual-flow}

## Answer Generation and Decomposition {#sec:factual-decomposition}

### Generation

The question is answered once at temperature 0 with a dedicated system prompt (`FACTUAL_REASONING_PROMPT`, Appendix C). It asks for a JSON object with a `steps` array and a `final_answer`, and constrains the content of the steps: each step must be "a concise, verifiable factual statement that supports the answer", and instruction-like steps such as "identify", "recall" or "verify" are forbidden. The final answer must answer the question directly and must say plainly if the answer cannot be determined. These constraints exist because a step such as "Identify the creator of The Chipmunks" cannot be verified against evidence, and earlier versions of the pipeline produced many such steps (the TriviaQA pilot shows them; Chapter 14).

When the model returns a final answer, it is appended as an additional step, marked as the *answer step*. The answer step's claims determine the answer confidence, so the confidence describes the answer the user reads and not only its supporting statements.

### Claim extraction

Each step is split into atomic claims by `extract_claims`. The splitter breaks a step at the conjunctions *and*, *but*, *however* and *also*, then merges back any *and*-joined fragment that does not contain a verb of its own. For example, "LSTM has an input gate and a forget gate" stays one claim, because "a forget gate" has no predicate, while "LSTM was introduced in 1997 and it uses gates" becomes two claims. Predicates are recognised by a list of auxiliary and common content verbs. Each claim receives an identifier `c{step}_{n}` and keeps a reference to its step. Duplicate clauses within a step are removed.

The splitter is deliberately rule-based: it is deterministic, costs no model call, and its behaviour can be unit-tested. Its limitation is that it cannot resolve pronouns or split claims joined by commas, so some claims are not fully atomic. In the TriviaQA pilot, answers produced between 2 and 6 claims, 2.95 on average (n = 40).

## Web Retrieval {#sec:factual-retrieval}

### Search

For each claim, the pipeline calls the Responses API with the `web_search` tool (model `gpt-4.1-mini`, search context size *medium*, tool use required). The query contains both the original question and the claim ("Question: …  Claim to verify: …"), because the claim alone is often ambiguous out of context. The system message asks the model to search for reliable sources, to summarise only facts supported by the results, to cite every source, and not to invent citations.

The client then collects sources from two places in the response. URLs listed by the search action are recorded without text. URLs cited in the model's answer through `url_citation` annotations are recorded together with an excerpt: the sentence that ends at the citation marker, extended to about 280 characters around the citation if that sentence is too short, with citation markers removed and the length capped at 1,000 characters. Up to five distinct URLs are kept per claim. Each source records how its text was obtained (`text_origin`): `citation_linked_model_summary` for an excerpt of the model's cited answer, or `search_source_without_citation` when only the URL is known.

### Page fetching

A search excerpt is a model's paraphrase of a page, not the page itself. When a source's text is not relevant enough to the claim (relevance below 0.2, defined in @eq:relevance), the pipeline fetches the page and replaces the excerpt with the most relevant passages of the real page text, recording `text_origin = fetched_webpage_content`. At most two pages are fetched per claim, to bound latency. Fetching is restricted for safety: only `http` and `https` URLs without embedded credentials are accepted; the host name is resolved and *every* resolved address must be a public (globally routable) IP, which prevents the server from being used to reach internal network addresses; redirects are followed manually so each hop is checked again; the timeout is 3 seconds, the body is capped at 1 MB and the extracted text at 20,000 characters. HTML is converted to readable text by a parser that drops scripts, styles and other non-content elements. The page text is split into fragments, each fragment is scored for relevance to the claim, and the four best fragments with non-zero relevance are joined (up to 2,000 characters). Fetched pages are cached per URL within the process.

In the TriviaQA pilot, 145 of the 160 retained sources (91%) carried fetched page content and 15 carried citation-linked excerpts (Chapter 14), which shows that the fallback is the normal path rather than an exception.

### Relevance

Relevance is a lexical overlap score between a claim $c$ and a source text $s$. Let $W(\cdot)$ be the set of lower-cased word tokens with a small stop-word list removed. With $o = |W(c) \cap W(s)|$:

$$\mathrm{rel}(c, s) = \min\!\left(1,\; \frac{1}{2}\left(\frac{o}{|W(c)|} + \frac{o}{|W(c) \cup W(s)|}\right)\right)$$ {#eq:relevance}

The first term (coverage) asks how much of the claim the source mentions; the second (Jaccard similarity) penalises long, unfocused texts. A source with relevance below 0.2 is not used as evidence. The score is intentionally simple and cheap; it decides only *which* text the language model will later judge, and the judgement itself is semantic.

## Source Reliability {#sec:factual-reliability}

Not all evidence is equal: a government statistics page and an anonymous forum post that both "support" a claim should not contribute equally. Every source is therefore assigned a reliability weight by a domain policy (`factual/retrieval/source_reliability.py`). The policy has 22 tiers, from official government sources to user-edited fan wikis (@tab:reliability-tiers, @fig:reliability-tiers); Appendix E lists every named domain.

A source is classified in the following order of precedence:

1. **Named domain.** About three hundred registrable domains are listed by tier. A source matches a listed domain if its host equals the domain or ends with "." followed by the domain, so `news.bbc.co.uk` matches `bbc.co.uk` while `notbbc.co.uk` does not. When several entries match, the longest (most specific) wins.
2. **Domain-suffix rules.** Hosts ending in `.gov` or `.mil`, or with a government second-level label under a country code (`gov.uk`, `gov.in`, `gouv.fr`, `gob.mx`, `go.jp`, …), are *government*; `.int` hosts are *intergovernmental*; `.edu` hosts and academic second-level labels under a country code (`ac.uk`, `edu.au`, …) are *academic*. Hosts beginning with `blog.` are *blogs*; a list of top-level domains with a poor reputation (`.xyz`, `.top`, `.click`, …) is *low-trust*; other `.org` and `.net` hosts are *general organisation*.
3. **Source type from search.** If neither rule applies, an explicit type supplied upstream (for example `government` or `academic`) is used.
4. **Default.** Everything else is *general* (0.52).

A source labelled as a blog is capped at the blog weight (0.48) whatever its host, because self-published content does not inherit the reputation of the platform that hosts it.

Table: Source-reliability tiers, weights and filter bands. {#tab:reliability-tiers}

| Weight | Tier | Band | Examples |
|---|---|---|---|
| 0.97 | Government | KEEP | `.gov`, `gov.uk`, `go.jp`, `europa.eu`, `canada.ca` |
| 0.95 | Intergovernmental | KEEP | `.int`, `un.org`, `worldbank.org`, `oecd.org` |
| 0.93 | Academic | KEEP | `.edu`, `ac.uk`, `ethz.ch`, `cnrs.fr` |
| 0.92 | Scholarly publisher | KEEP | `nature.com`, `ieee.org`, `acm.org`, `doi.org` |
| 0.90 | Reference | KEEP | `britannica.com`, `ebsco.com`, `ourworldindata.org` |
| 0.88 | Standards / professional body | KEEP | `iso.org`, `w3.org`, `ietf.org`, `asme.org` |
| 0.86 | Preprint | KEEP | `arxiv.org`, `biorxiv.org`, `ssrn.com` |
| 0.84 | Wire service / public broadcaster | KEEP | `reuters.com`, `apnews.com`, `bbc.co.uk` |
| 0.82 | Reputable newspaper | KEEP | `nytimes.com`, `theguardian.com`, `thehindu.com` |
| 0.80 | Encyclopedic wiki | KEEP | `wikipedia.org`, `wikidata.org` |
| 0.78 | Official documentation | KEEP | `docs.python.org`, `developer.nvidia.com`, `ibm.com` |
| 0.76 | Established non-profit / museum | KEEP | `khanacademy.org`, `pewresearch.org`, `brookings.edu` |
| 0.70 | General news / magazine | DOWN_WEIGHT | `cnn.com`, `forbes.com`, `wired.com` |
| 0.62 | Educational / explainer | DOWN_WEIGHT | `investopedia.com`, `geeksforgeeks.org` |
| 0.58 | Technical Q&A | DOWN_WEIGHT | `stackoverflow.com`, `github.com` |
| 0.55 | Unknown `.org` / `.net` | DOWN_WEIGHT | suffix rule |
| 0.52 | Unknown site (default) | DOWN_WEIGHT | — |
| 0.48 | Blog / self-publishing | DOWN_WEIGHT | `medium.com`, `substack.com`, `blog.*` |
| 0.40 | Low-trust top-level domain | REJECT | `.xyz`, `.top`, `.info` |
| 0.38 | Forum / general Q&A | REJECT | `reddit.com`, `quora.com` |
| 0.32 | Social media / video | REJECT | `x.com`, `youtube.com`, `facebook.com` |
| 0.30 | Open user-edited wiki | REJECT | `fandom.com`, `wikihow.com` |

![Source-reliability policy. Colours show the band each tier falls into under the filter thresholds.](reliability_tiers.png){#fig:reliability-tiers}

The weights are spread so that the 22 tiers fall into all three bands of the reliability filter. A source with weight at least 0.75 is marked KEEP, at least 0.45 DOWN_WEIGHT, and below that REJECT. Rejected sources are discarded before evidence retrieval; kept and down-weighted sources are both used, but their weight multiplies their contribution to the evidence score (@eq:evidence). The REJECT band is reserved for user-generated content that is unsuitable as evidence for factual verification. Unknown sites fall in DOWN_WEIGHT, so an unfamiliar but legitimate source still counts, at reduced weight.

Two corrections were made to an earlier version of this policy during the project, and both are visible in the data. First, the earlier table had no entry for the `government` type that the search module produced, so government sources fell back to a default; and it raised any domain *containing* the letters "ent" (intended for "government") to 0.96, so a domain such as `entertainment.com` would have been treated as official. Domains are now matched on dot boundaries only. Second, almost every non-government source received the default 0.52, so a reference work and an unknown content site were indistinguishable. Re-scoring the 160 sources retrieved in the TriviaQA pilot with the current policy moves 35 sources into KEEP compared with 16 at the time of the run (Chapter 14).

## Claim Verification {#sec:factual-verification}

The relevant evidence items for a claim, each with its source identifier, title, domain and text (truncated to 2,000 characters), are sent to the language model in a single assessment call at temperature 0. The prompt instructs the model to use only the supplied evidence and no prior knowledge, and to return, for each evidence item, **SUPPORT** only when it directly supports the claim, **CONTRADICT** only when it directly conflicts with it, and **UNKNOWN** otherwise. The model also returns a `confidence` in the claim (described in the prompt as "a model estimate, not a statistically calibrated probability") and an `essential` flag saying whether the claim is needed to answer the question.

The client validates the result: verdicts for source identifiers that were not supplied are discarded, verdicts outside the three labels are discarded, a confidence outside [0, 1] or non-numeric is an error, and the confidence is forced to 0 when the claim had no evidence at all, because a judgement on nothing is not evidence of anything. Evidence items without a valid verdict count as UNKNOWN.

The claim's overall verdict is decided by weighted vote. With $r_e$ the source reliability and $\rho_e$ the relevance of evidence item $e$, let

$$S = \sum_{e \in \mathrm{SUPPORT}} r_e\,\rho_e, \qquad C = \sum_{e \in \mathrm{CONTRADICT}} r_e\,\rho_e, \qquad U = \sum_{e \in \mathrm{UNKNOWN}} r_e\,\rho_e$$ {#eq:evidence-weights}

The claim is SUPPORT if $S > C$, CONTRADICT if $C > S$, and UNKNOWN otherwise (including when there is no evidence).

## Signals {#sec:factual-signals}

Three signals are computed for each claim.

**Self-verification** is the assessment call's `confidence`, the model's estimate that the claim is true given the evidence.

**Evidence score** turns the weighted verdicts into a number in [0, 1]. When at least one item supports or contradicts the claim, it maps the net weighted support linearly from [−1, 1] to [0, 1]; when all evidence is UNKNOWN it returns a low score that rises slightly with the amount of unknown evidence; with no evidence it is 0:

$$E = \begin{cases} \dfrac{1}{2}\left(\dfrac{S - C}{S + C + U} + 1\right) & S + C > 0 \\ 0.2 + 0.4\,\min(1, U) & S = C = 0,\ U > 0 \\ 0 & \text{no evidence} \end{cases}$$ {#eq:evidence}

**Verdict consistency** is the share of evidence items that agree with the most common verdict, computed over the per-source verdicts. It measures agreement *between sources*, not between model samples: a claim supported by four sources and contradicted by one has consistency 0.8. The factual pipeline does not resample the model's answer; independent sources play the role that independent samples play in the arithmetic pipeline.

## Fusion, Calibration and Aggregation {#sec:factual-fusion}

The three signals are fused with fixed weights and mapped through a fixed logistic function:

$$f = 0.4\,V + 0.3\,A + 0.3\,E, \qquad p = \sigma(-1 + 3.2\,f) = \frac{1}{1 + e^{-(-1 + 3.2 f)}}$$ {#eq:factual-calibration}

where $V$ is self-verification, $A$ verdict consistency and $E$ the evidence score. The sigmoid maps $f = 0$ to $p = 0.269$, $f = 0.3125$ to $p = 0.5$ and $f = 1$ to $p = 0.900$ (Chapter 10, @fig:sigmoid). Its parameters were chosen by hand so that a claim with no support at all stays well below one half and a claim with perfect signals stays below certainty; they have not been fitted to labelled data. Every factual response is therefore labelled `fixed_sigmoid_not_empirically_calibrated`.

Claim probabilities are aggregated in two ways:

- **Step confidence and error localisation.** A step's probability is the *minimum* over its claims (a step is as reliable as its weakest claim); the predicted error step is the step with the lowest probability.
- **Answer confidence.** The geometric mean of the calibrated probabilities of the *essential* claims of the answer step, or of all claims if the answer step produced none:

$$C_{\mathrm{answer}} = \left(\prod_{j \in \mathcal{E}} p_j\right)^{1/|\mathcal{E}|}$$ {#eq:geomean}

where $\mathcal{E}$ is the set of essential claims. If any essential claim has probability 0 the answer confidence is 0. The geometric mean was chosen over the arithmetic mean because it is pulled down strongly by a single weak essential claim, and over the minimum because a factual answer often contains several essential claims of which one can be slightly weaker without the answer being wrong. Non-essential claims (background statements) do not affect the answer confidence.

### Final answer

The answer shown to the user depends on verification. If the last essential claim of the answer step is supported, the answer is the text of its supported essential claims (`answer_confidence_status = verified`). Otherwise the model's proposed answer is shown and marked `unverified_model_answer`, and if there is none the user is told that the answer could not be verified from the available evidence. The status is returned with every response.

## Worked Example {#sec:factual-example}

The stored run for the question "Which mission first landed humans on the Moon, and who was the first person to walk on its surface?" (19 November 2026) illustrates the pipeline. The model answered in three steps, each a single atomic claim. Every claim was SUPPORTED by its evidence, which came from five distinct sources including `nasa.gov` pages (government tier). The three claim probabilities were 0.888, 0.900 and 0.900, and the answer confidence, the geometric mean over the essential claims of the answer step, was 0.900. The first step was flagged as the weakest because its self-verification score was 0.9 rather than 1.0. Even with all evidence agreeing, the confidence is bounded above by 0.900, the value of the fixed sigmoid at $f = 1$. Chapter 11 shows the same run in the interface.

## Limitations of the Factual Pipeline {#sec:factual-limitations}

- **Lexical relevance.** The relevance score cannot match paraphrases or synonyms, so a relevant passage with different wording can be dropped before the model sees it.
- **Search excerpts are model summaries.** Citation-linked excerpts are written by a model; they are replaced by page text only when they look irrelevant. A fluent but wrong summary that happens to overlap the claim's words would be kept.
- **The judge is a language model.** SUPPORT and CONTRADICT verdicts come from an LLM and inherit its biases; agreement between the judge and the generator is not independent evidence.
- **Domain reputation is not page reliability.** A reliable domain can host an outdated or wrong page, and the policy cannot tell. The policy is also manually maintained.
- **Fixed calibration.** The fusion weights and sigmoid are hand-set and cap confidence at 0.900; they need fitting on labelled claims.
- **Web drift.** Search results change over time, so the same question can receive different evidence on different days (Chapter 16).
