"use client";

import { useState, useCallback } from "react";
import StepSidebar from "./StepSidebar";
import StepContent from "./StepContent";
import { WIZARD_STEPS } from "@/lib/wizard-steps";
import { useSSE } from "@/lib/use-sse";

export default function WizardLayout() {
  const [activeStepId, setActiveStepId] = useState("upload");
  const [completedStepIds, setCompletedStepIds] = useState<string[]>([]);
  const [stepData, setStepData] = useState<Record<string, unknown>>({});

  // Establish SSE connection for real-time progress streaming
  const { connected: sseConnected } = useSSE("/api/sse", useCallback((event: string, data: unknown) => {
    // SSE events will be handled by individual steps in later phases
    console.debug("[SSE]", event, data);
  }, []));

  // Suppress unused variable lint warning for sseConnected
  void sseConnected;

  const handleStepClick = (stepId: string) => {
    const stepIndex = WIZARD_STEPS.findIndex((s) => s.id === stepId);
    const allPreviousCompleted = WIZARD_STEPS.slice(0, stepIndex).every((s) =>
      completedStepIds.includes(s.id)
    );

    if (completedStepIds.includes(stepId) || allPreviousCompleted) {
      setActiveStepId(stepId);
    }
  };

  const handleStepComplete = useCallback(
    (stepId: string) => {
      setCompletedStepIds((prev) => {
        if (prev.includes(stepId)) return prev;
        return [...prev, stepId];
      });

      // Advance to the next step
      const currentIndex = WIZARD_STEPS.findIndex((s) => s.id === stepId);
      if (currentIndex < WIZARD_STEPS.length - 1) {
        setActiveStepId(WIZARD_STEPS[currentIndex + 1].id);
      }
    },
    []
  );

  const handleStepData = useCallback((stepId: string, data: unknown) => {
    setStepData((prev) => ({ ...prev, [stepId]: data }));
  }, []);

  return (
    <div className="flex h-screen" style={{ backgroundColor: "var(--color-bg)" }}>
      <StepSidebar
        activeStepId={activeStepId}
        completedStepIds={completedStepIds}
        onStepClick={handleStepClick}
      />
      <StepContent
        activeStepId={activeStepId}
        onStepComplete={handleStepComplete}
        onStepData={handleStepData}
        stepData={stepData}
      />
    </div>
  );
}
