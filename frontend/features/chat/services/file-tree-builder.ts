/**
 * File tree builder for workspace files.
 *
 * Converts a flat list of file nodes into a hierarchical tree structure
 * with proper sorting (folders first, then alphabetical).
 */

import type { FileNode } from "../types/index.ts";

// ---------------------------------------------------------------------------
// Flatten
// ---------------------------------------------------------------------------

function flattenNodes(nodes: FileNode[]): FileNode[] {
  const result: FileNode[] = [];
  for (const item of nodes) {
    result.push(item);
    if (item.children) {
      result.push(...flattenNodes(item.children));
    }
  }
  return result;
}

// ---------------------------------------------------------------------------
// Sort
// ---------------------------------------------------------------------------

function sortTree(nodes: FileNode[]): void {
  nodes.sort((a, b) => {
    if (a.type !== b.type) return a.type === "folder" ? -1 : 1;
    return a.name.localeCompare(b.name);
  });
  for (const node of nodes) {
    if (node.children) sortTree(node.children);
  }
}

// ---------------------------------------------------------------------------
// Remove empty folders
// ---------------------------------------------------------------------------

function removeEmptyFolders(nodes: FileNode[]): FileNode[] {
  return nodes
    .map((node) => {
      if (node.type === "folder" && node.children) {
        node.children = removeEmptyFolders(node.children);
        if (node.children.length === 0) return null;
      }
      return node;
    })
    .filter((node): node is FileNode => node !== null);
}

// ---------------------------------------------------------------------------
// Build tree
// ---------------------------------------------------------------------------

/**
 * Builds a hierarchical file tree from a flat list of file nodes.
 *
 * Handles:
 * - Creating intermediate directory nodes
 * - Deduplication of paths
 * - Sorting (folders first, then alphabetical)
 * - Removing empty folders
 */
export function buildFileTree(rawFiles: FileNode[]): FileNode[] {
  if (!rawFiles || rawFiles.length === 0) return [];

  const nodeMap = new Map<string, FileNode>();
  const rootNodes: FileNode[] = [];
  const allNodes = flattenNodes(rawFiles);

  // Initialize map with empty children arrays
  for (const node of allNodes) {
    nodeMap.set(node.path, { ...node, children: [] });
  }

  const processedPaths = new Set<string>();
  const sortedPaths = Array.from(nodeMap.keys()).sort();

  for (const path of sortedPaths) {
    if (processedPaths.has(path)) continue;

    const parts = path.split("/");
    let currentPath = "";

    parts.forEach((part, index) => {
      const parentPath = currentPath;
      currentPath = currentPath ? `${currentPath}/${part}` : part;

      if (processedPaths.has(currentPath)) return;

      let node = nodeMap.get(currentPath);

      if (!node) {
        const isLastPart = index === parts.length - 1;
        const originalNode = nodeMap.get(path);

        node = {
          id: currentPath,
          name: part,
          path: currentPath,
          type: isLastPart && originalNode ? originalNode.type : "folder",
          children: [],
          ...(isLastPart && originalNode
            ? {
                url: originalNode.url,
                mimeType: originalNode.mimeType,
                oss_status: originalNode.oss_status,
                oss_meta: originalNode.oss_meta,
              }
            : {}),
        };
        nodeMap.set(currentPath, node);
      }

      if (parentPath) {
        const parent = nodeMap.get(parentPath);
        if (parent) {
          if (!parent.children) parent.children = [];
          if (!parent.children.find((c) => c.path === node!.path)) {
            parent.children.push(node);
          }
        }
      } else {
        if (!rootNodes.find((n) => n.path === node!.path)) {
          rootNodes.push(node);
        }
      }

      processedPaths.add(currentPath);
    });
  }

  sortTree(rootNodes);
  return removeEmptyFolders(rootNodes);
}
