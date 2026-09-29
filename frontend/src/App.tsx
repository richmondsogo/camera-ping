import { useQuery } from "@tanstack/react-query";

interface HealthResponse {
  status: string;
}

async function fetchHealth(): Promise<HealthResponse> {
  const response = await fetch("/api/health");
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  return response.json();
}

export function App() {
  const { data, isLoading, isError, error } = useQuery<HealthResponse>({
    queryKey: ["health"],
    queryFn: fetchHealth,
  });

  return (
    <main className="min-h-screen flex items-center justify-center p-6 bg-slate-50 text-slate-900 font-sans">
      <div className="w-full max-w-md p-6 bg-white border border-slate-200 rounded-lg shadow-xs">
        <h1 className="text-xl font-semibold tracking-tight text-slate-900">
          Camera Monitor
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          Admin PC Monitoring Foundation (Step 01 Scaffold)
        </p>

        <div className="mt-6 pt-4 border-t border-slate-100 flex items-center justify-between text-sm">
          <span className="text-slate-600">Backend Health:</span>
          {isLoading && (
            <span className="text-slate-400 font-mono">Checking...</span>
          )}
          {isError && (
            <span className="text-red-600 font-mono">
              Error ({error instanceof Error ? error.message : "Failed"})
            </span>
          )}
          {data && (
            <span className="inline-flex items-center gap-1.5 font-mono text-emerald-700 font-medium">
              <span className="inline-block w-2 h-2 rounded-full bg-emerald-500" />
              {data.status}
            </span>
          )}
        </div>
      </div>
    </main>
  );
}

export default App;
