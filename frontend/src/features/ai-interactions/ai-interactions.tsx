import { t, useLocale } from "../../shared/lib/i18n";
import { useMutation } from "@tanstack/react-query";
import { BookOpen, GitCompareArrows, MessageCircle, Sparkles } from "lucide-react";
import { useState, type FormEvent } from "react";

import { interactionsApi } from "../../entities/interactions/api";
import { ApiError } from "../../shared/api/client";
import type { GraphNode } from "../../shared/types/graph";
import type { Citation, CompareAnswer, GroundedAnswer, WhyAnswer } from "../../shared/types/interactions";
import { Button } from "../../shared/ui/button";
import { Card } from "../../shared/ui/card";
import { Input } from "../../shared/ui/input";

export function ConceptInsights({ conceptId }: { conceptId: string }) {
  useLocale();
  const [answer, setAnswer] = useState<GroundedAnswer | WhyAnswer>();
  const request = useMutation({
    mutationFn: ({ action, mode }: { action: "explain" | "why"; mode?: "standard" | "simpler" }) =>
      action === "why"
        ? interactionsApi.why(conceptId)
        : interactionsApi.explain(conceptId, mode ?? "standard"),
    onSuccess: setAnswer,
  });
  return (
    <div className="border-t border-ink/10 pt-4">
      <div className="flex flex-wrap gap-2">
        <Button className="h-9 px-4" onClick={() => request.mutate({ action: "explain" })}> {t("Explain")} </Button>
        <Button variant="secondary" className="h-9 px-4" onClick={() => request.mutate({ action: "explain", mode: "simpler" })}> {t("Simpler")} </Button>
        <Button variant="secondary" className="h-9 px-4" onClick={() => request.mutate({ action: "why" })}> {t("Why?")} </Button>
      </div>
      {request.isPending && <p className="mt-3 text-xs text-ink/45">{t("Building a grounded answer…")}</p>}
      {request.error && <InteractionError error={request.error} />}
      {answer && <GroundedAnswerView answer={answer} />}
      {answer && "path" in answer && answer.path.length > 1 && (
        <div className="mt-3 rounded-xl bg-lime/20 px-3 py-2 text-xs font-semibold text-moss">
          {answer.path.join(" → ")}
        </div>
      )}
    </div>
  );
}

export function GraphAssistant({ workspaceId, nodes }: { workspaceId: string; nodes: GraphNode[] }) {
  useLocale();
  const [question, setQuestion] = useState("");
  const [conceptA, setConceptA] = useState(nodes[0]?.id ?? "");
  const [conceptB, setConceptB] = useState(nodes[1]?.id ?? "");
  const chat = useMutation({ mutationFn: () => interactionsApi.chat(workspaceId, question) });
  const compare = useMutation({
    mutationFn: () => interactionsApi.compare(workspaceId, conceptA, conceptB),
  });

  function submitChat(event: FormEvent) {
    event.preventDefault();
    chat.mutate();
  }

  return (
    <div className="mt-5 grid gap-5 lg:grid-cols-2">
      <Card className="p-6 shadow-none">
        <p className="flex items-center gap-2 text-sm font-semibold"><MessageCircle size={17} /> {t("Chat with Graph")}</p>
        <form className="mt-4 flex gap-2" onSubmit={submitChat}>
          <Input
            required
            minLength={3}
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder={t("Why do I need HTTP before FastAPI?")}
          />
          <Button type="submit" className="shrink-0 px-4" disabled={chat.isPending}>
            <Sparkles size={16} />
          </Button>
        </form>
        {chat.isPending && <p className="mt-3 text-xs text-ink/45">{t("Searching your graph…")}</p>}
        {chat.error && <InteractionError error={chat.error} />}
        {chat.data && <GroundedAnswerView answer={chat.data} />}
      </Card>

      <Card className="p-6 shadow-none">
        <p className="flex items-center gap-2 text-sm font-semibold"><GitCompareArrows size={17} /> {t("Compare concepts")}</p>
        <div className="mt-4 grid grid-cols-2 gap-2">
          <ConceptSelect value={conceptA} nodes={nodes} onChange={setConceptA} />
          <ConceptSelect value={conceptB} nodes={nodes} onChange={setConceptB} />
        </div>
        <Button
          variant="secondary"
          className="mt-3 h-9"
          disabled={!conceptA || !conceptB || conceptA === conceptB || compare.isPending}
          onClick={() => compare.mutate()}
        > {t("Compare")} </Button>
        {compare.error && <InteractionError error={compare.error} />}
        {compare.data && <CompareAnswerView answer={compare.data} />}
      </Card>
    </div>
  );
}

