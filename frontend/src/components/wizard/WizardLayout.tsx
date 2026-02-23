"use client";

import { useState } from "react";
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

  return (
    <div className="flex h-screen" style={{ backgroundColor: "var(--color-bg)" }}>
      <StepSidebar
        activeStepId={activeStepId}
        completedStepIds={completedStepIds}
        onStepClick={handleStepClick}
      />
      <StepContent activeStepId={activeStepId} />
    </div>
  );
}
