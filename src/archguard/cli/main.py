"""
ArchGuard CLI Application.
Deterministic ISO/IEC/IEEE, W3C DTCG, and RFC software architecture governance.
"""

from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from archguard import __version__
from archguard.core.config import ArchGuardConfig
from archguard.core.models import Severity, SuiteResult
from archguard.templates.scaffold import scaffold_project
from archguard.validators import (
    ALL_VALIDATORS,
    ComponentValidator,
    LayerValidator,
    SpecValidator,
    TokenValidator,
    TopologyValidator,
    run_all_checks,
)

app = typer.Typer(
    name="archguard",
    help="Deterministic ISO/IEC/IEEE, W3C DTCG, and RFC software architecture governance engine.",
    add_completion=False,
)
hook_app = typer.Typer(help="Manage Git hook integrations.")
app.add_typer(hook_app, name="hook")

console = Console()


def render_suite_result(result: SuiteResult) -> None:
    """Render check results to terminal with rich tables and diagnostics."""
    table = Table(title="ArchGuard Governance Audit Matrix", header_style="bold cyan")
    table.add_column("Validator", style="bold")
    table.add_column("Standard", style="magenta")
    table.add_column("Status", justify="center")
    table.add_column("Violations", justify="right")
    table.add_column("Scanned Files", justify="right")

    for res in result.results:
        status_str = "[bold green]PASSED[/bold green]" if res.passed else "[bold red]FAILED[/bold red]"
        err_count = len([v for v in res.violations if v.severity == Severity.ERROR])
        warn_count = len([v for v in res.violations if v.severity == Severity.WARNING])
        viol_str = f"[red]{err_count} err[/red], [yellow]{warn_count} warn[/yellow]"
        table.add_row(
            res.validator_name,
            res.standard.value,
            status_str,
            viol_str,
            str(res.checked_files_count),
        )

    console.print(table)

    # Print Detailed Violations if any
    if result.total_violations > 0:
        console.print("\n[bold red]Detailed Governance Violations:[/bold red]")
        for res in result.results:
            for v in res.violations:
                sev_color = "red" if v.severity == Severity.ERROR else "yellow"
                loc = f"{v.file_path}:{v.line_number}" if v.line_number else v.file_path
                console.print(f"\n  • [{sev_color} bold][{v.rule_id}] [{v.severity.value.upper()}][/{sev_color} bold] [dim]{loc}[/dim]")
                console.print(f"    [white]{v.message}[/white]")
                if v.context_snippet:
                    console.print(f"    [dim]Snippet: {v.context_snippet}[/dim]")
                if v.remediation_hint:
                    console.print(f"    [cyan]Remediation: {v.remediation_hint}[/cyan]")

    # Print Summary Panel
    if result.passed:
        console.print(
            Panel(
                f"[bold green]✓ ZERO GOVERNANCE VIOLATIONS DETECTED[/bold green]\n"
                f"Scanned {result.total_files_checked} files across ISO/W3C/RFC standards.",
                title="ArchGuard Summary",
                border_style="green",
            )
        )
    else:
        console.print(
            Panel(
                f"[bold red]✗ GOVERNANCE GATE FAILED[/bold red]\n"
                f"Found [bold]{result.total_errors}[/bold] blocking errors and [bold]{result.total_warnings}[/bold] warnings.\n"
                f"Total files audited: {result.total_files_checked}",
                title="ArchGuard Summary",
                border_style="red",
            )
        )


@app.command("version")
def version_cmd() -> None:
    """Display ArchGuard version and metadata."""
    console.print(f"[bold cyan]ArchGuard Architecture Governance Engine[/bold cyan] v{__version__}")
    console.print("Author: Firmansyah Consulting & Enterprise Systems")
    console.print("Standards: ISO/IEC/IEEE 42010, ISO 29148, ISO 25010, W3C DTCG, RFC 7807")


@app.command("init")
def init_cmd(
    target_dir: Path = typer.Option(Path("."), "--target", "-t", help="Target project directory"),
    project_type: str = typer.Option(
        "fullstack", "--type", help="Topology type: fullstack | react-fastapi | scada | library | backend-only"
    ),
) -> None:
    """Scaffold complete ISO/W3C compliant folder topology, templates, and configs."""
    console.print(f"[bold blue]Scaffolding ArchGuard project topology ({project_type}) in {target_dir.resolve()}...[/bold blue]")
    try:
        scaffold_project(target_dir, project_type=project_type)
        console.print("[bold green]✓ ArchGuard topology initialized successfully.[/bold green]")
        console.print("Run [bold cyan]archguard check --all[/bold cyan] to verify compliance.")
    except Exception as e:
        console.print(f"[bold red]Error scaffolding project: {str(e)}[/bold red]")
        raise typer.Exit(code=1)


