"use client";

import { useState } from "react";

export interface CustomQAPair {
  id: string; // local-only React key (not sent to backend)
  question: string;
  answer: string;
}

interface CustomQAPanelProps {
  pairs: CustomQAPair[];
  onPairsChange: (pairs: CustomQAPair[]) => void;
}

function generateId(): string {
  return Math.random().toString(36).slice(2, 9);
}

export default function CustomQAPanel({ pairs, onPairsChange }: CustomQAPanelProps) {
  const [expanded, setExpanded] = useState(false);

  const addPair = () => {
    onPairsChange([...pairs, { id: generateId(), question: "", answer: "" }]);
    setExpanded(true);
  };

  const removePair = (id: string) => {
    onPairsChange(pairs.filter((p) => p.id !== id));
  };

  const updatePair = (id: string, field: "question" | "answer", value: string) => {
    onPairsChange(pairs.map((p) => (p.id === id ? { ...p, [field]: value } : p)));
  };

  return (
    <div className="mt-6 border border-zinc-700 rounded-lg">
      <button
        type="button"
        onClick={() => setExpanded((e) => !e)}
        className="w-full flex items-center justify-between px-4 py-3 text-sm font-medium text-zinc-300 hover:text-white hover:bg-zinc-800/50 rounded-lg transition-colors"
      >
        <span>
          Add custom context{" "}
          {pairs.length > 0 && (
            <span className="ml-1 text-xs text-zinc-500">({pairs.length} pair{pairs.length !== 1 ? "s" : ""})</span>
          )}
        </span>
        <span className="text-zinc-500 text-xs">{expanded ? "▲" : "▼"}</span>
      </button>

      {expanded && (
        <div className="px-4 pb-4 space-y-4">
          <p className="text-xs text-zinc-500">
            Add domain knowledge the analysis did not capture. Each pair is merged
            into the generation context.
          </p>

          {pairs.map((pair) => (
            <div key={pair.id} className="space-y-2 p-3 bg-zinc-800/40 rounded-md">
              <div className="flex items-start gap-2">
                <div className="flex-1 space-y-2">
                  <textarea
                    placeholder="Question (e.g. What domain are your users in?)"
                    value={pair.question}
                    onChange={(e) => updatePair(pair.id, "question", e.target.value)}
                    rows={2}
                    className="w-full bg-zinc-900 border border-zinc-700 rounded px-3 py-2 text-sm text-zinc-200 placeholder-zinc-600 focus:outline-none focus:border-zinc-500 resize-none"
                  />
                  <textarea
                    placeholder="Answer (e.g. Medical professionals reviewing patient records)"
                    value={pair.answer}
                    onChange={(e) => updatePair(pair.id, "answer", e.target.value)}
                    rows={2}
                    className="w-full bg-zinc-900 border border-zinc-700 rounded px-3 py-2 text-sm text-zinc-200 placeholder-zinc-600 focus:outline-none focus:border-zinc-500 resize-none"
                  />
                </div>
                <button
                  type="button"
                  onClick={() => removePair(pair.id)}
                  className="mt-1 text-zinc-600 hover:text-zinc-400 text-lg leading-none"
                  aria-label="Remove pair"
                >
                  ×
                </button>
              </div>
            </div>
          ))}

          <button
            type="button"
            onClick={addPair}
            className="flex items-center gap-1 text-sm text-zinc-400 hover:text-zinc-200 transition-colors"
          >
            <span>+</span> Add pair
          </button>
        </div>
      )}
    </div>
  );
}
