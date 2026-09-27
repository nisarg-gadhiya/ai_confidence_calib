export default function ReasoningChain({
  steps,
}) {

  return (

    <section>

      {steps.map((step) => (

        <article
          key={step.step_number}
        >

          <h3>
            Step {step.step_number}
          </h3>

          <p>
            {step.step_text}
          </p>

        </article>

      ))}

    </section>
  );
}