@app.command("check")
def check_cmd(
    path: Path = typer.Option(Path("."), "--path", "-p", help="Root directory of the project to check"),
    all_checks: bool = typer.Option(True, "--all", help="Run all standards checks"),
    tokens: bool = typer.Option(False, "--tokens", help="Run W3C DTCG token checks"),
    layers: bool = typer.Option(False, "--layers", help="Run ISO 42010 Layer architecture checks"),
    specs: bool = typer.Option(False, "--specs", help="Run ISO 29148 Living specification checks"),
    topology: bool = typer.Option(False, "--topology", help="Run ISO 12207 Repository hygiene checks"),
    components: bool = typer.Option(False, "--components", help="Run ISO 25010 Component reusability checks"),
) -> None:
    """Run deterministic static AST & standards validation engine."""
    root = path.resolve()
    cfg = ArchGuardConfig.load(root / "archguard.yaml" if (root / "archguard.yaml").exists() else None)

    # Select validators
    selected_validators = []
    if tokens:
        selected_validators.append(TokenValidator)
    if layers:
        selected_validators.append(LayerValidator)
    if specs:
        selected_validators.append(SpecValidator)
    if topology:
        selected_validators.append(TopologyValidator)
    if components:
        selected_validators.append(ComponentValidator)

    if not selected_validators or all_checks:
        selected_validators = ALL_VALIDATORS

    suite = run_all_checks(root_dir=root, config=cfg, validators=selected_validators)
    render_suite_result(suite)

    if not suite.passed:
        raise typer.Exit(code=1)


@hook_app.command("install")
def hook_install(
    git_dir: Path = typer.Option(Path(".git"), "--git-dir", help="Path to .git directory"),
) -> None:
    """Install pre-commit and pre-push hooks into .git/hooks/."""
    hooks_dir = git_dir / "hooks"
    if not git_dir.exists():
        console.print(f"[bold red]Error: '{git_dir}' not found. Are you inside a Git repository?[/bold red]")
        raise typer.Exit(code=1)

    hooks_dir.mkdir(parents=True, exist_ok=True)

    pre_push_script = """#!/usr/bin/env bash
# ArchGuard Automated Pre-Push Governance Gate
echo "===> [ArchGuard] Running deterministic architecture governance checks..."
if command -v archguard >/dev/null 2>&1; then
    archguard check --all
    exit $?
elif command -v uv >/dev/null 2>&1; then
    uv run archguard check --all
    exit $?
elif command -v python3 >/dev/null 2>&1; then
    python3 -m archguard.cli.main check --all
    exit $?
else
    echo "Warning: archguard executable not found in PATH. Skipping hook."
    exit 0
fi
"""
    pre_push_file = hooks_dir / "pre-push"
    pre_push_file.write_text(pre_push_script, encoding="utf-8")
    pre_push_file.chmod(0o755)

    console.print(f"[bold green]✓ ArchGuard pre-push hook installed into {pre_push_file}[/bold green]")


@app.command("ci-gen")
def ci_gen_cmd(
    output_dir: Path = typer.Option(Path(".github/workflows"), "--out", help="Workflow output directory"),
) -> None:
    """Generate ready-to-use GitHub Actions workflow files for ArchGuard governance."""
    output_dir.mkdir(parents=True, exist_ok=True)
    workflow_path = output_dir / "archguard-governance.yml"

    content = """name: ArchGuard Architecture Governance Gate

on:
  push:
    branches: [ main, dev ]
  pull_request:
    branches: [ main, dev ]

jobs:
  archguard-audit:
    name: ISO & W3C Standards Validation
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Source Code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install ArchGuard
        run: |
          pip install uv
          uv pip install --system . || uv pip install --system archguard

      - name: Run Deterministic ArchGuard Gate
        run: |
          archguard check --all
"""
    workflow_path.write_text(content, encoding="utf-8")
    console.print(f"[bold green]✓ Generated GitHub Actions workflow: {workflow_path}[/bold green]")


if __name__ == "__main__":
    app()
