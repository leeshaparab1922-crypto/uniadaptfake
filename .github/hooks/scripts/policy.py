#!/usr/bin/env python3
"""Copilot camelCase command-hook adapter. Standard library only.

stdin: {cwd, toolName, toolArgs}; toolArgs may be an object or JSON string.
stdout: one Copilot decision object, or {} to retain normal permissions.
No payload-provided agent identity is trusted. See ../../README.md.
"""
import json
import ntpath
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
WRITERS = {"create", "edit", "str_replace", "str_replace_editor", "apply_patch",
           "write_file", "replace_string_in_file", "multi_replace_string_in_file",
           "delete", "move", "rename"}
SHELLS = {"bash", "powershell", "shell", "local_shell"}
READERS = {"view", "read", "grep", "rg", "glob", "search", "web_fetch",
           "web_search", "ask_user", "update_todo", "report_intent"}


def decision(kind, reason):
    return {"permissionDecision": kind, "permissionDecisionReason": reason}


def arguments(payload):
    args = payload.get("toolArgs")
    if isinstance(args, str):
        args = json.loads(args)
    if not isinstance(args, dict):
        raise ValueError("toolArgs must be an object or encoded JSON object")
    return args


def protected(path):
    # Check components BEFORE collapsing '..': an SRS path cannot be used as
    # a traversal escape. Windows trims trailing dots/spaces and supports ADS.
    return any(part.rstrip(" .").split(":")[0].casefold() == "srs_doc"
               for part in path.replace("\\", "/").split("/"))


def resolved(path, cwd):
    if not isinstance(path, str) or not path.strip() or "\x00" in path:
        raise ValueError("missing/invalid target path")
    if not isinstance(cwd, str) or not cwd.strip():
        raise ValueError("cwd is required to resolve target paths")
    windows = bool(ntpath.splitdrive(path)[0] or ntpath.splitdrive(cwd)[0])
    if windows:
        full = ntpath.normpath(ntpath.join(cwd, path))
    else:
        full = os.path.normpath(os.path.join(cwd, path.replace("\\", "/")))
    # Resolve real symlinks/junctions when they belong to this operating system.
    real = str(Path(full).resolve()) if (os.name == "nt" or not windows) else full
    return full, real


def targets(name, args):
    if name == "str_replace_editor" and args.get("command") == "view":
        return []
    if name == "apply_patch":
        patch = args.get("input", args.get("patch"))
        if not isinstance(patch, str) or not patch.startswith("*** Begin Patch"):
            raise ValueError("unrecognized apply_patch payload")
        paths = re.findall(r"^\*\*\* (?:Add File|Update File|Delete File|Move to): (.+)$",
                           patch, re.MULTILINE)
        if not paths or "*** End Patch" not in patch:
            raise ValueError("patch has no identifiable targets or is incomplete")
        return paths
    if name == "multi_replace_string_in_file":
        edits = args.get("replacements")
        if not isinstance(edits, list) or not edits:
            raise ValueError("missing replacements")
        return [target_path(edit) for edit in edits]
    if name in {"move", "rename"}:
        source = args.get("source", args.get("source_path"))
        destination = args.get("destination", args.get("destination_path"))
        if not source or not destination:
            raise ValueError("move/rename requires identifiable source and destination")
        return [source, destination]
    return [target_path(args)]


def target_path(args):
    if not isinstance(args, dict):
        raise ValueError("invalid file arguments")
    for key in ("path", "filePath", "file_path"):
        if key in args:
            value = args[key]
            if not isinstance(value, str) or not value.strip():
                raise ValueError("invalid target path")
            return value
    raise ValueError("file-writing tool has no recognized target path")


def segments(command):
    """Conservative tokenization, not a shell interpreter; preserve Windows slashes.

    Operators split executable segments, quotes protect literal echo text.
    Expansion, redirects, scripts and unknown commands require human inspection.
    """
    pattern = r'''"(?:`.|\\.|[^"\\])*"|'[^']*'|&&|\|\||[;&|\n]|[^\s;&|]+'''
    groups, group = [], []
    for match in re.finditer(pattern, command):
        token = match.group()
        if token in {"&&", "||", ";", "&", "|", "\n"}:
            if group:
                groups.append(group)
            group = []
        else:
            group.append(token[1:-1] if token[:1] in {"'", '"'} and token[-1:] == token[:1] else token)
    if group:
        groups.append(group)
    return groups


