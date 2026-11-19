import axios from "axios";


const api = axios.create({
  baseURL:
    import.meta.env.VITE_API_BASE_URL
    || "http://127.0.0.1:8000/api",
});


export async function askQuestion(
  question,
  numConsistencySamples = 5
) {

  const response = await api.post(
    "/ask",
    {
      question,
      num_consistency_samples:
        numConsistencySamples,
    }
  );

  return response.data;
}


export async function fetchRuns() {
  const response = await api.get("/runs");
  return response.data;
}


export function errorMessage(error, fallback) {
  const detail = error?.response?.data?.detail;
  if (Array.isArray(detail)) {
    return detail.map((d) => d?.msg || JSON.stringify(d)).join("; ");
  }
  if (typeof detail === "string" && detail) return detail;
  if (error?.code === "ERR_NETWORK") {
    return "Could not reach the backend. Check that the API server is running on port 8000 and allows this page's origin (CORS).";
  }
  return error?.message || fallback;
}
