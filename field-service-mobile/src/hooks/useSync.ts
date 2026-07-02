import { useState, useCallback, useRef } from "react";
import { runSync, type SyncResult } from "../services/syncService";

type SyncStatus = "idle" | "syncing" | "success" | "error";

export function useSync() {
  const [status, setStatus] = useState<SyncStatus>("idle");
  const [lastResult, setLastResult] = useState<SyncResult | null>(null);
  const inFlight = useRef(false);

  const sync = useCallback(async (): Promise<SyncResult> => {
    if (inFlight.current) {
      return lastResult ?? { success: false, tasksReceived: 0, conflictsDetected: 0 };
    }
    inFlight.current = true;
    setStatus("syncing");
    const result = await runSync();
    setLastResult(result);
    setStatus(result.success ? "success" : "error");
    inFlight.current = false;
    return result;
  }, [lastResult]);

  return { status, lastResult, sync };
}
