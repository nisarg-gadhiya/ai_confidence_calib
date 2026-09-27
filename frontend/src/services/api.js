import axios from "axios";


const api = axios.create({
  baseURL: "http://127.0.0.1:8000/api",
});


export async function runInference(
  question,
  numConsistencySamples = 5
) {

  const response = await api.post(
    "/inference",
    {
      question,
      num_consistency_samples:
        numConsistencySamples,
    }
  );

  return response.data;
}