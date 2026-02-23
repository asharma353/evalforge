"use client";

import { WIZARD_STEPS } from "@/lib/wizard-steps";

interface StepSidebarProps {
  activeStepId: string;
  completedStepIds: string[];
  onStepClick: (stepId: string) => void;
}

export default function StepSidebar({
  activeStepId,
  completedStepIds,
  onStepClick,
}: StepSidebarProps) {
  const activeIndex = WIZARD_STEPS.findIndex((s) => s.id === activeStepId);

  const canNavigateTo = (stepId: string): boolean => {
    if (completedStepIds.includes(stepId)) return true;
    const stepIndex = WIZARD_STEPS.findIndex((s) => s.id === stepId);
    // Can navigate to the next step after all previous steps are completed
    const allPreviousCompleted = WIZARD_STEPS.slice(0, stepIndex).every((s) =>
      completedStepIds.includes(s.id)
    );
    return allPreviousCompleted;
  };

  return (
    <aside
      className="w-72 shrink-0 border-r py-8 px-6 flex flex-col"
      style={{
        backgroundColor: "var(--color-surface)",
        borderColor: "var(--color-border)",
      }}
    >
      <div className="mb-8">
        <h1
          className="text-sm font-semibold tracking-wider uppercase"
          style={{ color: "var(--color-text-muted)" }}
        >
          Eval Builder
        </h1>
      </div>

      <nav className="flex flex-col gap-1">
        {WIZARD_STEPS.map((step) => {
          const isActive = step.id === activeStepId;
          const isCompleted = completedStepIds.includes(step.id);
          const isFuture =
            !isActive &&
            !isCompleted &&
            step.number > activeIndex + 1;
          const isClickable = canNavigateTo(step.id);

          return (
            <button
              key={step.id}
              onClick={() => isClickable && onStepClick(step.id)}
              disabled={!isClickable}
              className={`flex items-start gap-3 text-left rounded-lg px-3 py-3 transition-colors ${
                isClickable && !isActive
                  ? "cursor-pointer hover:bg-white/5"
                  : isActive
                  ? "cursor-default"
                  : "cursor-not-allowed"
              }`}
              style={
                isActive
                  ? { backgroundColor: "rgba(59, 130, 246, 0.08)" }
                  : undefined
              }
            >
              {/* Step number circle */}
              <div
                className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-medium shrink-0 mt-0.5"
                style={
                  isActive
                    ? {
                        backgroundColor: "var(--color-accent)",
                        color: "#ffffff",
                      }
                    : isCompleted
                    ? {
                        backgroundColor: "var(--color-accent)",
                        color: "#ffffff",
                      }
                    : {
                        backgroundColor: "transparent",
                        border: "1.5px solid var(--color-border)",
                        color: "var(--color-text-muted)",
                      }
                }
              >
                {isCompleted ? (
                  <svg
                    width="14"
                    height="14"
                    viewBox="0 0 14 14"
                    fill="none"
                    xmlns="http://www.w3.org/2000/svg"
                  >
                    <path
                      d="M11.5 3.5L5.5 10.5L2.5 7.5"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                ) : (
                  step.number
                )}
              </div>

              {/* Step label and description */}
              <div className="flex flex-col min-w-0">
                <span
                  className="text-sm font-medium leading-tight"
                  style={{
                    color: isActive
                      ? "var(--color-text)"
                      : isCompleted
                      ? "var(--color-text)"
                      : "var(--color-text-muted)",
                  }}
                >
                  {step.label}
                </span>
                <span
                  className="text-xs leading-snug mt-0.5"
                  style={{
                    color: isActive
                      ? "var(--color-text-muted)"
                      : "var(--color-text-muted)",
                    opacity: isFuture ? 0.6 : 1,
                  }}
                >
                  {step.description}
                </span>
              </div>
            </button>
          );
        })}
      </nav>
    </aside>
  );
}
