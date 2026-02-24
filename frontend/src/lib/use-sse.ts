"use client";

import { useEffect, useRef, useState, useCallback } from "react";

interface UseSSEResult {
  connected: boolean;
  error: string | null;
}

/**
 * React hook for subscribing to Server-Sent Events.
 * Creates an EventSource connection on mount, cleans up on unmount.
 * Auto-reconnects on connection loss with a 3-second delay.
 */
export function useSSE(
  url: string,
  onEvent: (event: string, data: unknown) => void
): UseSSEResult {
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const onEventRef = useRef(onEvent);

  // Keep the callback ref current without triggering reconnects
  onEventRef.current = onEvent;

  const connect = useCallback(() => {
    // Clean up any existing connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    const es = new EventSource(url);
    eventSourceRef.current = es;

    es.onopen = () => {
      setConnected(true);
      setError(null);
    };

    es.onerror = () => {
      setConnected(false);
      setError("SSE connection lost");
      es.close();

      // Auto-reconnect after 3 seconds
      reconnectTimerRef.current = setTimeout(() => {
        connect();
      }, 3000);
    };

    // Listen for named events
    es.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onEventRef.current("message", data);
      } catch {
        onEventRef.current("message", event.data);
      }
    };

    // Listen for custom named events (test, progress, complete, analysis, generation, etc.)
    const knownEvents = [
      "test",
      "progress",
      "complete",
      "error",
      "analysis_progress",
      "analysis_complete",
      "analysis_error",
      "generation_progress",
      "generation_complete",
      "generation_error",
    ];
    for (const eventName of knownEvents) {
      es.addEventListener(eventName, (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data);
          onEventRef.current(eventName, data);
        } catch {
          onEventRef.current(eventName, event.data);
        }
      });
    }
  }, [url]);

  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, [connect]);

  return { connected, error };
}