def executable(token):
    return token.replace("\\", "/").rsplit("/", 1)[-1].casefold().removesuffix(".exe")


def command_risk(command, depth=0):
    """Return publish, opaque, or ordinary. Never execute the inspected command."""
    if depth > 5:
        return "opaque"
    risk = "ordinary"
    for tokens in segments(command):
        while tokens and (re.match(r"^[A-Za-z_][A-Za-z_0-9]*=", tokens[0]) or
                          tokens[0].casefold() in {"env", "command", "call", "sudo", "exec"}):
            tokens.pop(0)
        if not tokens:
            continue
        cmd, args = executable(tokens[0]), tokens[1:]
        lower = [a.casefold() for a in args]
        if cmd in {"bash", "sh", "zsh", "pwsh", "powershell", "cmd"}:
            for i, arg in enumerate(lower):
                if arg in {"-c", "-lc", "-command", "/c"} and i + 1 < len(args):
                    nested = command_risk(" ".join(args[i + 1:]), depth + 1)
                    if nested == "publish":
                        return nested
            risk = "opaque"
        elif cmd == "git":
            i = 0
            while i < len(args) and args[i].startswith("-"):
                option = args[i]
                if option in {"-c", "-C", "--git-dir", "--work-tree", "--namespace"}:
                    i += 2
                else:
                    i += 1
            verb = lower[i] if i < len(lower) else ""
            if verb in {"push", "send-pack", "http-push"}:
                return "publish"
            if verb not in {"status", "diff", "log", "show", "ls-files", "rev-parse", "branch",
                            "add", "commit", "fetch"}:
                risk = "opaque"  # includes git aliases; cannot safely expand config
        elif cmd == "gh":
            # --repo/-R/--hostname global arguments may precede the subcommand.
            i = 0
            while i < len(args) and args[i].startswith("-"):
                i += 2 if args[i] in {"-R", "--repo", "--hostname"} else 1
            verb = lower[i] if i < len(lower) else ""
            if verb in {"pr", "release", "api"}:
                return "publish"
            risk = "opaque"
        elif ((cmd in {"npm", "pnpm", "yarn", "cargo", "dotnet"} and "publish" in lower) or
              (cmd in {"docker", "podman"} and "push" in lower) or
              (cmd == "twine" and "upload" in lower) or
              cmd in {"vercel", "netlify", "scp", "sftp", "rsync"}):
            return "publish"
        elif cmd not in {"echo", "printf", "write-output", "write-host", "pwd", "get-location",
                         "ls", "dir", "get-childitem", "cat", "get-content", "type", "head", "tail",
                         "grep", "rg", "findstr", "select-string", "test", "true", "false"}:
            risk = "opaque"
    # Even an echo can execute command substitutions; literal single-quoted data
    # is excluded. A real shell grammar is beyond this hook's trust boundary.
    active = re.sub(r"'[^']*'", "''", command)
    for substitution in re.findall(r"\$\(([^()]*)\)", active):
        if command_risk(substitution, depth + 1) == "publish":
            return "publish"
    if "$" in active or "`" in active or re.search(r"[<>]", active):
        risk = "opaque"
    return risk


