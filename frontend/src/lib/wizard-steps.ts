export interface WizardStep {
  id: string;
  number: number;
  label: string;
  description: string;
}

export const WIZARD_STEPS: WizardStep[] = [
  {
    id: "upload",
    number: 1,
    label: "Upload",
    description: "Provide your codebase folder path",
  },
  {
    id: "analyze",
    number: 2,
    label: "Analyze",
    description: "AI analyzes your code patterns",
  },
  {
    id: "questions",
    number: 3,
    label: "Questions",
    description: "Answer targeted questions about your app",
  },
  {
    id: "generate",
    number: 4,
    label: "Generate",
    description: "Generate evaluators and test data",
  },
  {
    id: "export",
    number: 5,
    label: "Export",
    description: "Download your eval suite",
  },
];
