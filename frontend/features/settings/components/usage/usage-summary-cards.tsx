"use client";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { CountUp } from "@/components/ui/count-up";
import { useT } from "@/lib/i18n/client";
import {
  formatCompactNumber,
  formatCurrency,
  formatNumber,
} from "@/features/settings/lib/usage-analytics";
import type {
  UsageAnalyticsMetricSummary,
  UsageAnalyticsSummary,
} from "@/features/settings/types";

interface UsageSummaryCardsProps {
  summary: UsageAnalyticsSummary;
  locale: string;
  monthLabel: string;
  dayLabel: string;
}

interface UsageMetricCardProps {
  title: string;
  description: string;
  total: number;
  metric: UsageAnalyticsMetricSummary;
  locale: string;
}

function UsageMetricValue({
  value,
  locale,
  className,
}: {
  value: number;
  locale: string;
  className?: string;
}) {
  const exactValue = formatNumber(value, locale);
  const formatDisplay = (n: number) =>
    Math.abs(n) < 1_000
      ? formatNumber(Math.round(n), locale)
      : formatCompactNumber(n, locale);

  if (Math.abs(value) < 1_000) {
    return (
      <CountUp
        value={value}
        format={(n) => formatNumber(Math.round(n), locale)}
        className={className}
      />
    );
  }

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <CountUp value={value} format={formatDisplay} className={className} />
      </TooltipTrigger>
      <TooltipContent side="top" sideOffset={8}>
        {exactValue}
      </TooltipContent>
    </Tooltip>
  );
}

function UsageMetricCard({
  title,
  description,
  total,
  metric,
  locale,
}: UsageMetricCardProps) {
  const { t } = useT("translation");
  const metricItems = [
    {
      label: t("settings.usageTab.inputTokens"),
      value: metric.input_tokens,
    },
    {
      label: t("settings.usageTab.outputTokens"),
      value: metric.output_tokens,
    },
    {
      label: t("settings.usageTab.cacheWriteTokens"),
      value: metric.cache_creation_input_tokens,
    },
    {
      label: t("settings.usageTab.cacheReadTokens"),
      value: metric.cache_read_input_tokens,
    },
  ];

  return (
    <Card className="h-72 border-border/60 bg-card/80 shadow-sm">
      <CardHeader className="px-5 pt-5 pb-0">
        <div className="flex min-w-0 items-baseline gap-2">
          <CardTitle className="shrink-0 text-base font-semibold">
            {title}
          </CardTitle>
          <CardDescription className="min-w-0 truncate text-xs leading-none">
            {description}
          </CardDescription>
        </div>
      </CardHeader>
      <CardContent className="flex flex-1 flex-col px-5 pb-5 pt-2">
        <UsageMetricValue
          value={total}
          locale={locale}
          className="inline-block text-4xl font-semibold leading-none tracking-tight tabular-nums"
        />
        <div className="mt-4 flex flex-1 flex-col text-sm text-muted-foreground">
          <div className="space-y-2">
            {metricItems.map((item) => (
              <div
                key={item.label}
                className="flex items-center justify-between gap-4"
              >
                <span>{item.label}</span>
                <UsageMetricValue
                  value={item.value}
                  locale={locale}
                  className="inline-block text-base font-medium text-foreground tabular-nums"
                />
              </div>
            ))}
          </div>
          <div className="mt-auto flex items-center justify-between gap-4 border-t border-dashed border-border/70 pt-3">
            <span>{t("settings.usageTab.cost")}</span>
            <CountUp
              value={metric.total_cost_usd}
              format={(n) => formatCurrency(n, locale)}
              className="text-base font-medium text-foreground tabular-nums"
            />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export function UsageSummaryCards({
  summary,
  locale,
  monthLabel,
  dayLabel,
}: UsageSummaryCardsProps) {
  const { t } = useT("translation");

  return (
    <div className="grid gap-2.5 lg:grid-cols-3">
      <UsageMetricCard
        title={t("settings.usageTab.monthSummary")}
        description={monthLabel}
        total={summary.month.total_tokens}
        metric={summary.month}
        locale={locale}
      />
      <UsageMetricCard
        title={t("settings.usageTab.daySummary")}
        description={dayLabel}
        total={summary.day.total_tokens}
        metric={summary.day}
        locale={locale}
      />
      <UsageMetricCard
        title={t("settings.usageTab.allTimeSummary")}
        description={t("settings.usageTab.allTimeDescription")}
        total={summary.all_time.total_tokens}
        metric={summary.all_time}
        locale={locale}
      />
    </div>
  );
}
