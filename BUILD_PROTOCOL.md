# Build Protocol: How to Vibecode a Real Project Without Losing Your Mind

This document captures a working method developed over one real project
(medium-reader): a human, a planning/reviewing AI (Claude), and a
building AI running in an IDE (Antigravity/Gemini, Cursor, Claude Code,
etc.). It generalizes to any project, any builder tool.

Drop this file into a new project's repo root, or paste it as the first
message in a planning conversation, alongside a description of what you
want to build.

---

## The Core Idea

Two AI roles, kept separate on purpose:

- **The Planner** (this conversation) never writes code directly into the
  project. It writes precise, scoped prompts; reviews what comes back;
  catches problems; decides what happens next.
- **The Builder** (the IDE agent) executes exactly one prompt at a time,
  in a fresh conversation, and reports back.

The human is not a passive relay between them. The human runs verification
commands, looks at real screenshots, and is the one who ultimately decides
"this is good enough, move on." Neither AI's self-report is trusted as fact
until checked.

## Why This Works

A single long agent conversation degrades: context gets muddled, earlier
mistakes get silently carried forward, and "it's done" stops meaning
anything. Splitting work into small, independently-verified steps - each
in its own fresh conversation - keeps every single step small enough to
actually verify, and small enough that when something breaks, it's obvious
which step broke it.

## The Step Discipline

1. **One step, one fresh conversation.** Durable context lives in a rules
   file (AGENTS.md or equivalent) that the builder reads at the start of
   every conversation - not in chat history.
2. **Plan before code.** Every prompt ends with "make a numbered plan, wait
   for my approval" before any file gets touched.
3. **Commit at checkpoints, not once at the end.** A step with 5 real
   sub-tasks gets 5 small commits. If something breaks or gets lost, you
   lose one sub-task's worth of work, not the whole step.
4. **Discovery before implementation, for anything uncertain.** Before
   writing a parser for an unfamiliar format, a client for an external
   service, or a redesign based on a reference site: spend one step just
   gathering real evidence (save fixtures, take measurements, read actual
   API responses) and write it to a notes doc. Review the findings
   together. *Then* write the implementation step, scoped to what was
   actually found - not what was assumed going in.
5. **Small, targeted fixes over full redos.** When something breaks, first
   figure out exactly what's wrong before touching anything. A one-file bug
   gets a one-file fix, not a re-run of the whole step.

## The Verification Ritual (non-negotiable)

After every single builder turn, before reading its summary:

1. Run the project's real check command yourself (`pnpm check`, `npm test`,
   whatever it is).
2. Run `git status` / `git diff` yourself. Read the actual diff, at least
   the file list. Confirm it touches only what the task asked for.
3. For anything with a visible effect (a page, a UI change, a CLI's
   output): actually run it and look. A green type-checker does NOT prove
   a page renders correctly, loads real data, or looks right.
4. Only after 1-3 are clean do you read the agent's own report - as a
   claim to spot-check, not a fact to accept.

**If the builder has real browser/devtools tools available, put this same
loop on it**: read a file back from disk after editing it; check the
actual rendered page and computed styles after a visual change; don't move
to the next item until both are confirmed. This catches most problems
before the human ever sees them - but the human should still spot-check
with fresh eyes periodically, because a tool verifying its own output can
share the same blind spot that caused the bug in the first place.

## Known Failure Patterns (real bugs from this project - watch for these)

- **A green check does not mean the file has content.** Type-checkers and
  linters can pass cleanly against an empty file, or a file missing a
  runtime-required piece (e.g. a Next.js page with no default export).
  If it's a runtime-critical file, load it in a running app, don't just
  lint it.
- **Committed-good, disk-corrupted is a real, recurring failure mode** in
  some agentic IDEs - a commit can contain correct code while the working
  tree silently reverts a file afterward. `git diff <known-good-commit> --
  <file>` is the fastest way to find out which one is lying.
- **A file the editor shows as empty might just be a stale tab.** Always
  confirm via a fresh read from disk or `git show HEAD:<file>` before
  panicking or asking for a fix.
- **Never let an agent force-push without asking first, every time.** Put
  this in the rules file explicitly. A `git reset`/selective-restore/
  force-push sequence to "clean up" a commit is exactly the kind of
  surgery that silently drops files.
- **Speculative infrastructure outlives its own reason for existing.** If
  a library/feature is added to support something (e.g. a manual UI
  toggle), and that something is later removed, its supporting
  infrastructure (state, persistence, config) must be removed in the same
  change - not left behind "in case." Leftover infrastructure causes
  bugs that are disproportionately hard to diagnose, because the code
  looks intentional.
- **A working reference component doesn't guarantee a new one matches it.**
  Getting one page's design system right doesn't mean a newly-added route
  inherited it correctly - actually compare them side by side after
  building the second one, don't assume.
- **When copying visual inspiration from a real site: measure, don't
  view-source.** Pull real computed values (font-size, spacing, color) via
  a browser inspector - that's just factual data, fine to reuse freely.
  Don't copy actual markup, CSS, or component code/names from someone
  else's project - build your own version of the idea instead.

## Design System Discipline (for anything visual)

- Get real numbers from a reference before building, not invented ones.
  "Make it clean" is not a spec; "16px/24px, font-weight 500" is.
- Centralize every text style / spacing scale / color token in ONE file.
  Every component references it; nothing invents its own values inline.
- Once that file exists, lint-enforce it if your stack allows (e.g. a
  custom ESLint rule banning raw utility classes outside the token file).
  A convention that isn't enforced by tooling will eventually be violated
  by an agent that "forgot."
- Write down explicit non-goals ("no cards, no shadows, no thumbnails") as
  firmly as the goals. Restraint needs to be a documented rule, or it gets
  slowly eroded one "just this one card" at a time.

## Keeping a Decision Record

- **ADRs** (`docs/adr/0001-...md`): one per meaningful architectural
  choice - what was decided, why, and what it costs. Keep each under ~25
  lines. Write one the moment a real tradeoff gets made, not retroactively.
- **Step logs** (`docs/steps/step-NN.md`): what actually happened in each
  step, including messy real-world findings (an interrupted run, an
  unexpected discovery) - this is your evidence trail, and it's genuinely
  useful three weeks later when you've forgotten why something works the
  way it does.
- **A living rules file** (`AGENTS.md` or equivalent): architecture
  summary, stack, commands, conventions, and a running "working agreement"
  section that accumulates hard-won rules (like the force-push rule above)
  as you learn them. This file is what makes every fresh conversation
  actually consistent with every other one.

## Scope Discipline

- If a request implies a feature that wasn't explicitly asked for (search,
  a saved-items view, configurability, extra flexibility), name it and ask
  before building it - don't let it ride in on the back of something else.
- It's fine, and good, to descope something mid-project once its cost
  becomes clear (e.g. dropping a feature that adds complexity nobody
  actually needed yet). Update the plan and say so explicitly rather than
  quietly building it anyway.

## Starting a New Project With This

1. Do the planning conversation first: what's being built, what stack,
   what's explicitly out of scope. Write ADRs for the real decisions.
2. Scaffold the project in Step 1, with the rules file and this protocol's
   key points folded into it from day one (not bolted on after the first
   crisis).
3. For each subsequent piece: discovery step (if unfamiliar/fragile) →
   plan → implementation step with checkpoints → human verification →
   move on. Repeat.
4. When something breaks, diagnose before fixing. When a fix is small,
   consider doing it directly yourself rather than routing it through
   another agent turn - it's often faster and removes a point of failure.
