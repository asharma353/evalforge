"use client";

import type { FailureModeResult, EvaluatorResult } from "@/lib/api";
import FailureModeCard from "./FailureModeCard";

interface EvaluatorListProps {
  failureModes: FailureModeResult[];
  evaluators: Record<string, EvaluatorResult>;
}

export default function EvaluatorList({ failureModes, evaluators }: EvaluatorListProps) {
  return (
    <div className="flex flex-col gap-3">
      {failureModes.map((failureMode) => (
        <FailureModeCard
          key={failureMode.id}
          failureMode={failureMode}
          evaluator={evaluators[failureMode.id] ?? null}
        />
      ))}
    </div>
  );
}
