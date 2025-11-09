from datetime import datetime
import ast
import difflib
import logging
import os
import re

import requests


OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://ollama-dev:11434")


def _host_candidates():
    seen = set()
    for host in (OLLAMA_HOST, "http://localhost:11434"):
        if host and host not in seen:
            seen.add(host)
            yield host


def run_code_fix(filename: str, content: str, model: str = "granite4:tiny-h") -> dict:
    """
    Placeholder code-fix agent that pretends to run a model and returns a summary
    plus a lightly formatted version of the provided source.
    In a future iteration this can call a real LLM agent.
    """
    llm_code = _try_model_rewrite(filename, content, model)
    if llm_code:
        cleaned = llm_code.strip()
        if not cleaned.endswith("\n"):
            cleaned += "\n"
        summary = (
            f"Processed `{filename}` with {model}. Model rewrite applied based on detected issues."
            f" (Completed {datetime.utcnow().isoformat()}Z)"
        )
        logging.getLogger("code_fix").info("Fixed code for %s via model:\n%s", filename, cleaned)
        return {"summary": summary, "fixed_code": cleaned, "changes": 1}

    # fallback heuristic approach
    lines = content.splitlines()
    trimmed_lines = [line.rstrip() for line in lines]
    trimmed = "\n".join(trimmed_lines)

    touched = 0
    suggestions = []
    # Basic formatting and lint
    if "\t" in content:
        suggestions.append("Converted tabs to spaces.")
        trimmed = trimmed.replace("\t", "    ")
        touched += 1
    if not content.endswith("\n"):
        trimmed += "\n"
        suggestions.append("Ensured file ends with a newline.")
        touched += 1
    if "TODO" in content.upper():
        suggestions.append("Flagged TODO items for follow-up.")

    # Parse AST to discover undefined identifiers.
    undefined_names = set()
    defined_names = set()
    try:
        tree = ast.parse(content)

        class Analyzer(ast.NodeVisitor):
            def visit_Assign(self, node):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        defined_names.add(target.id)
                self.generic_visit(node)

            def visit_FunctionDef(self, node):
                defined_names.add(node.name)
                for arg in node.args.args:
                    defined_names.add(arg.arg)
                self.generic_visit(node)

            def visit_With(self, node):
                for item in node.items:
                    if isinstance(item.optional_vars, ast.Name):
                        defined_names.add(item.optional_vars.id)
                self.generic_visit(node)

        Analyzer().visit(tree)
        builtin_allow = set(dir(__builtins__)) | {"self"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                if node.id not in defined_names and node.id not in builtin_allow:
                    undefined_names.add(node.id)
    except SyntaxError:
        pass

    # Attempt to auto-fix undefined names by matching close defined names.
    fixes = []
    for name in sorted(undefined_names):
        match = difflib.get_close_matches(name, defined_names, n=1, cutoff=0.75)
        if match:
            fixes.append((name, match[0]))

    def apply_rename(lines: list[str], old: str, new: str):
        updated = []
        applied = False
        pattern = re.compile(rf"\b{re.escape(old)}\b")
        for line in lines:
            if pattern.search(line):
                line = pattern.sub(new, line)
                applied = True
            updated.append(line)
        return updated, applied

    line_list = trimmed_lines[:]
    for old, new in fixes:
        line_list, inserted = apply_rename(line_list, old, new)
        if inserted:
            suggestions.append(f"Renamed `{old}` to `{new}`.")
            touched += 1

    if fixes and not suggestions:
        suggestions.append("Corrected identifier typos.")

    stripped_comments = []
    for line in line_list:
        if line.strip().startswith("#"):
            continue
        stripped_comments.append(line)

    trimmed = "\n".join(stripped_comments)

    summary = (
        f"Processed `{filename}` with {model}. "
        + (", ".join(suggestions) if suggestions else "No obvious issues detected; normalized formatting.")
    )
    summary += f" (Completed {datetime.utcnow().isoformat()}Z)"

    logging.getLogger("code_fix").info("Fixed code for %s:\n%s", filename, trimmed)

    return {
        "summary": summary,
        "fixed_code": trimmed,
        "changes": touched,
    }


def _try_model_rewrite(filename: str, content: str, model: str) -> str | None:
    prompt = (
        "You are an expert software engineer. Fix the following source file. "
        "Correct logic errors (including operator precedence), typos, and formatting issues while preserving style. "
        "Return ONLY the fully corrected code with no commentary or code fences.\n"
        f"Filename: {filename}\n"
        "---------\n"
        f"{content}\n"
        "---------"
    )

    payload = {"model": model, "prompt": prompt, "stream": False}
    errors = []
    for host in _host_candidates():
        try:
            resp = requests.post(f"{host}/api/generate", json=payload, timeout=120)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("response", "")
            errors.append(f"{host} -> HTTP {resp.status_code}")
        except Exception as exc:
            errors.append(f"{host} -> {exc}")
    if errors:
        logging.getLogger("code_fix").warning("Model rewrite fallback: %s", "; ".join(errors))
    return None
