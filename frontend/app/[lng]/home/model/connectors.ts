import * as React from "react";
import {
  Chrome,
  Mail,
  Calendar,
  HardDrive,
  Github,
  Slack,
  Database,
  Command,
  Search,
} from "lucide-react";

export const ConnectorIcons = {
  chrome: Chrome,
  gmail: Mail,
  calendar: Calendar,
  drive: HardDrive,
  outlook: Mail,
  github: Github,
  slack: Slack,
  notion: Database,
  zapier: Command,
  search: Search,
};

export type ConnectorType = "app" | "mcp" | "skill" | "api";

export interface Connector {
  id: string;
  type: ConnectorType;
  title: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  author: string;
  website: string;
  privacyPolicy: string;
  connected?: boolean;
}

export const MOCK_CONNECTORS: Connector[] = [
  // APPS
  {
    id: "gmail",
    type: "app",
    title: "Gmail",
    description: "撰写邮件，搜索会话并快速生成摘要",
    icon: ConnectorIcons.gmail,
    author: "OpenCoWork",
    website: "https://google.com/gmail",
    privacyPolicy: "https://policies.google.com",
  },
  {
    id: "gcal",
    type: "app",
    title: "Google Calendar",
    description: "查看日程安排，优化时间与活动管理",
    icon: ConnectorIcons.calendar,
    author: "OpenCoWork",
    website: "https://calendar.google.com",
    privacyPolicy: "https://policies.google.com",
  },
  {
    id: "gdrive",
    type: "app",
    title: "Google Drive",
    description:
      "快速访问文件、智能搜索内容，并让 OpenCoWork 协助你更高效地管理文档",
    icon: ConnectorIcons.drive,
    author: "OpenCoWork",
    website: "https://drive.google.com",
    privacyPolicy: "https://policies.google.com",
  },
  {
    id: "outlook-mail",
    type: "app",
    title: "Outlook Mail",
    description: "在 OpenCoWork 中无缝写作、搜索并管理你的 Outlook 电子邮件",
    icon: ConnectorIcons.outlook,
    author: "Microsoft",
    website: "https://outlook.live.com",
    privacyPolicy: "https://privacy.microsoft.com",
  },
  {
    id: "github",
    type: "app",
    title: "GitHub",
    description: "管理代码仓库，协作开发与代码审查",
    icon: ConnectorIcons.github,
    author: "GitHub",
    website: "https://github.com",
    privacyPolicy: "https://docs.github.com/en/site-policy",
  },
  {
    id: "slack",
    type: "app",
    title: "Slack",
    description: "在 OpenCoWork 中读写 Slack 对话",
    icon: ConnectorIcons.slack,
    author: "Slack",
    website: "https://slack.com",
    privacyPolicy: "https://slack.com/privacy",
  },
  {
    id: "notion",
    type: "app",
    title: "Notion",
    description: "搜索和更新内容，实现自动化流程",
    icon: ConnectorIcons.notion,
    author: "Notion",
    website: "https://notion.so",
    privacyPolicy: "https://www.notion.so/privacy",
  },

  // MCPs
  {
    id: "filesystem",
    type: "mcp",
    title: "File System",
    description: "Allow reading and writing files on the local file system",
    icon: ConnectorIcons.drive, // Reuse drive icon or similar
    author: "ModelContextProtocol",
    website: "https://modelcontextprotocol.io",
    privacyPolicy: "https://modelcontextprotocol.io/privacy",
  },
  {
    id: "postgres",
    type: "mcp",
    title: "PostgreSQL",
    description: "Read-only database access for PostgreSQL",
    icon: ConnectorIcons.notion, // Reuse database icon
    author: "ModelContextProtocol",
    website: "https://modelcontextprotocol.io",
    privacyPolicy: "https://modelcontextprotocol.io/privacy",
  },
  {
    id: "sentry",
    type: "mcp",
    title: "Sentry",
    description: "Retrieve and analyze error reports from Sentry",
    icon: ConnectorIcons.zapier, // Reuse command icon
    author: "Sentry",
    website: "https://sentry.io",
    privacyPolicy: "https://sentry.io/privacy",
  },

  // SKILLS
  {
    id: "web-search",
    type: "skill",
    title: "Web Search",
    description:
      "Perform real-time web searches to retrieve up-to-date information.",
    icon: ConnectorIcons.search,
    author: "OpenCoWork",
    website: "https://open-cowork.com",
    privacyPolicy: "https://open-cowork.com/privacy",
  },
  {
    id: "code-interpreter",
    type: "skill",
    title: "Code Interpreter",
    description: "Execute Python code safely in a sandboxed environment.",
    icon: ConnectorIcons.zapier, // Reuse command icon
    author: "OpenCoWork",
    website: "https://open-cowork.com",
    privacyPolicy: "https://open-cowork.com/privacy",
  },
];
