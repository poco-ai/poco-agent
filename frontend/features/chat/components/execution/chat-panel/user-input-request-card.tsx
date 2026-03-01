"use client";

import * as React from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Stepper, Step } from "@/components/ui/stepper";
import { cn } from "@/lib/utils";
import { useT } from "@/lib/i18n/client";
import { playCompletionSound } from "@/lib/utils/sound";
import type {
  UserInputQuestion,
  UserInputRequest,
} from "@/features/chat/types";

interface UserInputRequestCardProps {
  request: UserInputRequest;
  isSubmitting?: boolean;
  onSubmit: (answers: Record<string, string>) => Promise<void>;
}

interface QuestionState {
  selected: string[];
  otherText: string;
  otherSelected: boolean;
}

type CompletionState = "idle" | "submitting" | "success" | "error";

const MAX_TOOL_INPUT_PARSE_DEPTH = 2;

function parseToolInput(rawInput: unknown): Record<string, unknown> {
  let current: unknown = rawInput;
  for (let i = 0; i < MAX_TOOL_INPUT_PARSE_DEPTH; i += 1) {
    if (typeof current === "string") {
      try {
        current = JSON.parse(current);
        continue;
      } catch {
        return {};
      }
    }
    break;
  }
  if (current && typeof current === "object") {
    return current as Record<string, unknown>;
  }
  return {};
}

function normalizeQuestions(rawQuestions: unknown[]): UserInputQuestion[] {
  return rawQuestions
    .map((item) => {
      if (!item || typeof item !== "object") return null;
      const raw = item as Record<string, unknown>;
      const rawOptions =
        (raw.options as unknown[] | undefined) ??
        (raw.choices as unknown[] | undefined) ??
        [];
      const options = Array.isArray(rawOptions)
        ? rawOptions
            .map((opt) => {
              if (!opt || typeof opt !== "object") return null;
              const option = opt as Record<string, unknown>;
              const label =
                typeof option.label === "string"
                  ? option.label
                  : typeof option.value === "string"
                    ? option.value
                    : "";
              if (!label) return null;
              return {
                label,
                description:
                  typeof option.description === "string"
                    ? option.description
                    : "",
              };
            })
            .filter((opt): opt is UserInputQuestion["options"][number] => !!opt)
        : [];

      const question =
        typeof raw.question === "string"
          ? raw.question
          : typeof raw.label === "string"
            ? raw.label
            : "";
      if (!question) return null;

      const header =
        typeof raw.header === "string"
          ? raw.header
          : typeof raw.title === "string"
            ? raw.title
            : "";
      const multiSelect = Boolean(
        raw.multiSelect ?? raw.multi_select ?? raw.multiselect,
      );

      return {
        question,
        header,
        options,
        multiSelect,
      } satisfies UserInputQuestion;
    })
    .filter((q): q is UserInputQuestion => Boolean(q));
}

function resolveQuestions(
  toolInput: Record<string, unknown>,
): UserInputQuestion[] {
  const candidates: unknown[] = [
    toolInput,
    (toolInput.input as Record<string, unknown> | undefined) ?? null,
    (toolInput.args as Record<string, unknown> | undefined) ?? null,
    (toolInput.payload as Record<string, unknown> | undefined) ?? null,
    (toolInput.data as Record<string, unknown> | undefined) ?? null,
  ];

  for (const candidate of candidates) {
    if (!candidate) continue;
    if (Array.isArray(candidate)) {
      return normalizeQuestions(candidate);
    }
    if (typeof candidate === "string") {
      const parsed = parseToolInput(candidate);
      const parsedQuestions = resolveQuestions(parsed);
      if (parsedQuestions.length > 0) return parsedQuestions;
      continue;
    }
    if (typeof candidate === "object") {
      const rawQuestions = (candidate as Record<string, unknown>).questions;
      if (Array.isArray(rawQuestions)) {
        return normalizeQuestions(rawQuestions);
      }
      if (typeof rawQuestions === "string") {
        try {
          const parsed = JSON.parse(rawQuestions);
          if (Array.isArray(parsed)) {
            return normalizeQuestions(parsed);
          }
          if (
            parsed &&
            typeof parsed === "object" &&
            Array.isArray((parsed as Record<string, unknown>).questions)
          ) {
            return normalizeQuestions(
              (parsed as Record<string, unknown>).questions as unknown[],
            );
          }
        } catch {
          // ignore malformed payloads
        }
      }
    }
  }
  return [];
}

