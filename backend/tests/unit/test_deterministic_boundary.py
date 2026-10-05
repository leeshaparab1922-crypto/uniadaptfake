"""AI-vs-deterministic boundary (`.claude/rules/deterministic-services.md`, plan "Conventions").

The deterministic services never import an LLM client, the agents, or the prompt registry, so no
LLM call can sit inside them. Checked statically (AST) and dynamically (a clean interpreter)."""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

import pytest

APP = Path(__file__).resolve().parents[2] / "app"
FORBIDDEN = (
    "langchain",
    "langchain_core",
    "langchain_anthropic",
    "langgraph",
    "anthropic",
    "openai",
    "app.agents",
    "app.prompts",
    "app.integrations.llm",
)

DETERMINISTIC_FILES = [
    "services/curriculum_graph.py",
    "services/curriculum_service.py",
    "services/curriculum_edit_service.py",
    "services/similarity_config_service.py",
    "services/ingestion_service.py",
    *sorted(
        str(p.relative_to(APP)).replace("\\", "/") for p in (APP / "services" / "ingestion").rglob("*.py")
    ),
]


def _imports(path: Path) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            found.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
            found.update(f"{node.module}.{a.name}" for a in node.names)
    return found


@pytest.mark.parametrize("relative", DETERMINISTIC_FILES)
def test_deterministic_module_has_no_llm_agent_or_prompt_imports(relative: str):
    bad = {
        name
        for name in _imports(APP / relative)
        if any(name == f or name.startswith(f + ".") for f in FORBIDDEN)
    }
    assert not bad, f"{relative} imports {sorted(bad)}"


def test_deterministic_services_load_without_pulling_in_llm_modules():
    code = (
        "import sys\n"
        "import app.services.curriculum_graph, app.services.curriculum_service, "
        "app.services.curriculum_edit_service, app.services.ingestion_service\n"
        "bad = [m for m in sys.modules if m.split('.')[0] in "
        "('langchain', 'langchain_core', 'langchain_anthropic', 'langgraph', 'anthropic', 'openai') "
        "or m.startswith(('app.agents', 'app.prompts', 'app.integrations.llm'))]\n"
        "print(','.join(bad))\n"
    )
    out = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, cwd=APP.parent, check=True
    ).stdout.strip()
    assert out == ""


def test_curriculum_graph_is_database_and_network_free():
    imports = _imports(APP / "services" / "curriculum_graph.py")
    assert not any(
        i.startswith(("sqlalchemy", "app.models", "app.db", "requests", "httpx", "socket")) for i in imports
    )
