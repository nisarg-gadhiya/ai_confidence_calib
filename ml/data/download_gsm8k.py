from datasets import load_dataset


def load_gsm8k():

    print("Loading GSM8K...")

    dataset = load_dataset(
        "openai/gsm8k",
        "main",
    )

    print("\nDataset loaded successfully.")
    print(dataset)

    return dataset


if __name__ == "__main__":

    dataset = load_gsm8k()

    sample = dataset["test"][0]

    print("\n==============================")
    print("QUESTION")
    print("==============================")

    print(sample["question"])

    print("\n==============================")
    print("REFERENCE ANSWER")
    print("==============================")

    print(sample["answer"])