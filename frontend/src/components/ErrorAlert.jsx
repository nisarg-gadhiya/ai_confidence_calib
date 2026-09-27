export default function ErrorAlert({
  stepNumber,
}) {

  if (!stepNumber) {
    return null;
  }

  return (

    <p>
      Lowest-confidence step:
      {" "}
      Step {stepNumber}
    </p>

  );
}