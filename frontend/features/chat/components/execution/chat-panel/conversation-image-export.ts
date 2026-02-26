const BASE_EXPORT_WIDTH = 1242;
const BASE_HEADER_HEIGHT_BUDGET = 108;
const MULTI_IMAGE_HEIGHT_RATIO = 4 / 3;
const MIN_EXPORT_WIDTH = 560;

export type ConversationImageExportMode = "long" | "multi";

export interface ConversationImageExportResult {
  count: number;
  mode: ConversationImageExportMode;
}

export interface ConversationImageExportOptions {
  panelElement: HTMLElement;
  filename?: string;
  mode: ConversationImageExportMode;
}

function sanitizeFilename(value: string | undefined): string {
  const cleaned = (value || "").replace(/[\\/:*?"<>|]+/g, "-").trim();
  return cleaned.length > 0 ? cleaned : "poco-conversation";
}

function getExportWidth(panelElement: HTMLElement): number {
  const messageList =
    panelElement.querySelector<HTMLElement>("[data-chat-message-list]") ??
    panelElement;
  const width = Math.round(messageList.getBoundingClientRect().width);
  return Math.max(width, MIN_EXPORT_WIDTH);
}

function scaleByWidth(value: number, exportWidth: number): number {
  return Math.round((value / BASE_EXPORT_WIDTH) * exportWidth);
}

function getMultiImageHeight(exportWidth: number): number {
  return Math.round(exportWidth * MULTI_IMAGE_HEIGHT_RATIO);
}

function getBackgroundColor(): string {
  const value = getComputedStyle(document.documentElement)
    .getPropertyValue("--background")
    .trim();
  return value || "#ffffff";
}

function getTokenColor(variable: string, fallback: string): string {
  const value = getComputedStyle(document.documentElement)
    .getPropertyValue(variable)
    .trim();
  return value || fallback;
}

function triggerDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 0);
}

async function waitForNextFrame(): Promise<void> {
  await new Promise<void>((resolve) => {
    window.requestAnimationFrame(() => resolve());
  });
}

async function waitForImages(node: HTMLElement): Promise<void> {
  const imageNodes = Array.from(node.querySelectorAll("img"));
  if (imageNodes.length === 0) return;

  await Promise.all(
    imageNodes.map((image) => {
      if (image.complete) {
        return Promise.resolve();
      }
      return new Promise<void>((resolve) => {
        const done = () => resolve();
        image.addEventListener("load", done, { once: true });
        image.addEventListener("error", done, { once: true });
      });
    }),
  );
}

function isCrossOriginImageSrc(src: string): boolean {
  try {
    const parsed = new URL(src, window.location.href);
    if (parsed.protocol === "data:" || parsed.protocol === "blob:") {
      return false;
    }
    return parsed.origin !== window.location.origin;
  } catch {
    return false;
  }
}

function getPlaceholderSize(image: HTMLImageElement): {
  width: number;
  height: number;
} {
  const rect = image.getBoundingClientRect();
  const attrWidth = Number(image.getAttribute("width") || 0);
  const attrHeight = Number(image.getAttribute("height") || 0);
  const width = Math.max(Math.round(rect.width), image.width, attrWidth, 24);
  const height = Math.max(
    Math.round(rect.height),
    image.height,
    attrHeight,
    24,
  );
  return { width, height };
}

function shouldReplaceImage(image: HTMLImageElement): boolean {
  const src = image.getAttribute("src") ?? "";
  if (!src) return true;
  if (src.startsWith("blob:") || src.startsWith("file:")) return true;
  if (isCrossOriginImageSrc(src)) return true;
  if (image.complete && image.naturalWidth === 0) return true;
  return false;
}

function replaceProblematicImages(node: HTMLElement): number {
  const muted = getTokenColor("--muted", "#f3f4f6");
  const border = getTokenColor("--border", "#e5e7eb");
  let replaced = 0;

  node.querySelectorAll<HTMLImageElement>("img").forEach((image) => {
    if (!shouldReplaceImage(image)) return;

    const placeholder = document.createElement("div");
    const { width, height } = getPlaceholderSize(image);
    const computed = getComputedStyle(image);
    placeholder.style.width = `${width}px`;
    placeholder.style.height = `${height}px`;
    placeholder.style.background = muted;
    placeholder.style.border = `1px solid ${border}`;
    placeholder.style.borderRadius = computed.borderRadius || "8px";
    placeholder.style.display =
      computed.display === "block" ? "block" : "inline-block";
    placeholder.style.verticalAlign = "middle";
    image.replaceWith(placeholder);
    replaced += 1;
  });

  return replaced;
}

function stringifyError(error: unknown): string {
  if (error instanceof Error) return error.message;
  if (error instanceof Event) return `Event(${error.type})`;
  try {
    return JSON.stringify(error);
  } catch {
    return String(error);
  }
}

