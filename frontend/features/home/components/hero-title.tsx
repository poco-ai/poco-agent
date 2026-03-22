"use client";

import * as React from "react";
import { motion } from "motion/react";
import {
  BarChart3,
  Code,
  Github,
  Map,
  Network,
  Presentation,
  Search,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useT } from "@/lib/i18n/client";
import { usePrefersReducedMotion } from "@/hooks/use-prefers-reduced-motion";
import { RotatingText } from "./rotating-text";

const ROTATION_INTERVAL_MS = 1800;

const ROTATING_WORD_ICONS: LucideIcon[] = [
  Presentation, // 做 PPT
  Search, // 搜索资料
  Network, // 做思维导图
  Github, // 分析 Github 仓库
  BarChart3, // 分析数据
  Map, // 旅行规划
  Code, // 编写程序
];

function normalizeWords(value: unknown): string[] {
  if (Array.isArray(value)) {
    return value.filter((v): v is string => typeof v === "string");
  }
  return [];
}

const DEFAULT_ROTATING_WORDS = [
  "做 PPT",
  "搜索资料",
  "做思维导图",
  "分析 Github 仓库",
  "分析数据",
  "旅行规划",
  "编写程序",
];

export function HeroTitle() {
  const { t } = useT("translation");
  const prefersReducedMotion = usePrefersReducedMotion();
  const [isHovered, setIsHovered] = React.useState(false);

  const rotatingWords = React.useMemo(() => {
    const words = normalizeWords(
      t("hero.rotatingWords", { returnObjects: true }) as unknown,
    );
    return words.length > 0 ? words : DEFAULT_ROTATING_WORDS;
  }, [t]);

  const longestWord = React.useMemo(
    () =>
      rotatingWords.reduce((a, b) => (a.length >= b.length ? a : b), "") ||
      "做 PPT",
    [rotatingWords],
  );

  const [index, setIndex] = React.useState(0);
  const currentWord = rotatingWords[index % rotatingWords.length] ?? "";
  const CurrentIcon =
    ROTATING_WORD_ICONS[index % ROTATING_WORD_ICONS.length] ?? Presentation;

  React.useEffect(() => {
    if (!isHovered || prefersReducedMotion || rotatingWords.length <= 1) return;
    const id = setInterval(() => {
      setIndex((i) => (i + 1) % rotatingWords.length);
    }, ROTATION_INTERVAL_MS);
    return () => clearInterval(id);
  }, [isHovered, prefersReducedMotion, rotatingWords.length]);

  const staticTitle = t("hero.title");

  if (prefersReducedMotion) {
    return (
      <>
        {staticTitle} {currentWord}
      </>
    );
  }

  return (
    <span
      className="inline-flex cursor-default items-baseline"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <motion.span
        animate={{ x: isHovered ? -10 : 0 }}
        transition={{ duration: 0.22, ease: [0.32, 0.72, 0, 1] }}
        className="inline-block shrink-0"
      >
        {staticTitle}
      </motion.span>
      <motion.span
        initial={{ maxWidth: 0, opacity: 0, marginLeft: 0 }}
        animate={{
          maxWidth: isHovered ? 280 : 0,
          opacity: isHovered ? 1 : 0,
          marginLeft: isHovered ? 8 : 0,
        }}
        transition={{ duration: 0.22, ease: [0.32, 0.72, 0, 1] }}
        className="relative inline-block overflow-hidden align-middle"
      >
        <span
          className="invisible inline-flex h-[2.25rem] items-center whitespace-nowrap rounded-lg px-2 py-0.5 font-medium"
          style={{ fontSize: "1rem" }}
          aria-hidden="true"
        >
          <span className="w-4 shrink-0" />
          <span className="ml-2">{longestWord}</span>
        </span>
        {isHovered && (
          <span
            className="absolute left-0 top-0 flex h-[2.25rem] shrink-0 items-center gap-2 whitespace-nowrap rounded-lg px-2 py-0.5"
            style={{
              backgroundColor: "var(--primary)",
              color: "var(--primary-foreground)",
            }}
          >
            <motion.span
              key={index}
              initial={{ scale: 0, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{
                type: "spring",
                stiffness: 400,
                damping: 25,
              }}
              className="flex shrink-0"
            >
              <CurrentIcon className="size-4" aria-hidden />
            </motion.span>
            <RotatingText
              text={currentWord}
              staggerDuration={0.02}
              staggerFrom="first"
              className="font-medium text-base shrink-0"
              charClassName="leading-none"
            />
          </span>
        )}
      </motion.span>
    </span>
  );
}
