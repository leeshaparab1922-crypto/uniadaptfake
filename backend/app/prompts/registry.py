"""Versioned prompt registry (ADR-0017, NFR-MNT-001, NFR-DAT-002).

Prompts live in `backend/app/prompts/<agent>/v<N>.toml`, are read with the standard library's
`tomllib`, and are synced at application/worker startup into the append-only `prompt_versions`
table with a SHA-256 of the file bytes. An existing (agent, version) whose hash differs makes
startup fail: a change is always a NEW `v<N+1>` file. Templates use `string.Template`.

Deterministic services never import this package (a static test enforces it).
"""

from __future__ import annotations

import hashlib
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from string import Template

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ai import PromptVersion

PROMPTS_ROOT = Path(__file__).resolve().parent
_FILE_RE = re.compile(r"^v(\d+)\.toml$")
REQUIRED_KEYS = ("agent", "version", "output_schema", "system", "user")


class PromptRegistryError(RuntimeError):
    """A prompt file is malformed, or was edited in place after being synced."""


@dataclass(frozen=True)
class PromptFile:
    agent: str
    version: int
    sha256: str
    body: str  # the exact file text stored in prompt_versions.body
    output_schema: str
    system: str
    user: str
    repair: str

    def render_user(self, **values: str) -> str:
        return Template(self.user).safe_substitute(**values)

    def render_repair(self, **values: str) -> str:
        return Template(self.repair).safe_substitute(**values)


def parse_prompt(
    raw: bytes, *, expected_agent: str | None = None, expected_version: int | None = None
) -> PromptFile:
    try:
        data = tomllib.loads(raw.decode("utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as exc:
        raise PromptRegistryError(f"prompt file is not valid TOML: {exc}") from exc
    missing = [k for k in REQUIRED_KEYS if k not in data]
    if missing:
        raise PromptRegistryError(f"prompt file is missing keys: {', '.join(missing)}")
    if not isinstance(data["version"], int) or data["version"] < 1:
        raise PromptRegistryError("prompt 'version' must be a positive integer")
    if expected_agent is not None and data["agent"] != expected_agent:
        raise PromptRegistryError(f"prompt agent {data['agent']!r} does not match folder {expected_agent!r}")
    if expected_version is not None and data["version"] != expected_version:
        raise PromptRegistryError(
            f"prompt version {data['version']} does not match file name v{expected_version}.toml"
        )
    return PromptFile(
        agent=data["agent"],
        version=data["version"],
        sha256=hashlib.sha256(raw).hexdigest(),
        body=raw.decode("utf-8"),
        output_schema=data["output_schema"],
        system=data["system"],
        user=data["user"],
        repair=data.get("repair", ""),
    )


def load_prompts(root: Path | None = None) -> list[PromptFile]:
    root = root or PROMPTS_ROOT
    found: list[PromptFile] = []
    for agent_dir in sorted(p for p in root.iterdir() if p.is_dir() and not p.name.startswith("__")):
        for path in sorted(agent_dir.glob("v*.toml")):
            match = _FILE_RE.match(path.name)
            if match is None:
                raise PromptRegistryError(f"prompt file {path.name!r} must be named v<N>.toml")
            found.append(
                parse_prompt(
                    path.read_bytes(), expected_agent=agent_dir.name, expected_version=int(match.group(1))
                )
            )
    return found


def sync_prompts(db: Session, root: Path | None = None) -> list[PromptVersion]:
    """Insert new prompt versions; raise when an existing one changed. Idempotent."""
    rows: list[PromptVersion] = []
    for prompt in load_prompts(root):
        row = db.scalar(
            select(PromptVersion).where(
                PromptVersion.agent == prompt.agent, PromptVersion.version == prompt.version
            )
        )
        if row is None:
            row = PromptVersion(
                agent=prompt.agent,
                version=prompt.version,
                content_sha256=prompt.sha256,
                body=prompt.body,
                output_schema=prompt.output_schema,
            )
            db.add(row)
            db.flush()
        elif row.content_sha256 != prompt.sha256:
            db.rollback()
            raise PromptRegistryError(
                f"Prompt {prompt.agent} v{prompt.version} was edited in place (hash mismatch). "
                f"Revert the edit and add v{prompt.version + 1}.toml instead (ADR-0017)."
            )
        rows.append(row)
    db.commit()
    return rows


def get_prompt(db: Session, agent: str, version: int | None = None) -> tuple[PromptFile, PromptVersion]:
    """The file-backed prompt (latest version by default) together with its synced DB row."""
    candidates = [p for p in load_prompts() if p.agent == agent and (version is None or p.version == version)]
    if not candidates:
        raise PromptRegistryError(f"No prompt registered for agent {agent!r}.")
    prompt = max(candidates, key=lambda p: p.version)
    row = db.scalar(
        select(PromptVersion).where(PromptVersion.agent == agent, PromptVersion.version == prompt.version)
    )
    if row is None or row.content_sha256 != prompt.sha256:
        raise PromptRegistryError(
            f"Prompt {agent} v{prompt.version} has not been synced; restart the service."
        )
    return prompt, row
