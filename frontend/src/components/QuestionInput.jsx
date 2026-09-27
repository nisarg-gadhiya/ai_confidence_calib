export default function QuestionInput({
  value,
  onChange,
  onSubmit,
  loading,
}) {

  return (

    <form
      onSubmit={onSubmit}
    >

      <textarea
        value={value}
        onChange={(event) =>
          onChange(event.target.value)
        }
        rows={6}
        placeholder="Enter question..."
      />

      <button
        type="submit"
        disabled={
          loading
          || !value.trim()
        }
      >

        {loading
          ? "Running..."
          : "Analyze"}

      </button>

    </form>
  );
}