function toDataUrl(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () =>
      reject(reader.error ?? new Error("Failed to read blob"));
    reader.readAsDataURL(blob);
  });
}

function getCandidateLogoUrls(): string[] {
  const candidates = ["/poco.JPG"];
  const nextData = (
    window as Window & {
      __NEXT_DATA__?: { assetPrefix?: string };
    }
  ).__NEXT_DATA__;
  const assetPrefix = nextData?.assetPrefix?.trim();
  if (assetPrefix) {
    const normalizedPrefix = assetPrefix.endsWith("/")
      ? assetPrefix.slice(0, -1)
      : assetPrefix;
    candidates.unshift(`${normalizedPrefix}/poco.JPG`);
  }
  return Array.from(new Set(candidates));
}

async function resolveLogoSrc(): Promise<string> {
  const urls = getCandidateLogoUrls();
  for (const candidate of urls) {
    try {
      const url = new URL(candidate, window.location.origin).toString();
      const response = await fetch(url, { cache: "force-cache" });
      if (!response.ok) continue;
      const blob = await response.blob();
      if (blob.size === 0) continue;
      return await toDataUrl(blob);
    } catch {
      // Fallback to the next candidate.
    }
  }
  return "/poco.JPG";
}

async function renderExportBlob(
  node: HTMLElement,
  width: number,
  preferredPixelRatio: number,
): Promise<Blob> {
  const { toBlob } = await import("html-to-image");
  const ratios = [preferredPixelRatio, 2, 1.5];
  let lastError: unknown = null;

  for (const ratio of ratios) {
    try {
      const blob = await toBlob(node, {
        cacheBust: true,
        pixelRatio: ratio,
        backgroundColor: getBackgroundColor(),
        width,
      });
      if (blob) {
        return blob;
      }
      lastError = new Error("html-to-image returned empty blob");
    } catch (error) {
      lastError = error;
      const replaced = replaceProblematicImages(node);
      if (replaced > 0) {
        await waitForNextFrame();
      }
    }
  }

  throw new Error(
    `Failed to render export image: ${stringifyError(lastError)}`,
  );
}

function createExportHeader(exportWidth: number, logoSrc: string): HTMLElement {
  const scale = exportWidth / BASE_EXPORT_WIDTH;
  const foreground = getTokenColor("--foreground", "#111827");
  const border = getTokenColor("--border", "#e5e7eb");
  const muted = getTokenColor("--muted", "#f3f4f6");

  const header = document.createElement("div");
  header.style.display = "flex";
  header.style.alignItems = "center";
  header.style.gap = `${Math.round(14 * scale)}px`;
  header.style.padding = `${Math.round(18 * scale)}px ${Math.round(24 * scale)}px`;
  header.style.borderBottom = `1px solid ${border}`;
  header.style.background = muted;
  header.style.minHeight = `${Math.round(80 * scale)}px`;
  header.style.flexShrink = "0";

  const logoWrap = document.createElement("div");
  logoWrap.style.width = `${Math.round(48 * scale)}px`;
  logoWrap.style.height = `${Math.round(48 * scale)}px`;
  logoWrap.style.borderRadius = "9999px";
  logoWrap.style.overflow = "hidden";
  logoWrap.style.border = `1px solid ${border}`;
  logoWrap.style.background = muted;
  logoWrap.style.flexShrink = "0";

  const logo = document.createElement("img");
  logo.src = logoSrc;
  logo.alt = "Poco logo";
  logo.style.width = "100%";
  logo.style.height = "100%";
  logo.style.objectFit = "cover";

  const title = document.createElement("span");
  title.textContent = "Poco";
  title.style.display = "inline-flex";
  title.style.alignItems = "center";
  title.style.fontFamily = "var(--font-brand)";
  title.style.fontSize = `${Math.round(32 * scale)}px`;
  title.style.fontWeight = "700";
  title.style.lineHeight = "1.1";
  title.style.color = foreground;
  title.style.letterSpacing = "0.01em";

  logoWrap.appendChild(logo);
  header.appendChild(logoWrap);
  header.appendChild(title);
  return header;
}

