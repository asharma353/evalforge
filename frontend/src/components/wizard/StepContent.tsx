"use client";

import { WIZARD_STEPS } from "@/lib/wizard-steps";
import UploadStep from "./steps/UploadStep";

interface StepContentProps {
  activeStepId: string;
  onStepComplete: (stepId: string) => void;
}

export default function StepContent({
  activeStepId,
  onStepComplete,
}: StepContentProps) {
  const activeStep = WIZARD_STEPS.find((s) => s.id === activeStepId);

  if (!activeStep) return null;

  if (activeStep.id === "upload") {
    return <UploadStep onStepComplete={onStepComplete} />;
  }

  return (
    <div className="flex-1 p-8 flex items-center justify-center">
      <div className="text-center max-w-md">
        <div
          className="w-12 h-12 rounded-full flex items-center justify-center text-lg font-medium mx-auto mb-4"
          style={{
            backgroundColor: "var(--color-surface)",
            border: "1px solid var(--color-border)",
            color: "var(--color-text-muted)",
          }}
        >
          {activeStep.number}
        </div>
        <h2
          className="text-xl font-semibold mb-2"
          style={{ color: "var(--color-text)" }}
        >
          {activeStep.label}
        </h2>
        <p
          className="text-sm"
          style={{ color: "var(--color-text-muted)" }}
        >
          Coming soon
        </p>
      </div>
    </div>
  );
}
