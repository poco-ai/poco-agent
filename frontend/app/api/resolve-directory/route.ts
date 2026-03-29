import { NextRequest, NextResponse } from "next/server";
import { readdir } from "fs/promises";
import os from "os";
import path from "path";

const MAX_DEPTH = 5;
const MAX_RESULTS = 5;

async function searchDirectory(
  basePath: string,
  targetName: string,
  depth: number,
): Promise<string[]> {
  if (depth <= 0) return [];

  const results: string[] = [];
  try {
    const entries = await readdir(basePath, { withFileTypes: true });
    for (const entry of entries) {
      if (!entry.isDirectory()) continue;
      if (entry.name.startsWith(".")) continue;

      const fullPath = path.join(basePath, entry.name);
      if (entry.name === targetName) {
        results.push(fullPath);
        if (results.length >= MAX_RESULTS) return results;
      }

      if (depth > 1) {
        const subResults = await searchDirectory(
          fullPath,
          targetName,
          depth - 1,
        );
        for (const p of subResults) {
          results.push(p);
          if (results.length >= MAX_RESULTS) return results;
        }
      }
    }
  } catch {
    // Permission denied or directory doesn't exist
  }

  return results;
}

export async function GET(request: NextRequest) {
  const name = request.nextUrl.searchParams.get("name");
  if (!name?.trim()) {
    return NextResponse.json({ paths: [] });
  }

  const home = os.homedir();
  const matchedPaths = await searchDirectory(home, name.trim(), MAX_DEPTH);

  return NextResponse.json({ paths: matchedPaths });
}
