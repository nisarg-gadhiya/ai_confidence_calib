import React from "react";
import { useState } from "react";

import { runInference } from "./services/api";


export default function App() {

  const [question, setQuestion] =
    useState("");

  const [result, setResult] =
    useState(null);

  const [loading, setLoading] =
    useState(false);

  const [error, setError] =
    useState("");


  async function handleSubmit(event) {

    event.preventDefault();

    setLoading(true);
    setError("");

    try {

      const data =
        await runInference(question);

      setResult(data);

    } catch (err) {

      setError(
        err.response?.data?.detail
        || err.message
      );

    } finally {

      setLoading(false);
    }
  }


  return (

    <main
      style={{
        maxWidth: "900px",
        margin: "40px auto",
        padding: "20px",
        fontFamily: "Arial, sans-serif",
      }}
    >

      <h1>
        AI Confidence Calibration
      </h1>

      <p>
        Step-level confidence
        and error localization
        prototype.
      </p>


      <form
        onSubmit={handleSubmit}
      >

        <textarea
          rows={6}
          value={question}
          onChange={(event) =>
            setQuestion(
              event.target.value
            )
          }
          placeholder="Enter a GSM8K-style question..."
          style={{
            width: "100%",
            padding: "12px",
            boxSizing: "border-box",
          }}
        />


        <button
          type="submit"
          disabled={
            loading
            || !question.trim()
          }
          style={{
            marginTop: "12px",
            padding: "10px 16px",
          }}
        >

          {loading
            ? "Running..."
            : "Analyze reasoning"}

        </button>

      </form>


      {error && (

        <p>
          Error: {error}
        </p>

      )}


      {result && (

        <section
          style={{
            marginTop: "30px",
          }}
        >

          <h2>
            Reasoning
          </h2>


          {result.reasoning.map(
            (step) => (

              <article
                key={step.step_number}
                style={{
                  border:
                    "1px solid #ddd",
                  borderRadius: "8px",
                  padding: "16px",
                  marginBottom: "12px",
                }}
              >

                <strong>
                  Step {step.step_number}
                </strong>


                <p>
                  {step.step_text}
                </p>


                <div>
                  Verification:{" "}
                  {step.verification_score.toFixed(
                    2
                  )}
                </div>


                <div>
                  Consistency:{" "}
                  {step.consistency_score.toFixed(
                    2
                  )}
                </div>


                <div>
                  Confidence:{" "}
                  {step.fused_confidence.toFixed(
                    2
                  )}
                </div>

              </article>

            )
          )}


        <h3>
            Predicted error step:{" "}
            {result.predicted_error_step ?? "None"}
        </h3>

        <h3>Final Answer</h3>

        <p>
          {result.final_answer ?? "No final answer returned."}
        </p>

        </section>

      )}

    </main>
  );
}