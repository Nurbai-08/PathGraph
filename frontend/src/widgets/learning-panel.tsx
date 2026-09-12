import { t, useLocale } from "../shared/lib/i18n";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, ArrowRight, Brain, CheckCircle2, Route } from "lucide-react";
import { useState, type FormEvent } from "react";

import { learningApi } from "../entities/learning/api";
import { ApiError } from "../shared/api/client";
import type { QuizQuestion } from "../shared/types/learning";
import { Button } from "../shared/ui/button";
import { Card } from "../shared/ui/card";
import { ErrorMessage } from "../shared/ui/status";
import { Input } from "../shared/ui/input";
import { AIRequired } from "../features/ai-settings/ai-required";
import { StudyConcept } from "../features/learning/study-concept";

export function LearningPanel({ workspaceId }: { workspaceId: string }) {
  useLocale();
  const [goal, setGoal] = useState("");
  const queryClient = useQueryClient();
  const paths = useQuery({
    queryKey: ["learning-paths", workspaceId],
    queryFn: () => learningApi.listPaths(workspaceId),
  });
  const activePath = paths.data?.[0];
  const next = useQuery({
    queryKey: ["next-concept", activePath?.id],
    queryFn: () => learningApi.next(activePath!.id),
    enabled: Boolean(activePath),
  });
  const create = useMutation({
    mutationFn: () => learningApi.createPath(workspaceId, goal),
    onSuccess: async () => {
      setGoal("");
      await queryClient.invalidateQueries({ queryKey: ["learning-paths", workspaceId] });
    },
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    create.mutate();
  }

  return (
    <section className="mt-12">
      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-moss">{t("Learning engine")}</p>
      <div className="mt-2 flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <h2 className="text-2xl font-semibold">{t("Your Learning Path")}</h2>
          <p className="mt-1 text-sm text-ink/50">{t("Prerequisites first, progress at your pace.")}</p>
        </div>
      </div>

      {!activePath && !paths.isLoading && (
        <Card className="mt-5 p-6 sm:p-8">
          <div className="flex items-center gap-3">
            <Route className="text-moss" size={24} />
            <h3 className="font-semibold">{t("What do you want to learn?")}</h3>
          </div>
          <form className="mt-5 flex flex-col gap-3 sm:flex-row" onSubmit={submit}>
            <Input
              required
              minLength={3}
              value={goal}
              onChange={(event) => setGoal(event.target.value)}
              placeholder={t("I want to learn Python backend")}
            />
            <Button type="submit" className="shrink-0" disabled={create.isPending}>
              {create.isPending ? t("Building…") : t("Build path")} <ArrowRight size={16} />
            </Button>
          </form>
          {create.error && (
            <div className="mt-4">
              <ErrorMessage
                message={create.error instanceof ApiError ? create.error.message : t("Could not build path.")}
              />
            </div>
          )}
        </Card>
      )}

      {activePath && (
        <div className="mt-5 grid gap-5 lg:grid-cols-[0.8fr_1.2fr]">
          <Card className="p-6 shadow-none">
            <p className="text-xs font-semibold uppercase tracking-[0.15em] text-ink/40">{t("Active goal")}</p>
            <h3 className="mt-2 text-xl font-semibold">{activePath.title}</h3>
            <div className="mt-5 space-y-3">
              {activePath.items.map((item) => (
                <div key={item.id} className="flex items-center gap-3 text-sm">
                  <span className={`grid h-6 w-6 place-items-center rounded-full text-xs ${
                    item.concept.mastery >= 85 ? "bg-moss text-white" : "bg-ink/5 text-ink/40"
                  }`}>
                    {item.concept.mastery >= 85 ? <CheckCircle2 size={14} /> : item.position + 1}
                  </span>
                  <span className={item.concept.mastery >= 85 ? "text-ink/40 line-through" : "font-medium"}>
                    {item.concept.name}
                  </span>
                </div>
              ))}
            </div>
          </Card>

          <Card className="p-6 shadow-none">
            <p className="text-xs font-semibold uppercase tracking-[0.15em] text-moss">{t("Recommended next")}</p>
            <h3 className="mt-2 text-2xl font-semibold">{next.isLoading ? t("Loading…") : next.data?.concept?.name ?? (next.isError ? t("Request failed.") : t("Path complete"))}</h3>
            {next.error && <ErrorMessage message={next.error.message} />}
            {next.data?.concept && (
              <p className="mt-2 text-sm text-ink/50">
                {t(next.data.concept.type)} · {t("Mastery")} {next.data.concept.mastery}%
              </p>
            )}
            {next.data?.gaps && next.data.gaps.length > 0 && (
              <div className="mt-5 rounded-2xl bg-orange-50 p-4">
                <p className="flex items-center gap-2 text-sm font-semibold text-orange-900">
                  <AlertTriangle size={16} /> {t("Knowledge gaps")} </p>
                <ul className="mt-2 space-y-1 text-xs leading-5 text-orange-800/80">
                  {next.data.gaps.map((gap) => <li key={`${gap.concept.id}-${gap.blocked_concept.id}`}>{t("Review first")}: {gap.concept.name} → {gap.blocked_concept.name}</li>)}
                </ul>
              </div>
            )}
            {next.data?.concept && <>
              <StudyConcept key={next.data.concept.id} conceptId={next.data.concept.id} />
              <AIRequired><Quiz key={next.data.concept.id} conceptId={next.data.concept.id} pathId={activePath.id} /></AIRequired>
            </>}
          </Card>
        </div>
      )}
    </section>
  );
}

function Quiz({ conceptId, pathId }: { conceptId: string; pathId: string }) {
  useLocale();
  const [questionIndex, setQuestionIndex] = useState(0);
  const questions = useQuery({
    queryKey: ["quiz", conceptId],
    queryFn: () => learningApi.listQuiz(conceptId),
  });
  const queryClient = useQueryClient();
  const generate = useMutation({
    mutationFn: () => learningApi.generateQuiz(conceptId),
    onSuccess: (data) => { setQuestionIndex(0); queryClient.setQueryData(["quiz", conceptId], data); },
  });
  const question = questions.data?.[questionIndex];
  if (question) {
    return <>
      <p className="mt-3 text-sm">{t("Question")} {questionIndex + 1} / {questions.data?.length}</p>
      <QuizQuestionForm key={question.id} question={question} pathId={pathId} />
      {questions.data && questionIndex + 1 < questions.data.length && (
        <Button variant="secondary" className="mt-3" onClick={() => setQuestionIndex(questionIndex + 1)}>{t("Next question")}</Button>
      )}
    </>;
  }
  return (
    <div className="mt-5 border-t border-ink/10 pt-5">
      <Button variant="secondary" onClick={() => generate.mutate()} disabled={generate.isPending}>
        <Brain size={16} /> {generate.isPending ? t("Generating…") : t("Generate quiz")}
      </Button>
      {questions.error && <ErrorMessage message={questions.error.message} />}
      {generate.error && (
        <p className="mt-2 text-xs text-red-700">
          {t(generate.error instanceof ApiError ? generate.error.message : "Quiz generation failed.")}
        </p>
      )}
    </div>
  );
}

function QuizQuestionForm({ question, pathId }: { question: QuizQuestion; pathId: string }) {
  useLocale();
  const [answer, setAnswer] = useState("");
  const queryClient = useQueryClient();
  const submit = useMutation({
    mutationFn: () => learningApi.answer(question.id, answer),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["next-concept", pathId] }),
        queryClient.invalidateQueries({ queryKey: ["learning-paths"] }),
        queryClient.invalidateQueries({ queryKey: ["graph"] }),
        queryClient.invalidateQueries({ queryKey: ["concept"] }),
      ]);
    },
  });
  return (
    <div className="mt-5 border-t border-ink/10 pt-5">
      <p className="text-sm font-semibold">{t("Quick check")}</p>
      <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-ink/65">{question.question}</p>
      <div className="mt-3 space-y-2">
        {question.choices ? question.choices.map((choice) => (
          <label key={choice} className="flex cursor-pointer items-center gap-2 rounded-xl border border-ink/10 px-3 py-2 text-sm">
            <input type="radio" name={question.id} value={choice} onChange={() => setAnswer(choice)} /> {choice}
          </label>
        )) : (
          <Input value={answer} onChange={(event) => setAnswer(event.target.value)} placeholder={t("Your answer")} />
        )}
      </div>
      {!submit.data && (
        <Button className="mt-3 h-9" onClick={() => submit.mutate()} disabled={!answer || submit.isPending}> {t("Check answer")} </Button>
      )}
      {submit.error && <ErrorMessage message={submit.error.message} />}
      {submit.data && (
        <div className={`mt-3 rounded-xl p-3 text-sm ${submit.data.correct ? "bg-green-50 text-green-800" : "bg-red-50 text-red-800"}`}>
          <p className="flex items-center gap-2 font-semibold">
            {submit.data.correct && <CheckCircle2 size={15} />}
            {submit.data.correct ? t("Correct") : `${t("Answer")}: ${submit.data.correct_answer}`}
          </p>
          <p className="mt-1 whitespace-pre-wrap text-xs leading-5">{submit.data.explanation}</p>
          <p className="mt-2 text-xs font-semibold">{t("Mastery")}: {submit.data.mastery_before}% → {submit.data.mastery_after}%</p>
        </div>
      )}
    </div>
  );
}
