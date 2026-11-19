# Sample Run Outputs

This appendix shows the complete pipeline response for one stored run of each pipeline, as returned by `POST /api/ask` and stored under `pipeline_output` in `backend/data/calibration_runs.json`. To fit the page, numbers are rounded to four decimals, long strings are shortened (marked “...”), and lists with more than two items show the first two. Run numbers count from 1 in the order stored.

## Arithmetic run

Run 21, stored 2026-11-19 16:53:58 UTC, answer confidence 0.627.

```json
{
 "question": "Every day, Wendi feeds each of her chickens three cups of mixed chicken feed, containing seeds, mealworms and vegetables to help keep the...",
 "reasoning": [
  {
   "step_number": 1,
   "step_text": "Calculate the total amount of feed needed for 20 chickens for one day.",
   "step_type": "setup",
   "verification_score": 1.0,
   "consistency_score": 0.2,
   "sample_agreement_score": 0.2,
   "semantic_entropy": null,
   "consistency_method": "exact_match_fallback",
   "mean_token_logprob": -0.2097,
   "token_entropy": 0.1602,
   "fused_confidence": 0.7222,
   "verification_rationale": "The proposed step correctly identifies the need to calculate the total amount of feed required for the chickens in a day, which is essent...",
   "sample_count": 5
  },
  {
   "step_number": 2,
   "step_text": "Each chicken needs 3 cups of feed per day, so for 20 chickens: 20 * 3 = 60 cups.",
   "step_type": "arithmetic",
   "verification_score": 1.0,
   "consistency_score": 0.2,
   "sample_agreement_score": 0.2,
   "semantic_entropy": 1.0,
   "consistency_method": "model_semantic_clusters",
   "mean_token_logprob": -0.2376,
   "token_entropy": 0.1512,
   "fused_confidence": 0.6271,
   "verification_rationale": "The proposed step correctly calculates the total amount of feed needed for 20 chickens by multiplying the number of chickens by the amoun...",
   "sample_count": 5
  },
  "... 4 more"
 ],
 "predicted_error_step": 2,
 "final_answer": "20 cups",
 "final_answer_confidence": 0.6271,
 "confidence_method": "type_adaptive_weighted_proxy"
}
```

## Factual run

Run 16, stored 2026-11-19 16:21:28 UTC, answer confidence 0.900.

```json
{
 "question": "Which mission first landed humans on the Moon, and who was the first person to walk on its surface??",
 "final_answer": "The Apollo 11 mission first landed humans on the Moon, and Neil Armstrong was the first person to walk on its surface.",
 "steps": [
  {
   "step_id": 1,
   "text": "The Apollo 11 mission was the first to land humans on the Moon.",
   "claims": [
    {
     "claim_id": "c1_1",
     "text": "The Apollo 11 mission was the first to land humans on the Moon.",
     "essential": true,
     "verification": {
      "verdict": "SUPPORT",
      "evidence_score": 1.0
     },
     "self_verification_score": 0.9,
     "consistency_score": 1.0,
     "calibrated_probability": 0.8882,
     "sources": [
      {
       "source_id": "web_1",
       "title": "https://astrobiology.nasa.gov/missions/apollo-11/?utm_source=openai",
       "url": "https://astrobiology.nasa.gov/missions/apollo-11/?utm_source=openai",
       "domain": "astrobiology.nasa.gov",
       "text_origin": "fetched_webpage_content",
       "reliability_method": "domain_type_policy",
       "reliability_score": 0.96,
       "status": "KEEP",
       "text": "The Apollo 11 mission marked the first time that human explorers traveled beyond the Earth to set..."
      },
      {
       "source_id": "web_2",
       "title": "Apollo 11 - NASA",
       "url": "https://www.nasa.gov/mission/apollo-11/?utm_source=openai",
       "domain": "nasa.gov",
       "text_origin": "fetched_webpage_content",
       "reliability_method": "domain_type_policy",
       "reliability_score": 0.96,
       "status": "KEEP",
       "text": "Watch highlights from the Apollo 11 mission including the launch on July 16, 1969, the landing of..."
      }
     ]
    }
   ]
  },
  {
   "step_id": 2,
   "text": "Neil Armstrong was the first person to walk on the Moon's surface.",
   "claims": [
    {
     "claim_id": "c2_1",
     "text": "Neil Armstrong was the first person to walk on the Moon's surface.",
     "essential": true,
     "verification": {
      "verdict": "SUPPORT",
      "evidence_score": 1.0
     },
     "self_verification_score": 1.0,
     "consistency_score": 1.0,
     "calibrated_probability": 0.9002,
     "sources": [
      {
       "source_id": "web_1",
       "title": "https://science.nasa.gov/moon/moon-walkers/?utm_source=openai",
       "url": "https://science.nasa.gov/moon/moon-walkers/?utm_source=openai",
       "domain": "science.nasa.gov",
       "text_origin": "fetched_webpage_content",
       "reliability_method": "domain_type_policy",
       "reliability_score": 0.96,
       "status": "KEEP",
       "text": "Neil Armstrong and Edwin \"Buzz\" Aldrin were the first of 12 human beings to walk on the Moon. One..."
      },
      {
       "source_id": "web_2",
       "title": "Apollo 11 - NASA",
       "url": "https://www.nasa.gov/mission/apollo-11/?utm_source=openai",
       "domain": "nasa.gov",
       "text_origin": "citation_linked_model_summary",
       "reliability_method": "domain_type_policy",
       "reliability_score": 0.96,
       "status": "KEEP",
       "text": "On July 20, 1969, Commander Neil Armstrong became the first person to walk on the lunar surface, ..."
      },
      "... 1 more"
     ]
    }
   ]
  },
  "... 1 more"
 ],
 "predicted_error_step": 1,
 "answer_confidence": 0.9002,
 "answer_confidence_status": "ok",
 "calibration_status": "fixed_sigmoid_not_empirically_calibrated"
}
```

