"use client";

import { useState, useCallback } from "react";
import StepSidebar from "./StepSidebar";
import StepContent from "./StepContent";
import { WIZARD_STEPS } from "@/lib/wizard-steps";

export default function WizardLayout() {
  const [activeStepId, setActiveStepId] = useState("upload");
  const [completedStepIds, setCompletedStepIds] = useState<string[]>([]);

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
      />
    </div>
  );
}
