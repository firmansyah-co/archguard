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
from archguard.core.updater import (
    ARCHGUARD_REPO_URL,
    perform_project_update,
    perform_self_update,
)
from archguard.templates.scaffold import (
    PRE_PUSH_HOOK_SCRIPT,
    WORKFLOW_TEMPLATE,
    scaffold_project,
)
from archguard.validators import (
    ALL_VALIDATORS,
    ComponentValidator,
    DataIntegrityValidator,
    GitTopologyValidator,
    LayerValidator,
    SpecValidator,
    TokenValidator,
    TopologyValidator,
    VersioningValidator,
    run_all_checks,
)
from archguard.versioning.engine import VersioningEngine, run_git_command

app = typer.Typer(
    name="archguard",
    help="Deterministic ISO/IEC/IEEE, W3C DTCG, and RFC software architecture governance engine.",
    add_completion=False,
)
hook_app = typer.Typer(help="Manage Git hook integrations.")
app.add_typer(hook_app, name="hook")

version_app = typer.Typer(help="Deterministic Git-derived version calculation and file synchronization.")
app.add_typer(version_app, name="version")

topology_app = typer.Typer(help="Dual-trunk dual-gate branch topology management.")
app.add_typer(topology_app, name="topology")

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


@version_app.callback(invoke_without_command=True)
def version_main(ctx: typer.Context) -> None:
    """Display ArchGuard version or manage deterministic versioning subcommands."""
    if ctx.invoked_subcommand is None:
        console.print(f"[bold cyan]ArchGuard Architecture Governance Engine[/bold cyan] v{__version__}")
        console.print("Author: Firmansyah Consulting & Enterprise Systems")
        console.print("Standards: ISO/IEC/IEEE 42010, ISO 29148, ISO 25010, SemVer 2.0.0, PEP 440, IEEE 828")


@version_app.command("compute")
def version_compute_cmd(
    target_dir: Path = typer.Option(Path("."), "--path", "-p", help="Target project root directory"),
    version_format: str = typer.Option("pep440", "--format", "-f", help="Version format: pep440 | semver"),
    branch: Optional[str] = typer.Option(None, "--branch", "-b", help="Branch name (defaults to active branch)"),
) -> None:
    """Calculate current deterministic version from Git history and print to stdout."""
    engine = VersioningEngine(root_dir=target_dir)
    ver = engine.compute_version(branch=branch, version_format=version_format)
    # Output raw computed version string for CLI piping / scripting
    console.print(ver)


