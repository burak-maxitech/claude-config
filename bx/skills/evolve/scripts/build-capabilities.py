#!/usr/bin/env python3
"""build-capabilities.py — derive the bx capability inventory deterministically.

The inventory is the vocabulary of `affected_capability`: a lane may only name a string from
this list (or `bx:pain/<id>`), so `finding_id` is stable across runs. Until bx 2.12.0 the
orchestrator rebuilt the list by Grep every run and lanes worded strings freehand, which is
why the same finding re-entered under new ids.

Usage (from the repo root):
    python -I bx/skills/evolve/scripts/build-capabilities.py --write   # regenerate bx/skills/evolve/capabilities.json
    python -I bx/skills/evolve/scripts/build-capabilities.py --check   # diff live vs pinned; exit 1 on drift

Four categories, matching SKILL.md Step 0.2:
  (a) frontmatter keys          bx:<skill|agent>/<key>            every key in a SKILL.md or agent frontmatter
      tools named in them        bx:<skill|agent>/tool:<Tool>      each tool in allowed-tools / tools (specifiers stripped)
  (b) built-in slash commands    bx:<owner>/builtin:<command>      backticked `/name` tokens that are not bx:-namespaced
  (c) harness idioms             bx:<owner>/idiom:<name>           a fixed table of regexes (below)
  (d) hook events                bx:hooks/<Event>                  every event registered in bx/hooks/hooks.json

<owner> is the skill or agent name for files under bx/skills/<name>/ or bx/agents/<name>.md,
`plugin` for bx/scripts and bx/.claude-plugin, and `docs` for README.md and workflow.md.
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]  # repo root (bx/skills/evolve/scripts/<file>)
PINNED = ROOT / "bx" / "skills" / "evolve" / "capabilities.json"

IDIOMS = [
    ("agent-dispatch", re.compile(r"subagent_type")),
    ("dynamic-injection", re.compile(r"^\s*!`", re.M)),
    ("bin-path-helper", re.compile(r"\bbin/\b")),
    ("no-env-persistence", re.compile(r"shell state does not persist|does not persist (?:between|across) (?:Bash )?calls", re.I)),
    ("allowed-tools-enumeration", re.compile(r"allowed-tools")),
    ("session-start-hook", re.compile(r"SessionStart")),
    ("plugin-root-var", re.compile(r"CLAUDE_PLUGIN_ROOT")),
    ("skill-dir-var", re.compile(r"CLAUDE_SKILL_DIR")),
    ("model-invocation-flag", re.compile(r"disable-model-invocation")),
    ("rewind-checkpoints", re.compile(r"/rewind|Esc Esc|checkpoint", re.I)),
    ("ask-user-question", re.compile(r"AskUserQuestion")),
    ("task-tracker", re.compile(r"\bTask(?:Create|List|Get)\b|TodoWrite")),
]
BUILTIN = re.compile(r"`/([a-z][a-z0-9-]*(?: [a-z][a-z0-9-]*)?)`")
FRONTMATTER_KEY = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*):", re.M)
TOOL_LIST_KEYS = ("allowed-tools", "tools", "disallowed-tools")


def owner_of(path: Path) -> str:
    rel = path.relative_to(ROOT).as_posix()
    m = re.match(r"bx/skills/([^/]+)/", rel)
    if m:
        return m.group(1)
    m = re.match(r"bx/agents/([^/]+)\.md$", rel)
    if m:
        return m.group(1)
    if rel.startswith("bx/"):
        return "plugin"
    return "docs"


def frontmatter(text: str):
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    return text[3:end] if end != -1 else None


def tools_in(value: str):
    for raw in value.split(","):
        tok = raw.strip()
        if not tok:
            continue
        name = re.split(r"[(\s]", tok, maxsplit=1)[0]
        if name == "*":
            continue
        yield name


def build():
    caps = set()
    files = sorted(list((ROOT / "bx").rglob("*.md")) + [ROOT / "README.md", ROOT / "workflow.md"])
    files = [f for f in files if "tests" not in f.relative_to(ROOT).parts and "fixtures" not in f.relative_to(ROOT).parts]
    for f in files:
        text = f.read_text(encoding="utf-8", errors="replace")
        owner = owner_of(f)
        fm = frontmatter(text)
        if fm and f.name in ("SKILL.md",) or (fm and f.parent.name == "agents"):
            for key in FRONTMATTER_KEY.findall(fm):
                caps.add(f"bx:{owner}/{key}")
            for key in TOOL_LIST_KEYS:
                m = re.search(rf"^{key}:\s*(.+)$", fm, re.M)
                if m:
                    for tool in tools_in(m.group(1)):
                        caps.add(f"bx:{owner}/tool:{tool}")
        for cmd in BUILTIN.findall(text):
            if cmd.startswith("bx:") or cmd.startswith("bx "):
                continue
            caps.add(f"bx:{owner}/builtin:{cmd.replace(' ', '-')}")
        for name, rx in IDIOMS:
            if rx.search(text):
                caps.add(f"bx:{owner}/idiom:{name}")
    hooks = ROOT / "bx" / "hooks" / "hooks.json"
    if hooks.exists():
        for event in json.loads(hooks.read_text(encoding="utf-8")).get("hooks", {}):
            caps.add(f"bx:hooks/{event}")
    return sorted(caps)


def digest(caps):
    return hashlib.sha1("\n".join(sorted(set(caps))).encode("utf-8")).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--write", action="store_true")
    g.add_argument("--check", action="store_true")
    g.add_argument("--print", action="store_true")
    args = ap.parse_args()

    live = build()
    if args.print:
        print("\n".join(live))
        return 0
    if args.write:
        PINNED.write_text(json.dumps({
            "generated_by": "bx/skills/evolve/scripts/build-capabilities.py --write",
            "count": len(live),
            "inventory_hash": digest(live),
            "capabilities": live,
        }, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {PINNED.relative_to(ROOT).as_posix()}: {len(live)} capabilities, hash {digest(live)[:12]}")
        return 0
    if not PINNED.exists():
        print(json.dumps({"drift": True, "error": "capabilities.json missing — run --write"}))
        return 1
    pinned = json.loads(PINNED.read_text(encoding="utf-8")).get("capabilities", [])
    added = sorted(set(live) - set(pinned))
    removed = sorted(set(pinned) - set(live))
    print(json.dumps({
        "drift": bool(added or removed),
        "pinned_count": len(pinned),
        "live_count": len(live),
        "pinned_hash": digest(pinned),
        "live_hash": digest(live),
        "added_live_only": added,
        "removed_pinned_only": removed,
    }, indent=2))
    return 1 if (added or removed) else 0


if __name__ == "__main__":
    sys.exit(main())