function prepareCloneForExport(clone: HTMLElement, exportWidth: number): void {
  clone.style.width = `${exportWidth}px`;
  clone.style.maxWidth = `${exportWidth}px`;
  clone.style.height = "auto";
  clone.style.minHeight = "0";
  clone.style.maxHeight = "none";
  clone.style.overflow = "visible";

  const messageList = clone.querySelector<HTMLElement>(
    "[data-chat-message-list]",
  );
  if (messageList) {
    messageList.style.width = "100%";
    messageList.style.maxWidth = "100%";
    messageList.style.height = "auto";
    messageList.style.minHeight = "0";
    messageList.style.maxHeight = "none";
    messageList.style.overflow = "visible";
  }

  const scrollArea = clone.querySelector<HTMLElement>(
    "[data-chat-scroll-area]",
  );
  if (scrollArea) {
    scrollArea.style.height = "auto";
    scrollArea.style.minHeight = "0";
    scrollArea.style.maxHeight = "none";
    scrollArea.style.overflow = "visible";
  }

  const viewport = clone.querySelector<HTMLElement>(
    "[data-radix-scroll-area-viewport]",
  );
  if (viewport) {
    viewport.style.height = "auto";
    viewport.style.maxHeight = "none";
    viewport.style.overflow = "visible";
  }

  clone
    .querySelectorAll<HTMLElement>("[data-radix-scroll-area-scrollbar]")
    .forEach((scrollbar) => {
      scrollbar.style.display = "none";
    });

  clone
    .querySelectorAll<HTMLElement>("[data-chat-export-skip]")
    .forEach((node) => {
      node.remove();
    });

  clone.querySelectorAll<HTMLElement>(".line-clamp-5").forEach((node) => {
    node.classList.remove("line-clamp-5");
    node.style.setProperty("display", "block");
    node.style.setProperty("overflow", "visible");
    node.style.setProperty("-webkit-line-clamp", "unset");
    node.style.setProperty("-webkit-box-orient", "unset");
  });
}

function buildExportNode(
  contentNode: HTMLElement,
  exportWidth: number,
  logoSrc: string,
  fixedHeight?: number,
): HTMLElement {
  const exportNode = document.createElement("div");
  exportNode.style.width = `${exportWidth}px`;
  exportNode.style.maxWidth = `${exportWidth}px`;
  exportNode.style.background = getBackgroundColor();
  exportNode.style.color = getTokenColor("--foreground", "#111827");
  exportNode.style.overflow = "visible";
  exportNode.style.display = "flex";
  exportNode.style.flexDirection = "column";
  if (fixedHeight) {
    exportNode.style.height = `${fixedHeight}px`;
    exportNode.style.minHeight = `${fixedHeight}px`;
    exportNode.style.maxHeight = `${fixedHeight}px`;
    exportNode.style.overflow = "hidden";
  }

  exportNode.appendChild(createExportHeader(exportWidth, logoSrc));
  contentNode.style.flexShrink = "0";
  exportNode.appendChild(contentNode);
  return exportNode;
}

function buildContentPage(
  template: HTMLElement,
  items: HTMLElement[],
  indices: number[],
): HTMLElement {
  const content = template.cloneNode(false) as HTMLElement;
  content.style.height = "auto";
  content.style.maxHeight = "none";
  content.style.overflow = "visible";
  indices.forEach((index) => {
    content.appendChild(items[index].cloneNode(true));
  });
  return content;
}

interface ItemSlice {
  index: number;
  offset: number;
  height: number;
  full: boolean;
}

function splitItemSlices(
  itemHeights: number[],
  pageContentHeight: number,
): ItemSlice[][] {
  const pages: ItemSlice[][] = [];
  let currentPage: ItemSlice[] = [];
  let remainingHeight = pageContentHeight;

  itemHeights.forEach((rawHeight, index) => {
    if (rawHeight <= 0) {
      currentPage.push({ index, offset: 0, height: 0, full: true });
      return;
    }

    const itemHeight = Math.ceil(rawHeight);
    let consumed = 0;

    while (consumed < itemHeight) {
      if (remainingHeight <= 0) {
        pages.push(currentPage);
        currentPage = [];
        remainingHeight = pageContentHeight;
      }

      const remainingItemHeight = itemHeight - consumed;
      const take = Math.min(remainingItemHeight, remainingHeight);
      currentPage.push({
        index,
        offset: consumed,
        height: take,
        full: consumed === 0 && take === itemHeight,
      });
      consumed += take;
      remainingHeight -= take;
    }
  });

  if (currentPage.length > 0) {
    pages.push(currentPage);
  }

  return pages.length > 0 ? pages : [[]];
}

function buildSlicedItem(
  item: HTMLElement,
  offset: number,
  viewportHeight: number,
): HTMLElement {
  const viewport = document.createElement("div");
  viewport.style.width = "100%";
  viewport.style.height = `${viewportHeight}px`;
  viewport.style.maxHeight = `${viewportHeight}px`;
  viewport.style.overflow = "hidden";
  viewport.style.position = "relative";
  viewport.style.flexShrink = "0";

  const content = item.cloneNode(true) as HTMLElement;
  content.style.transform = `translateY(-${offset}px)`;
  content.style.willChange = "transform";
  viewport.appendChild(content);
  return viewport;
}