@version_app.command("sync")
def version_sync_cmd(
    target_dir: Path = typer.Option(Path("."), "--path", "-p", help="Target project root directory"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show version changes without modifying files"),
) -> None:
    """Synchronize computed version across pyproject.toml, package.json, and __init__.py files."""
    engine = VersioningEngine(root_dir=target_dir)
    computed_ver = engine.compute_version()
    changes = engine.sync_version_files(dry_run=dry_run)

    if not changes:
        console.print(f"[bold green]✓ All version files are in sync with Git-derived version '{computed_ver}'.[/bold green]")
        return

    table = Table(title=f"Version Synchronization ({'[yellow]DRY RUN[/yellow]' if dry_run else '[green]APPLIED[/green]'})", header_style="bold cyan")
    table.add_column("File Path", style="bold")
    table.add_column("Previous Version", style="red")
    table.add_column("New Version", style="green")

    for path_str, (old_v, new_v) in changes.items():
        table.add_row(path_str, old_v, new_v)

    console.print(table)
    if dry_run:
        console.print("[yellow]Dry-run mode active. No files were modified.[/yellow]")
    else:
        console.print(f"[bold green]✓ Synchronized {len(changes)} files to version '{computed_ver}'.[/bold green]")


@topology_app.command("init")
def topology_init_cmd(
    target_dir: Path = typer.Option(Path("."), "--path", "-p", help="Target project root directory"),
    topology_type: str = typer.Option("production", "--type", "-t", help="Topology type: library | production"),
    create_dev: bool = typer.Option(False, "--create-dev", help="Create dev branch if missing"),
) -> None:
    """Initialize dual-trunk branch structure and protection configuration."""
    root = target_dir.resolve()
    console.print(f"[bold blue]Initializing {topology_type} Git topology in {root}...[/bold blue]")
    
    if create_dev or topology_type == "production":
        # Check if dev branch exists
        code, out, _ = run_git_command(["branch", "--list", "dev"], root)
        if code == 0 and not out:
            # Create dev branch from current HEAD
            c_dev, _, err = run_git_command(["branch", "dev"], root)
            if c_dev == 0:
                console.print("[bold green]✓ Created local integration branch 'dev'.[/bold green]")
            else:
                console.print(f"[yellow]Warning creating dev branch: {err}[/yellow]")
        else:
            console.print("[dim]Branch 'dev' already exists.[/dim]")

    console.print(f"[bold green]✓ Git topology initialized for '{topology_type}'.[/bold green]")


@topology_app.command("validate")
def topology_validate_cmd(
    target_dir: Path = typer.Option(Path("."), "--path", "-p", help="Target project root directory"),
) -> None:
    """Validate current repository topology and output structured JSON report."""
    root = target_dir.resolve()
    cfg = ArchGuardConfig.load(root / "archguard.yaml" if (root / "archguard.yaml").exists() else None)
    validator = GitTopologyValidator(root_dir=root, config=cfg)
    res = validator.validate()

    report = {
        "passed": res.passed,
        "standard": res.standard.value,
        "violations": [v.model_dump() for v in res.violations],
        "metadata": res.metadata,
    }
    import json
    console.print(json.dumps(report, indent=2))
    if not res.passed:
        raise typer.Exit(code=1)


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
    all_checks: bool = typer.Option(False, "--all", help="Run all standards checks"),
    tokens: bool = typer.Option(False, "--tokens", help="Run W3C DTCG token checks"),
    layers: bool = typer.Option(False, "--layers", help="Run ISO 42010 Layer architecture checks"),
    specs: bool = typer.Option(False, "--specs", help="Run ISO 29148 Living specification checks"),
    topology: bool = typer.Option(False, "--topology", help="Run ISO 12207 / IEEE 828 Repository & Git topology checks"),
    components: bool = typer.Option(False, "--components", help="Run ISO 25010 Component reusability checks"),
    integrity: bool = typer.Option(False, "--integrity", help="Run ISO 25010 Data integrity & zero-mock checks"),
    versioning: bool = typer.Option(False, "--versioning", help="Run SemVer 2.0.0 / IEEE 828 deterministic versioning checks"),
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
        selected_validators.extend([TopologyValidator, GitTopologyValidator])
    if components:
        selected_validators.append(ComponentValidator)
    if integrity:
        selected_validators.append(DataIntegrityValidator)
    if versioning:
        selected_validators.append(VersioningValidator)

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
    pre_push_file = hooks_dir / "pre-push"
    pre_push_file.write_text(PRE_PUSH_HOOK_SCRIPT, encoding="utf-8")
    pre_push_file.chmod(0o755)

    console.print(f"[bold green]✓ ArchGuard pre-push hook installed into {pre_push_file}[/bold green]")


@app.command("ci-gen")
def ci_gen_cmd(
    output_dir: Path = typer.Option(Path(".github/workflows"), "--out", help="Workflow output directory"),
) -> None:
    """Generate ready-to-use GitHub Actions workflow files for ArchGuard governance."""
    output_dir.mkdir(parents=True, exist_ok=True)
    workflow_path = output_dir / "archguard-governance.yml"
    workflow_path.write_text(WORKFLOW_TEMPLATE, encoding="utf-8")
    console.print(f"[bold green]✓ Generated GitHub Actions workflow: {workflow_path}[/bold green]")


@app.command("update")
def update_cmd(
    self_upgrade: bool = typer.Option(False, "--self", "-s", help="Self-upgrade ArchGuard CLI & sync Hermes skill"),
    project_update: bool = typer.Option(False, "--project", "-p", help="Update project CI workflows, Git hooks & config"),
    target_dir: Path = typer.Option(Path("."), "--target", "-t", help="Target project directory for asset update"),
    repo_path: Optional[Path] = typer.Option(None, "--repo", help="Custom local ArchGuard repository path for self-upgrade"),
) -> None:
    """
    Self-upgrade ArchGuard engine, synchronize Hermes skills, and refresh project CI/hook assets.
    """
    # If neither flag is passed, execute both or determine context
    run_self = self_upgrade
    run_proj = project_update

    if not run_self and not run_proj:
        # Default behavior: run self-update, and also project update if inside a git/archguard project
        run_self = True
        is_project = (target_dir / "archguard.yaml").exists() or (target_dir / ".git").exists()
        if is_project:
            run_proj = True

    console.print(
        Panel(
            f"[bold cyan]ArchGuard Architecture Governance Engine Updater[/bold cyan]\n"
            f"[dim]Version: {__version__} | Upstream: {ARCHGUARD_REPO_URL}[/dim]",
            title="ArchGuard Maintenance & Update",
            border_style="cyan",
        )
    )

    success = True

    # 1. Self Upgrade
    if run_self:
        console.print("\n[bold blue]▶ [1/2] Upgrading ArchGuard Core Engine & Hermes Skill...[/bold blue]")
        res_self = perform_self_update(repo_path=repo_path)
        
        self_table = Table(title="ArchGuard Self-Upgrade Summary", header_style="bold cyan")
        self_table.add_column("Component", style="bold")
        self_table.add_column("Status", justify="center")
        self_table.add_column("Details", style="dim")

        if res_self["method"] == "local_git":
            git_status = "[bold green]PULLED[/bold green]" if res_self["git_pulled"] else "[yellow]UNCHANGED/FAILED[/yellow]"
            self_table.add_row("Git Repository", git_status, res_self.get("commit_info") or res_self["repo_path"])
        else:
            self_table.add_row("Git Remote", "[cyan]REMOTE[/cyan]", ARCHGUARD_REPO_URL)

        pip_status = "[bold green]INSTALLED[/bold green]" if res_self["pip_upgraded"] else "[bold red]FAILED[/bold red]"
        self_table.add_row("Python Package", pip_status, f"pip install ({res_self['method']})")

        skill_status = "[bold green]SYNCED[/bold green]" if res_self["skill_synced"] else "[yellow]SKIPPED/NOT FOUND[/yellow]"
        self_table.add_row("Hermes Skill Symlink", skill_status, res_self["skill_path"])

        console.print(self_table)

        if not res_self["success"]:
            success = False
            for err in res_self.get("errors", []):
                console.print(f"  [bold red]✗ {err}[/bold red]")

    # 2. Project Update
    if run_proj:
        step_num = "2/2" if run_self else "1/1"
        console.print(f"\n[bold blue]▶ [{step_num}] Refreshing Project CI/CD & Governance Assets in {target_dir.resolve()}...[/bold blue]")
        res_proj = perform_project_update(target_dir=target_dir)

        proj_table = Table(title="Project Asset Synchronization Matrix", header_style="bold cyan")
        proj_table.add_column("Asset", style="bold")
        proj_table.add_column("Status", justify="center")
        proj_table.add_column("Target Path", style="dim")

        wf_status = "[bold green]UPDATED[/bold green]" if res_proj["workflow_updated"] else "[bold red]FAILED[/bold red]"
        proj_table.add_row("GitHub Workflow", wf_status, res_proj["workflow_path"])

        if res_proj["hook_skipped"]:
            hook_status = "[yellow]SKIPPED (no .git)[/yellow]"
        elif res_proj["hook_updated"]:
            hook_status = "[bold green]INSTALLED[/bold green]"
        else:
            hook_status = "[bold red]FAILED[/bold red]"
        proj_table.add_row("Git Pre-Push Hook", hook_status, res_proj["hook_path"] or "N/A")

        cfg_status = f"[bold green]{res_proj['config_status'].upper()}[/bold green]" if res_proj["config_status"] else "[bold red]FAILED[/bold red]"
        proj_table.add_row("ArchGuard Config", cfg_status, res_proj["config_path"])

        console.print(proj_table)

        if not res_proj["success"]:
            success = False
            for err in res_proj.get("errors", []):
                console.print(f"  [bold red]✗ {err}[/bold red]")

    # Final Outcome Banner
    if success:
        console.print(
            Panel(
                "[bold green]✓ ArchGuard update completed successfully![/bold green]\n"
                "Engine, skills, and project assets are fully aligned with latest standards.",
                title="Update Complete",
                border_style="green",
            )
        )
    else:
        console.print(
            Panel(
                "[bold red]✗ ArchGuard update completed with errors.[/bold red]\n"
                "Review the diagnostic matrix above for remediation steps.",
                title="Update Warnings/Errors",
                border_style="red",
            )
        )
        raise typer.Exit(code=1)



if __name__ == "__main__":
    app()