function CompletionBar({ steps }: { steps: number }) {
  return (
    <div className="w-full">
      <div className="rounded-full border border-border/60 bg-card/70 px-6 py-4 shadow-sm">
        <div className="flex items-center gap-3">
          {Array.from({ length: steps }).map((_, index) => (
            <React.Fragment key={index}>
              <div className="flex size-7 items-center justify-center rounded-full bg-primary text-primary-foreground">
                <CheckIcon className="size-3.5" />
              </div>
              {index < steps - 1 && (
                <div className="h-0.5 flex-1 rounded bg-primary" />
              )}
            </React.Fragment>
          ))}
        </div>
      </div>
    </div>
  );
}

function CheckIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      {...props}
      fill="none"
      stroke="currentColor"
      strokeWidth={2.5}
      viewBox="0 0 24 24"
    >
      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
    </svg>
  );
}

export function UserInputRequestCard({
  request,
  isSubmitting = false,
  onSubmit,
}: UserInputRequestCardProps) {
  const { t } = useT("translation");
  const toolInput = React.useMemo(
    () => parseToolInput(request.tool_input),
    [request.tool_input],
  );

  const questions = React.useMemo(
    () => resolveQuestions(toolInput),
    [toolInput],
  );

  const buildInitialQuestionState = React.useCallback(
    () =>
      Object.fromEntries(
        questions.map((q) => [
          q.question,
          { selected: [], otherText: "", otherSelected: false },
        ]),
      ) as Record<string, QuestionState>,
    [questions],
  );

  const [questionState, setQuestionState] = React.useState<
    Record<string, QuestionState>
  >(buildInitialQuestionState);

  const [secondsLeft, setSecondsLeft] = React.useState<number | null>(null);
  const [currentIndex, setCurrentIndex] = React.useState(0);
  const [completionState, setCompletionState] =
    React.useState<CompletionState>("idle");
  const [shouldDismiss, setShouldDismiss] = React.useState(false);
  const lastRequestIdRef = React.useRef<string | null>(null);

  React.useEffect(() => {
    if (lastRequestIdRef.current === request.id) return;
    lastRequestIdRef.current = request.id;
    setQuestionState(buildInitialQuestionState());
    setCurrentIndex(0);
    setCompletionState("idle");
    setShouldDismiss(false);
  }, [buildInitialQuestionState, request.id]);

  const currentQuestion = questions[currentIndex];

  const isOtherSelected = (q: UserInputQuestion) =>
    questionState[q.question]?.otherSelected ?? false;

  const isQuestionAnswered = (q: UserInputQuestion) => {
    const state = questionState[q.question];
    if (!state) return false;
    if (state.selected.length > 0) return true;
    return state.otherSelected && state.otherText.trim().length > 0;
  };

  const allAnswered = questions.every(isQuestionAnswered);

  React.useEffect(() => {
    if (!request.expires_at) {
      setSecondsLeft(null);
      return;
    }
    const expiresAt = new Date(request.expires_at).getTime();
    const update = () => {
      const now = Date.now();
      const diff = Math.max(0, Math.ceil((expiresAt - now) / 1000));
      setSecondsLeft(diff);
    };
    update();
    const timer = window.setInterval(update, 1000);
    return () => window.clearInterval(timer);
  }, [request.expires_at]);

  const setSelected = (questionKey: string, values: string[]) => {
    setQuestionState((prev) => ({
      ...prev,
      [questionKey]: { ...prev[questionKey], selected: values },
    }));
  };

  const setOtherText = (questionKey: string, value: string) => {
    setQuestionState((prev) => ({
      ...prev,
      [questionKey]: { ...prev[questionKey], otherText: value },
    }));
  };

  const toggleOtherSelected = (questionKey: string, selected: boolean) => {
    setQuestionState((prev) => ({
      ...prev,
      [questionKey]: {
        ...prev[questionKey],
        otherSelected: selected,
        otherText: selected ? prev[questionKey].otherText : "",
      },
    }));
  };

  const buildAnswers = React.useCallback((): Record<string, string> | null => {
    const result: Record<string, string> = {};
    for (const q of questions) {
      const state = questionState[q.question];
      if (!state) return null;

      const otherText = state.otherSelected ? state.otherText.trim() : "";
      const answer = q.multiSelect
        ? [...state.selected, ...(otherText ? [otherText] : [])].join(", ")
        : otherText || state.selected[0] || "";

      if (!answer) return null;
      result[q.question] = answer;
    }
    return result;
  }, [questionState, questions]);

  const handleSubmit = React.useCallback(async () => {
    const answers = buildAnswers();
    if (!answers) {
      toast.error(t("chat.askUserRequired"));
      return;
    }
    setCompletionState("submitting");
    try {
      await onSubmit(answers);
      toast.success(t("chat.askUserSubmitted"));
      playCompletionSound();
      setCompletionState("success");
    } catch (error) {
      console.error("Submit AskUserQuestion failed:", error);
      toast.error(t("chat.askUserFailed"));
      setCompletionState("error");
    }
  }, [buildAnswers, onSubmit, t]);

  React.useEffect(() => {
    if (completionState !== "success") return;
    const timer = window.setTimeout(() => {
      setShouldDismiss(true);
    }, 1500);
    return () => window.clearTimeout(timer);
  }, [completionState]);

  if (questions.length === 0) {
    return null;
  }

  // Auto-close when timeout
  if (secondsLeft === 0) {
    return null;
  }

  if (shouldDismiss) {
    return null;
  }

  const totalSteps = questions.length;
  const currentStep = currentIndex + 1;
  const showCompletion = completionState !== "idle";
  const currentAnswered = currentQuestion
    ? isQuestionAnswered(currentQuestion)
    : false;
  const isLastStep = currentIndex === totalSteps - 1;
  const nextDisabled =
    isSubmitting || (isLastStep ? !allAnswered : !currentAnswered);

  const showPrev = currentIndex > 0;
  const nextLabel = isLastStep
    ? t("chat.askUserSubmit")
    : t("chat.askUserNext");

  const isCompletionSuccess = showCompletion && completionState !== "error";

  return (
    <div
      className={cn(
        "space-y-4",
        isCompletionSuccess
          ? "border-0 bg-transparent p-0 shadow-none"
          : "border border-border/90 rounded-lg bg-card p-4 shadow-md",
      )}
    >
      {showCompletion ? (
        completionState === "error" ? (
          <div className="flex flex-col items-center gap-2 py-6 text-center">
            <div className="text-sm font-medium text-foreground">
              {t("chat.askUserFailed")}
            </div>
            <div className="text-xs text-muted-foreground">
              {t("chat.askUserCompleteHint")}
            </div>
            <Button size="sm" onClick={handleSubmit} disabled={isSubmitting}>
              {t("chat.askUserRetry")}
            </Button>
          </div>
        ) : (
          <div className="py-4">
            <CompletionBar steps={totalSteps} />
          </div>
        )
      ) : (
        <Stepper
          currentStep={currentStep}
          onStepChange={(step) => setCurrentIndex(step - 1)}
          onFinalStepCompleted={() => void handleSubmit()}
          showFooter={false}
          showCompleteButton
          backButtonText={t("chat.askUserPrevious")}
          nextButtonText={t("chat.askUserNext")}
          completeButtonText={t("chat.askUserSubmit")}
          className="w-full flex-none items-stretch p-0 min-h-0"
          stepCircleContainerClassName="mx-0 max-w-none border-0 bg-transparent shadow-none"
          backButtonProps={{ disabled: isSubmitting }}
          nextButtonProps={{
            disabled: nextDisabled,
          }}
          stepContainerClassName="p-0 px-1 pb-3"
          contentClassName="px-0 pt-4"
        >
          {questions.map((question) => (
            <Step key={question.question} className="px-0">
              <div className="space-y-4">
                <div className="space-y-1">
                  <div className="text-sm font-medium text-foreground">
                    {question.header}
                  </div>
                  <div className="text-sm text-muted-foreground">
                    {question.question}
                  </div>
                </div>

                {question.multiSelect ? (
                  <div className="space-y-2">
                    {question.options.map((opt) => {
                      const questionKey = question.question;
                      const selected =
                        questionState[questionKey]?.selected || [];
                      const checked = selected.includes(opt.label);
                      return (
                        <label
                          key={opt.label}
                          className="flex items-start gap-2 text-sm cursor-pointer"
                        >
                          <Checkbox
                            checked={checked}
                            onCheckedChange={(value) => {
                              const next = value
                                ? [...selected, opt.label]
                                : selected.filter((v) => v !== opt.label);
                              setSelected(questionKey, next);
                            }}
                            className="mt-0.5 size-5 [&_[data-slot=checkbox-indicator]_svg]:size-4"
                          />
                          <div className="flex-1">
                            <div className="text-foreground">{opt.label}</div>
                            <div className="text-xs text-muted-foreground">
                              {opt.description}
                            </div>
                          </div>
                        </label>
                      );
                    })}

                    <label className="flex items-start gap-2 text-sm cursor-pointer">
                      <Checkbox
                        checked={isOtherSelected(question)}
                        onCheckedChange={(checked) =>
                          toggleOtherSelected(question.question, !!checked)
                        }
                        className="mt-0.5 size-5 [&_[data-slot=checkbox-indicator]_svg]:size-4"
                      />
                      <div className="flex-1">
                        <div className="text-foreground">
                          {t("chat.askUserOtherOption")}
                        </div>
                        {isOtherSelected(question) && (
                          <Input
                            value={
                              questionState[question.question]?.otherText || ""
                            }
                            onChange={(e) =>
                              setOtherText(question.question, e.target.value)
                            }
                            placeholder={t("chat.askUserOtherPlaceholder")}
                            className="mt-2"
                            onClick={(e) => e.stopPropagation()}
                            autoFocus
                          />
                        )}
                      </div>
                    </label>
                  </div>
                ) : (
                  <RadioGroup
                    className="space-y-2"
                    value={
                      isOtherSelected(question)
                        ? "other"
                        : questionState[question.question]?.selected[0] || ""
                    }
                    onValueChange={(value) => {
                      if (value === "other") {
                        toggleOtherSelected(question.question, true);
                        setSelected(question.question, []);
                      } else {
                        setSelected(question.question, [value]);
                        toggleOtherSelected(question.question, false);
                      }
                    }}
                  >
                    {question.options.map((opt) => (
                      <label
                        key={opt.label}
                        className="flex items-start gap-2 text-sm cursor-pointer"
                      >
                        <RadioGroupItem
                          value={opt.label}
                          className="mt-0.5 size-5 [&_[data-slot=radio-group-indicator]_svg]:size-2.5"
                        />
                        <div className="flex-1">
                          <div className="text-foreground">{opt.label}</div>
                          <div className="text-xs text-muted-foreground">
                            {opt.description}
                          </div>
                        </div>
                      </label>
                    ))}

                    <label className="flex items-start gap-2 text-sm cursor-pointer">
                      <RadioGroupItem
                        value="other"
                        className="mt-0.5 size-5 [&_[data-slot=radio-group-indicator]_svg]:size-2.5"
                      />
                      <div className="flex-1">
                        <div className="text-foreground">
                          {t("chat.askUserOtherOption")}
                        </div>
                        {isOtherSelected(question) && (
                          <Input
                            value={
                              questionState[question.question]?.otherText || ""
                            }
                            onChange={(e) =>
                              setOtherText(question.question, e.target.value)
                            }
                            placeholder={t("chat.askUserOtherPlaceholder")}
                            className="mt-2"
                            onClick={(e) => e.stopPropagation()}
                            autoFocus
                          />
                        )}
                      </div>
                    </label>
                  </RadioGroup>
                )}
              </div>
            </Step>
          ))}
        </Stepper>
      )}

      {!showCompletion && (
        <div className="pt-5">
          <div className="grid grid-cols-3 gap-2">
            <div className="flex items-end justify-self-start">
              {showPrev ? (
                <button
                  type="button"
                  onClick={() => setCurrentIndex((idx) => Math.max(0, idx - 1))}
                  disabled={isSubmitting}
                  className="rounded px-2 py-1 text-sm text-muted-foreground transition hover:text-foreground disabled:pointer-events-none disabled:opacity-50"
                >
                  {t("chat.askUserPrevious")}
                </button>
              ) : (
                <span />
              )}
            </div>
            <div
              className={cn(
                "flex items-end justify-center text-center text-xs",
                secondsLeft !== null && secondsLeft <= 10
                  ? "text-destructive"
                  : "text-muted-foreground",
              )}
            >
              {secondsLeft !== null
                ? t("chat.askUserTimeout", { seconds: secondsLeft })
                : ""}
            </div>
            <div className="flex items-end justify-self-end">
              <button
                type="button"
                onClick={() => {
                  if (isLastStep) {
                    void handleSubmit();
                  } else {
                    setCurrentIndex((idx) => Math.min(totalSteps - 1, idx + 1));
                  }
                }}
                disabled={nextDisabled}
                className="flex items-center justify-center rounded-full bg-primary px-3.5 py-1.5 text-sm font-medium text-primary-foreground transition hover:bg-primary/90 active:bg-primary/80 disabled:pointer-events-none disabled:opacity-50"
              >
                {nextLabel}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