function ConceptSelect({
  value,
  nodes,
  onChange,
}: {
  value: string;
  nodes: GraphNode[];
  onChange: (value: string) => void;
}) {
  useLocale();
  return (
    <select
      value={value}
      onChange={(event) => onChange(event.target.value)}
      className="h-11 min-w-0 rounded-xl border border-ink/15 bg-white px-3 text-sm outline-none"
    >
      <option value="">{t("Choose concept")}</option>
      {nodes.map((node) => <option key={node.id} value={node.id}>{node.name}</option>)}
    </select>
  );
}

function GroundedAnswerView({ answer }: { answer: GroundedAnswer }) {
  useLocale();
  return (
    <div className="mt-4 space-y-3 text-sm leading-6">
      {answer.source_backed_answer && (
        <div className="rounded-xl bg-moss/5 p-3">
          <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-moss">
            <BookOpen size={14} /> {t("From your sources")} </p>
          <p className="mt-1 whitespace-pre-wrap text-ink/70">{answer.source_backed_answer}</p>
        </div>
      )}
      {answer.additional_explanation && (
        <div className="rounded-xl bg-purple-50 p-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-purple-800">{t("Additional AI explanation")}</p>
          <p className="mt-1 whitespace-pre-wrap text-ink/70">{answer.additional_explanation}</p>
        </div>
      )}
      <Citations citations={answer.citations} />
    </div>
  );
}

function CompareAnswerView({ answer }: { answer: CompareAnswer }) {
  useLocale();
  const sections = [
    [t("Similarities"), answer.similarities],
    [t("Differences"), answer.differences],
    [`${t("When to use")} ${answer.concept_a}`, answer.when_to_use_a],
    [`${t("When to use")} ${answer.concept_b}`, answer.when_to_use_b],
    [t("Examples"), answer.examples],
  ] as const;
  return (
    <div className="mt-4 space-y-3 text-sm">
      {sections.map(([title, items]) => (
        <div key={title}>
          <p className="font-semibold">{title}</p>
          <ul className="mt-1 list-disc space-y-1 pl-5 text-xs leading-5 text-ink/60">
            {items.map((item) => <li key={item}>{item}</li>)}
          </ul>
        </div>
      ))}
      <Citations citations={answer.citations} />
    </div>
  );
}

function Citations({ citations }: { citations: Citation[] }) {
  useLocale();
  const [openIndex, setOpenIndex] = useState<number>();
  if (!citations.length) return null;
  return (
    <div className="flex flex-wrap gap-2">
      {citations.map((citation) => (
        <div key={citation.index}>
          <button
            onClick={() => setOpenIndex(openIndex === citation.index ? undefined : citation.index)}
            className="rounded-full bg-ink/5 px-2.5 py-1 text-xs font-semibold text-moss hover:bg-lime/30"
          >
            [{citation.index}] {citation.source_title}
          </button>
          {openIndex === citation.index && (
            <div className="mt-2 rounded-xl border border-ink/10 bg-white p-3 text-xs leading-5 text-ink/60">
              {citation.heading_path && <p className="mb-1 font-semibold text-ink">{citation.heading_path}</p>}
              {citation.excerpt}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function InteractionError({ error }: { error: Error }) {
  useLocale();
  return (
    <p className="mt-3 text-xs text-red-700">
      {t(error instanceof ApiError ? error.message : "The AI interaction failed.")}
    </p>
  );
}