def pre(payload, mode):
    if not isinstance(payload, dict) or not isinstance(payload.get("toolName"), str):
        raise ValueError("malformed Copilot hook envelope")
    name = payload["toolName"].casefold()
    if mode == "srs":
        if name in WRITERS:
            for path in targets(name, arguments(payload)):
                full, real = resolved(path, payload.get("cwd"))
                if any(protected(p) for p in (path, full, real)):
                    return decision("deny", "SRS_Doc/ is authoritative: no agent or session may edit or write it.")
            return {}
        if name in SHELLS:
            args = arguments(payload)
            command = args.get("command")
            if not isinstance(command, str) or not command.strip():
                raise ValueError("shell command is missing")
            # Explicit protected paths in opaque/write shell commands are denied;
            # ordinary reads remain usable for SRS lookup.
            if command_risk(command) != "ordinary" and (protected(command) or protected(payload.get("cwd", "")) or
                    re.search(r"(?i)(?:^|[\s/'\"\\])srs_doc(?:[/\\\s'\"]|$)", command)):
                return decision("deny", "Shell operation may write SRS_Doc/. Use read-only lookup; SRS writes are prohibited.")
        elif name not in READERS and name != "task":
            # Unknown mutation tools fail closed if their target cannot be
            # identified. Their implementation still needs a separate review.
            if (re.search(r"(?:write|edit|create|replace|delete|move|rename|patch)", name)
                    and not any(remote in name for remote in ("pull_request", "issue", "branch", "release"))):
                args = arguments(payload)
                path = target_path(args)
                full, real = resolved(path, payload.get("cwd"))
                if any(protected(p) for p in (path, full, real)):
                    return decision("deny", "External mutation tool targets protected SRS_Doc/.")
            # Unknown tool schemas cannot prove that an SRS target is safe.
            return decision("ask", "Unknown tool: confirm it cannot write SRS_Doc/ or publish on Agent 1's behalf.")
        return {}
    if mode == "publish":
        if name not in SHELLS:
            return {}
        command = arguments(payload).get("command")
        if not isinstance(command, str) or not command.strip():
            raise ValueError("shell command is missing")
        risk = command_risk(command)
        if risk == "ordinary":
            return {}
        if risk == "publish" and os.environ.get("UNIADAPT_AGENT1_SESSION") == "1":
            return decision("deny", "Agent 1 launcher: phase-planner-implementer must not publish (git push, gh pr, or equivalent).")
        return decision("ask", "Human review required: this command publishes or is opaque to static inspection. "
                        "Never approve publication for phase-planner-implementer. Agent 2 needs a PASS report "
                        "and fresh human approval to ship. Confirm no SRS_Doc writes. Main-session commands "
                        "are not subject to an Agent 1 identity claim.")
    raise ValueError("unknown pre-hook mode")


def format_written(payload):
    if not isinstance(payload, dict):
        return
    name = payload.get("toolName", "").casefold()
    if name not in WRITERS or name in {"delete", "move", "rename"}:
        return
    if payload.get("toolResult", {}).get("resultType") != "success":
        return
    deadline = time.monotonic() + 16
    for path in targets(name, arguments(payload)):
        full, real = resolved(path, payload.get("cwd"))
        file = Path(real)
        if protected(path) or protected(full) or protected(real) or not file.is_file():
            continue
        try:
            rel = file.relative_to(ROOT.resolve())
        except ValueError:
            continue
        if len(rel.parts) < 2:
            continue
        commands = []
        area = ROOT / rel.parts[0]
        if rel.parts[0].casefold() == "backend" and file.suffix.casefold() == ".py":
            config = any((area / p).is_file() for p in ("ruff.toml", ".ruff.toml"))
            project = area / "pyproject.toml"
            config = config or (project.is_file() and "[tool.ruff" in project.read_text(encoding="utf-8"))
            ruff = shutil.which("ruff")
            if ruff and config:
                commands = [[ruff, "check", "--fix", "--no-cache", str(file)],
                            [ruff, "format", "--no-cache", str(file)]]
        elif rel.parts[0].casefold() == "frontend" and file.suffix.casefold() in {".ts", ".tsx"}:
            if not (area / "package.json").is_file():
                continue
            node = shutil.which("node")
            eslint = area / "node_modules/eslint/bin/eslint.js"
            prettier = area / "node_modules/prettier/bin/prettier.cjs"
            if not prettier.is_file():
                prettier = area / "node_modules/prettier/bin-prettier.js"
            eslint_config = any(area.glob("eslint.config.*")) or any(area.glob(".eslintrc*"))
            package = json.loads((area / "package.json").read_text(encoding="utf-8"))
            prettier_config = any(area.glob(".prettierrc*")) or any(area.glob("prettier.config.*")) or "prettier" in package
            if node and eslint.is_file() and eslint_config:
                commands.append([node, str(eslint), "--fix", str(file)])
            if node and prettier.is_file() and prettier_config:
                commands.append([node, str(prettier), "--write", str(file)])
        for command in commands:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return
            try:
                subprocess.run(command, cwd=area, stdin=subprocess.DEVNULL,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               timeout=min(4, remaining), check=False)
            except (OSError, subprocess.SubprocessError):
                pass


def main():
    mode = sys.argv[1] if len(sys.argv) == 2 else "invalid"
    try:
        payload = json.load(sys.stdin)
        if mode == "format":
            format_written(payload)
            output = {}
        else:
            output = pre(payload, mode)
    except Exception:
        # Never print user content, credentials, source text, or a traceback.
        output = {} if mode == "format" else decision("deny", "Invalid hook payload or policy failure; cannot establish write/publication safety.")
    print(json.dumps(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