## Logical run

Run 29, stored 2026-11-19 17:24:05 UTC, answer confidence 0.882.

```json
{
 "question": "All pilots are crew members. If someone is a crew member and someone is a safety officer then someone is an emergency coordinator. All em...",
 "final_answer": "Yes. Niko is certified operator.",
 "premises": [
  {
   "premise_id": "p1",
   "text": "All pilots are crew members."
  },
  {
   "premise_id": "p2",
   "text": "If someone is a crew member and someone is a safety officer then someone is an emergency coordina..."
  },
  "... 3 more"
 ],
 "rules": [
  {
   "rule_id": "r1",
   "text": "All pilots are crew members.",
   "antecedents": [
    "$X is pilot"
   ],
   "consequents": [
    "$X is crew member"
   ],
   "disjunctive": false
  },
  {
   "rule_id": "r2",
   "text": "If someone is a crew member and someone is a safety officer then someone is an emergency coordina...",
   "antecedents": [
    "$X is crew member",
    "$X is safety officer"
   ],
   "consequents": [
    "$X is emergency coordinator"
   ],
   "disjunctive": false
  },
  "... 1 more"
 ],
 "steps": [
  {
   "step_id": 1,
   "text": "Niko is crew member.",
   "reasoning_operation": "modus_ponens",
   "premises_used": [
    "p4"
   ],
   "rules_used": [
    "r1"
   ],
   "claims": [
    {
     "claim_id": "c1_1",
     "text": "Niko is crew member.",
     "essential": false,
     "verification": {
      "verdict": "ENTAILED",
      "logical_validity_score": 1.0,
      "premises_used": [
       "p1",
       "p4"
      ],
      "rules_used": [
       "r1"
      ],
      "reasoning_operation": "solver_entailment_check"
     },
     "self_verification_score": 1.0,
     "consistency_score": 1.0,
     "calibrated_probability": 0.9002
    }
   ],
   "consistency_method": "model_semantic_clusters",
   "semantic_entropy": -0.0,
   "sample_count": 5
  },
  {
   "step_id": 2,
   "text": "Niko is emergency coordinator.",
   "reasoning_operation": "modus_ponens",
   "premises_used": [
    "p4",
    "p5"
   ],
   "rules_used": [
    "r1",
    "r2"
   ],
   "claims": [
    {
     "claim_id": "c2_1",
     "text": "Niko is emergency coordinator.",
     "essential": false,
     "verification": {
      "verdict": "ENTAILED",
      "logical_validity_score": 1.0,
      "premises_used": [
       "p1",
       "p2",
       "... 2 more"
      ],
      "rules_used": [
       "r1",
       "r2"
      ],
      "reasoning_operation": "solver_entailment_check"
     },
     "self_verification_score": 0.4,
     "consistency_score": 0.2,
     "calibrated_probability": 0.6602
    }
   ],
   "consistency_method": "model_semantic_clusters",
   "semantic_entropy": 1.0,
   "sample_count": 5
  },
  "... 1 more"
 ],
 "inconsistency_detected": false,
 "contradictions": [],
 "unsupported_premises": [],
 "predicted_error_step": 2,
 "answer_confidence": 0.8816,
 "answer_confidence_status": "ok",
 "calibration_status": "fixed_sigmoid_not_empirically_calibrated"
}
```