function buildSlicedContentPage(
  template: HTMLElement,
  items: HTMLElement[],
  slices: ItemSlice[],
): HTMLElement {
  const content = template.cloneNode(false) as HTMLElement;
  content.style.height = "auto";
  content.style.maxHeight = "none";
  content.style.overflow = "visible";

  slices.forEach((slice) => {
    const item = items[slice.index];
    if (!item) return;
    if (slice.full) {
      content.appendChild(item.cloneNode(true));
      return;
    }
    content.appendChild(buildSlicedItem(item, slice.offset, slice.height));
  });

  return content;
}

async function measureHeaderHeight(
  host: HTMLElement,
  exportWidth: number,
  logoSrc: string,
): Promise<number> {
  const header = createExportHeader(exportWidth, logoSrc);
  header.style.width = `${exportWidth}px`;
  host.appendChild(header);

  await waitForNextFrame();
  await waitForImages(header);
  const measured = Math.ceil(header.getBoundingClientRect().height);
  header.remove();

  const fallback = scaleByWidth(BASE_HEADER_HEIGHT_BUDGET, exportWidth);
  return Math.max(measured, fallback);
}

function getPageFilename(
  base: string,
  pageIndex: number,
  total: number,
): string {
  if (total <= 1) return `${base}.png`;
  const padding = String(total).length < 2 ? 2 : String(total).length;
  const pageNumber = String(pageIndex + 1).padStart(padding, "0");
  return `${base}-${pageNumber}.png`;
}

export async function exportConversationImage(
  options: ConversationImageExportOptions,
): Promise<ConversationImageExportResult> {
  const exportWidth = getExportWidth(options.panelElement);
  const multiImageHeight = getMultiImageHeight(exportWidth);
  const logoSrc = await resolveLogoSrc();

  const host = document.createElement("div");
  host.style.position = "fixed";
  host.style.left = "-10000px";
  host.style.top = "0";
  host.style.pointerEvents = "none";
  host.style.zIndex = "-1";
  document.body.appendChild(host);

  try {
    const headerHeight = await measureHeaderHeight(host, exportWidth, logoSrc);
    const pageContentHeight = Math.max(1, multiImageHeight - headerHeight);

    const clone = options.panelElement.cloneNode(true) as HTMLElement;
    prepareCloneForExport(clone, exportWidth);
    host.appendChild(clone);

    await waitForNextFrame();
    await waitForNextFrame();
    await waitForImages(clone);

    const sourceContent =
      clone.querySelector<HTMLElement>("[data-chat-scroll-content]") ?? clone;
    const exportItems = Array.from(
      sourceContent.querySelectorAll<HTMLElement>(
        ":scope > [data-chat-export-item]",
      ),
    );

    if (exportItems.length === 0) {
      return { count: 0, mode: options.mode };
    }

    const filenameBase = sanitizeFilename(options.filename);
    const preferredPixelRatio = Math.min(
      Math.max(window.devicePixelRatio || 1, 2),
      3,
    );

    if (options.mode === "long") {
      try {
        const longContent = buildContentPage(
          sourceContent,
          exportItems,
          exportItems.map((_, index) => index),
        );
        const exportNode = buildExportNode(longContent, exportWidth, logoSrc);
        host.replaceChildren(exportNode);

        await waitForNextFrame();
        await waitForImages(exportNode);
        replaceProblematicImages(exportNode);

        const blob = await renderExportBlob(
          exportNode,
          exportWidth,
          preferredPixelRatio,
        );
        triggerDownload(blob, `${filenameBase}.png`);
        return { count: 1, mode: options.mode };
      } catch {
        // Long image may exceed browser canvas limits, fallback to multi export.
      }
    }

    const itemHeights = exportItems.map((item) =>
      Math.ceil(item.getBoundingClientRect().height),
    );
    const pageSlices = splitItemSlices(itemHeights, pageContentHeight);
    const totalPages = Math.max(1, pageSlices.length);

    for (let i = 0; i < totalPages; i += 1) {
      const pageContent = buildSlicedContentPage(
        sourceContent,
        exportItems,
        pageSlices[i] ?? [],
      );
      const pageNode = buildExportNode(
        pageContent,
        exportWidth,
        logoSrc,
        multiImageHeight,
      );
      host.replaceChildren(pageNode);

      await waitForNextFrame();
      await waitForImages(pageNode);
      replaceProblematicImages(pageNode);

      const blob = await renderExportBlob(
        pageNode,
        exportWidth,
        preferredPixelRatio,
      );
      triggerDownload(blob, getPageFilename(filenameBase, i, totalPages));
    }

    return {
      count: totalPages,
      mode: options.mode === "long" ? "multi" : options.mode,
    };
  } finally {
    host.remove();
  }
}
