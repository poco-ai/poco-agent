"use client";

import * as React from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { cn } from "@/lib/utils";
import { useT } from "@/lib/i18n/client";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { playTaskCompleteSound } from "@/lib/utils/sound";
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

export function UserInputRequestCard({
  request,
  isSubmitting = false,
  onSubmit,
}: UserInputRequestCardProps) {
  const { t } = useT("translation");
  const questions = (request.tool_input?.questions ||
    []) as UserInputQuestion[];

  const [questionState, setQuestionState] = React.useState<
    Record<string, QuestionState>
  >(() =>
    Object.fromEntries(
      questions.map((q) => [
        q.question,
        { selected: [], otherText: "", otherSelected: false },
      ]),
    ),
  );

  const [secondsLeft, setSecondsLeft] = React.useState<number | null>(null);
  const [currentIndex, setCurrentIndex] = React.useState(0);

  const currentQuestion = questions[currentIndex];

  const goToPrevious = () => {
    setCurrentIndex((prev) => Math.max(0, prev - 1));
  };

  const goToNext = () => {
    setCurrentIndex((prev) => Math.min(questions.length - 1, prev + 1));
  };

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

  const buildAnswers = (): Record<string, string> | null => {
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
  };

  const handleSubmit = async () => {
    const answers = buildAnswers();
    if (!answers) {
      toast.error(t("chat.askUserRequired", "请回答所有问题后再提交"));
      return;
    }
    try {
      await onSubmit(answers);
      toast.success(t("chat.askUserSubmitted", "已提交答案"));
      playTaskCompleteSound();
    } catch (error) {
      console.error("Submit AskUserQuestion failed:", error);
      toast.error(t("chat.askUserFailed", "提交失败，请重试"));
    }
  };

  if (questions.length === 0) {
    return null;
  }

  // Auto-close when timeout
  if (secondsLeft === 0) {
    return null;
  }

  return (
    <div className="border border-border rounded-lg bg-card/60 p-4 space-y-4">
      <div className="flex items-center justify-between">
        <div className="text-sm font-medium text-foreground">
          {currentQuestion?.header}
        </div>
        {secondsLeft !== null && (
          <div
            className={cn(
              "text-xs",
              secondsLeft <= 10 ? "text-destructive" : "text-muted-foreground",
            )}
          >
            {t("chat.askUserTimeout", "剩余 {{seconds}} 秒", {
              seconds: secondsLeft,
            })}
          </div>
        )}
      </div>

      <div className="space-y-4">
        {currentQuestion && (
          <div key={currentQuestion.question} className="space-y-4">
            <div className="text-sm text-muted-foreground">
              {currentQuestion.question}
            </div>

            {currentQuestion.multiSelect ? (
              <div className="space-y-2">
                {currentQuestion.options.map((opt) => {
                  const questionKey = currentQuestion.question;
                  const selected = questionState[questionKey]?.selected || [];
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
                        className="mt-0.5"
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

                {/* Other option - clickable checkbox with conditional input */}
                <label className="flex items-start gap-2 text-sm cursor-pointer">
                  <Checkbox
                    checked={isOtherSelected(currentQuestion)}
                    onCheckedChange={(checked) =>
                      toggleOtherSelected(currentQuestion.question, !!checked)
                    }
                    className="mt-0.5"
                  />
                  <div className="flex-1">
                    <div className="text-foreground">
                      {t("chat.askUserOtherOption", "其他")}
                    </div>
                    {isOtherSelected(currentQuestion) && (
                      <Input
                        value={
                          questionState[currentQuestion.question]?.otherText ||
                          ""
                        }
                        onChange={(e) =>
                          setOtherText(currentQuestion.question, e.target.value)
                        }
                        placeholder={t(
                          "chat.askUserOtherPlaceholder",
                          "请输入具体内容",
                        )}
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
                  isOtherSelected(currentQuestion)
                    ? "other"
                    : questionState[currentQuestion.question]?.selected[0] || ""
                }
                onValueChange={(value) => {
                  if (value === "other") {
                    toggleOtherSelected(currentQuestion.question, true);
                    setSelected(currentQuestion.question, []);
                  } else {
                    setSelected(currentQuestion.question, [value]);
                    toggleOtherSelected(currentQuestion.question, false);
                  }
                }}
              >
                {currentQuestion.options.map((opt) => (
                  <label
                    key={opt.label}
                    className="flex items-start gap-2 text-sm cursor-pointer"
                  >
                    <RadioGroupItem value={opt.label} className="mt-0.5" />
                    <div className="flex-1">
                      <div className="text-foreground">{opt.label}</div>
                      <div className="text-xs text-muted-foreground">
                        {opt.description}
                      </div>
                    </div>
                  </label>
                ))}

                {/* Other option - clickable radio with conditional input */}
                <label className="flex items-start gap-2 text-sm cursor-pointer">
                  <RadioGroupItem value="other" className="mt-0.5" />
                  <div className="flex-1">
                    <div className="text-foreground">
                      {t("chat.askUserOtherOption", "其他")}
                    </div>
                    {isOtherSelected(currentQuestion) && (
                      <Input
                        value={
                          questionState[currentQuestion.question]?.otherText ||
                          ""
                        }
                        onChange={(e) =>
                          setOtherText(currentQuestion.question, e.target.value)
                        }
                        placeholder={t(
                          "chat.askUserOtherPlaceholder",
                          "请输入具体内容",
                        )}
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
        )}
      </div>

      {questions.length === 1 ? (
        <div className="flex justify-end">
          <Button
            size="sm"
            onClick={handleSubmit}
            disabled={isSubmitting || !allAnswered}
          >
            {t("chat.askUserSubmit", "提交")}
          </Button>
        </div>
      ) : (
        <div className="flex items-center justify-between">
          <Button
            variant="outline"
            size="sm"
            onClick={goToPrevious}
            disabled={currentIndex === 0}
          >
            <ChevronLeft className="h-4 w-4" />
            {t("chat.askUserPrevious", "上一题")}
          </Button>

          <div className="flex items-center gap-1">
            {questions.map((_, idx) => (
              <button
                key={idx}
                onClick={() => setCurrentIndex(idx)}
                className={cn(
                  "h-2 rounded-full transition-all",
                  idx === currentIndex
                    ? "w-6 bg-primary"
                    : "w-2 bg-muted-foreground/30 hover:bg-muted-foreground/50",
                )}
                aria-label={t("chat.askUserGoTo", "第 {{index}} 题", {
                  index: idx + 1,
                })}
              />
            ))}
          </div>

          {currentIndex === questions.length - 1 ? (
            <Button
              size="sm"
              onClick={handleSubmit}
              disabled={isSubmitting || !allAnswered}
            >
              {t("chat.askUserSubmit", "提交")}
            </Button>
          ) : (
            <Button variant="outline" size="sm" onClick={goToNext}>
              {t("chat.askUserNext", "下一题")}
              <ChevronRight className="h-4 w-4" />
            </Button>
          )}
        </div>
      )}
    </div>
  );
}
