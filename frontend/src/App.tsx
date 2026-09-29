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
    <main className="min-h-screen flex items-center justify-center p-6 bg-background text-foreground font-sans">
      <div className="w-full max-w-md p-6 bg-background border border-border rounded-control">
        <h1 className="text-page-title text-foreground">Camera Monitor</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Admin PC Monitoring Foundation (Step 01 Scaffold)
        </p>

        <div className="mt-6 pt-4 border-t border-border flex items-center justify-between text-sm">
          <span className="text-muted-foreground">Backend Health:</span>
          {isLoading && (
            <span className="text-muted-foreground tabular-nums">
              Checking...
            </span>
          )}
          {isError && (
            <span className="text-destructive tabular-nums">
              Error ({error instanceof Error ? error.message : "Failed"})
            </span>
          )}
          {data && (
            <span className="inline-flex items-center gap-1.5 tabular-nums text-foreground font-medium">
              <span className="inline-block size-2 rounded-full bg-status-online" />
              {data.status}
            </span>
          )}
        </div>
      </div>
    </main>
  );
}

export default App;
