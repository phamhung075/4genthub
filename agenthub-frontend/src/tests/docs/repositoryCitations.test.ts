/**
 * @fileoverview The frontend's citations of repository paths resolve.
 *
 * WHY. A frontend header or comment that names a repository file is a claim the next reader trusts:
 * "the Go resolver is here", "the document that says X is this one". Nothing checked them, and two
 * rotted unnoticed - a Go path whose `infrastructure/repositories/` prefix had long been dropped, and
 * a migration guide that exists in no commit of either tree (both corrected 2026-10-20). A citation
 * that points nowhere is worse than no citation: it sends the reader looking, and finds them nothing.
 *
 * WHAT IT ASSERTS. Every `ai_docs/`, `CHANGELOG/`, `agenthub_go/` or `agenthub_client/` path written
 * in a file under `src/` or `e2e/` resolves - in this checkout, or in `origin/main`, which is the tree
 * a branch lands in. The two trees are both read because a doc added and cited by the same branch is
 * a legitimate citation before it lands (it resolves in the checkout) while a doc that arrived on main
 * from another line resolves there before this branch merges it.
 *
 * THE ONE DELIBERATE ABSENCE. `websocket-protocol-migration-guide.md` is named in
 * `test_useRealtimeSync_branch_delete.test.tsx` precisely BECAUSE it exists in no commit - the header
 * records the wrong source it replaced. An absence cannot resolve, so the exemption is named here,
 * with its reason, rather than inferred from wording: a new absence has to be added here to pass.
 */
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';

const REPO_ROOT = path.resolve(process.cwd(), '..');
const SCANNED_DIRS = ['src', 'e2e'];
const SCANNED_SUFFIXES: Record<string, true> = {
  '.ts': true,
  '.tsx': true,
  '.js': true,
  '.mjs': true,
  '.md': true,
};
const CITED_ROOTS = ['ai_docs', 'CHANGELOG', 'agenthub_go', 'agenthub_client'];
const CITED_SUFFIXES = 'go|md|ts|tsx|js|json|yaml|yml|py|rs|sh|sql|css|txt';

/** A repository-rooted path with an extension, and not the tail of a longer name. */
const CITED_PATH = new RegExp(
  `(?<![\\w./-])(?:${CITED_ROOTS.join('|')})/[A-Za-z0-9_./-]*[A-Za-z0-9_/-]\\.(?:${CITED_SUFFIXES})`,
  'g'
);

/** The paths that are named for being absent, each with the reason it is still a true claim. */
const INTENTIONALLY_ABSENT: Record<string, string> = {
  'ai_docs/core-architecture/websocket-protocol-migration-guide.md':
    'named in the branch-delete header as the source it replaced, which exists in no commit',
};

function scannedFiles(): string[] {
  const out: string[] = [];
  const walk = (dir: string) => {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      if (entry.name === 'node_modules') continue;
      const full = path.join(dir, entry.name);
      if (entry.isDirectory()) walk(full);
      else if (SCANNED_SUFFIXES[path.extname(entry.name)]) out.push(full);
    }
  };
  for (const dir of SCANNED_DIRS) {
    const full = path.join(REPO_ROOT, 'agenthub-frontend', dir);
    if (fs.existsSync(full)) walk(full);
  }
  return out;
}

/** Every repository path a text cites, mapped to the files citing it. */
function citations(text: string): string[] {
  return [...text.matchAll(CITED_PATH)].map(match => match[0]);
}

function mainTreeHas(repoPath: string): boolean {
  try {
    execFileSync('git', ['cat-file', '-e', `origin/main:${repoPath}`], {
      cwd: REPO_ROOT,
      stdio: 'ignore',
    });
    return true;
  } catch {
    return false;
  }
}

function resolves(repoPath: string): boolean {
  return fs.existsSync(path.join(REPO_ROOT, repoPath)) || mainTreeHas(repoPath);
}

describe('repository citations in the frontend', () => {
  it('names no repository path that resolves nowhere', () => {
    const cited = new Map<string, string[]>();
    for (const file of scannedFiles()) {
      const relative = path.relative(REPO_ROOT, file);
      for (const repoPath of citations(fs.readFileSync(file, 'utf8'))) {
        const citedBy = cited.get(repoPath) ?? [];
        if (!citedBy.includes(relative)) citedBy.push(relative);
        cited.set(repoPath, citedBy);
      }
    }

    // The sweep found the citations that exist, so a clean result below is not an empty scan.
    expect(cited.size).toBeGreaterThan(0);

    const unresolved = [...cited]
      .filter(([repoPath]) => !resolves(repoPath) && !INTENTIONALLY_ABSENT[repoPath])
      .map(([repoPath, citedBy]) => `${repoPath} (cited by ${citedBy.join(', ')})`);

    expect(unresolved).toEqual([]);
  });

  it('reads a path out of prose, inline code and a comment alike, and ignores lookalikes', () => {
    // The sample is assembled from CITED_ROOTS so this file's own text carries no citation the sweep
    // would have to resolve: the extractor is exercised on strings, not on paths that must exist.
    const [docRoot, logRoot, goRoot, clientRoot] = CITED_ROOTS;
    const boundaries = `${docRoot}/core-architecture/agent-boundaries.md`;
    const goSample = `${goRoot}/x/y.go`;
    const logSample = `${logRoot}/2026-10-20--a-title.md`;

    expect(
      citations(
        `the file \`${boundaries}\` say so; see ${goSample}.\n` +
          `// ${logSample} records it\n` +
          `not a citation: my_${goSample}, ${clientRoot}.obsolete/, ${logRoot}/`
      )
    ).toEqual([boundaries, goSample, logSample]);
  });
});
