import json
import sys
from pathlib import Path
from typing import Dict, Optional, Any

# Force UTF-8 output on Windows so that § and other legal symbols render correctly.
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    except (AttributeError, OSError):
        pass

import click
from rich.console import Console
from rich.panel import Panel

from annex4 import __version__
from annex4.classifier.engine import ClassifierEngine
from annex4.cli.disclaimer import (
    print_cli_disclaimer,
    FULL_DISCLAIMER,
    DisclaimerRequiredError,
)
from annex4.regulation.loader import RegulationLoader, get_regulation_loader
from annex4.regulation.search import search_regulation


class _AnnexGroup(click.Group):
    """Custom group that prints the short disclaimer to STDERR before every subcommand."""

    def invoke(self, ctx: click.Context) -> object:
        if ctx.invoked_subcommand is not None:
            print_cli_disclaimer()
        return super().invoke(ctx)


@click.group(cls=_AnnexGroup)
@click.version_option(version=__version__)
def cli() -> None:
    """
    annex4-cli: EU AI Act Technical Documentation Generator.

    This tool helps AI providers navigate the EU AI Act by classifying their
    systems and generating technical documentation as per Annex IV.
    """
    pass


@cli.command(name="legal")
def legal_command() -> None:
    """Print the full legal disclaimer and licence notice."""
    console = Console()
    try:
        loader = RegulationLoader()
        reg_version = loader.version
    except Exception:
        reg_version = "2024-1689_base"

    console.print(
        Panel(
            FULL_DISCLAIMER,
            title="annex4-cli — Legal Disclaimer",
            border_style="yellow",
        )
    )
    console.print()
    console.print(f"[bold]Tool version:[/bold] annex4-cli v{__version__}")
    console.print(f"[bold]Regulation pack:[/bold] {reg_version}")
    console.print("[bold]Licence:[/bold] Apache-2.0")
    console.print("[bold]Full legal notice:[/bold] see LEGAL.md in the repository")


@cli.command()
@click.option(
    "--output",
    "-o",
    "output_path",
    type=click.Path(path_type=Path, dir_okay=False, writable=True),
    help="Path to save the RiskProfile JSON.",
)
@click.option(
    "--regulation-version",
    help="Regulation version ID to use.",
    default="2024-1689_base",
    show_default=True,
)
@click.option(
    "--i-acknowledge-uncertainty",
    "acknowledged",
    is_flag=True,
    default=False,
    help="Required flag: confirms you understand this output is not a legal determination.",
)
@click.option(
    "--system",
    "system_yaml",
    type=click.Path(exists=True, path_type=Path, dir_okay=False),
    default=None,
    help="Path to an existing dossier YAML — enables non-interactive classification.",
)
def classify(
    output_path: Optional[Path],
    regulation_version: str,
    acknowledged: bool,
    system_yaml: Optional[Path],
) -> None:
    """Classify your AI system's risk level under the EU AI Act.

    \b
    Requires --i-acknowledge-uncertainty to proceed.
    Use --system dossier.yaml for non-interactive mode.
    """
    import sys as _sys

    console = Console()

    if not acknowledged:
        console.print(
            Panel(
                "[bold yellow]Acknowledgement required[/bold yellow]\n\n"
                "The classification produced by this tool is [bold]not a legal determination[/bold].\n"
                "Re-run with [bold cyan]--i-acknowledge-uncertainty[/bold cyan] to proceed.",
                border_style="yellow",
                title="annex4 classify",
            )
        )
        _sys.exit(2)

    try:
        loader = get_regulation_loader(regulation_version)
        spec = loader.load_classifier_spec()
    except FileNotFoundError as e:
        Console().print(f"[bold red]Error:[/bold red] {e}")
        raise click.Abort()

    engine = ClassifierEngine(spec, console)
    if system_yaml:
        console.print(
            f"[dim]Reading system from {system_yaml} (non-interactive mode)…[/dim]"
        )
        profile = engine.classify_from_yaml(system_yaml)
    else:
        console.print(
            Panel(
                "[bold]EU AI Act Risk Classifier[/bold]\n\nAnswer the following questions to determine the risk profile of your AI system.\nYour answers are processed locally — nothing is transmitted.",
                title="Classification",
                border_style="green",
            )
        )
        profile = engine.run()

    console.print("\n" + "─" * 60)
    console.print("[bold green]Risk Classification Profile[/bold green]")
    console.print("─" * 60)
    console.print(f"[bold]Path ID:[/bold]  {profile.path_id}")
    console.print(f"[bold]Citation:[/bold] {profile.citation}")
    console.print()
    for art in profile.articles:
        console.print(f"  • {art}")
    console.print()
    console.print(f"[bold]Conformity route:[/bold] {profile.conformity_route}")
    nb_text = (
        "[bold red]Yes[/bold red]"
        if profile.notified_body_required
        else "[green]No (by default)[/green]"
    )
    console.print(f"[bold]Notified Body required:[/bold] {nb_text}")
    console.print()
    console.print("[bold]Explanation:[/bold]")
    console.print(profile.explanation_markdown.strip())
    console.print()
    console.print("[bold]Next steps:[/bold]")
    console.print(profile.next_steps.strip())
    console.print()
    console.print(
        Panel(
            f"[dim]{profile.disclaimer}[/dim]",
            border_style="yellow",
            title="⚠  Not legal advice",
        )
    )

    if output_path:
        result_data = {
            "risk_profile": profile.model_dump(),
            "answers": {
                k: list(v) if isinstance(v, set) else v
                for k, v in engine.answers.items()
            },
            "regulation_version": regulation_version,
        }
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(result_data, f, indent=2)
        console.print(f"\n[dim]Risk profile saved to {output_path}[/dim]")


@cli.command()
@click.argument(
    "classification_file", type=click.Path(exists=True, path_type=Path, dir_okay=False)
)
@click.option(
    "--output",
    "-o",
    "output_path",
    type=click.Path(path_type=Path, dir_okay=False, writable=True),
    required=True,
)
@click.option("--template", default="annex_iv.md.j2", show_default=True)
@click.option(
    "--overrides",
    "override_paths",
    type=click.Path(exists=True, path_type=Path, dir_okay=False),
    multiple=True,
)
def generate(
    classification_file: Path,
    output_path: Path,
    template: str,
    override_paths: tuple[Path, ...],
) -> None:
    """Generate technical documentation from a classification result file."""
    from annex4.generator.engine import GeneratorEngine

    console = Console()
    try:
        engine = GeneratorEngine()
        output_path.write_text(
            engine.render(classification_file, template, list(override_paths)),
            encoding="utf-8",
        )
        console.print(
            f"[bold green]Success![/bold green] Documentation generated at [cyan]{output_path.resolve()}[/cyan]"
        )
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise e


def _print_validation_report(console: Console, report: Any) -> None:
    from annex4.core.validate import Level

    level_style = {
        Level.ERROR: "bold red",
        Level.LEGAL_GAP: "bold magenta",
        Level.INCONSISTENCY: "bold yellow",
        Level.WARNING: "yellow",
        Level.ASSUMPTION: "dim yellow",
        Level.INFO: "dim cyan",
    }
    level_label = {
        Level.ERROR: "ERROR  ",
        Level.LEGAL_GAP: "LGL_GAP",
        Level.INCONSISTENCY: "INCONSIST",
        Level.WARNING: "WARNING",
        Level.ASSUMPTION: "ASSUMPT",
        Level.INFO: "INFO   ",
    }
    if not report.issues:
        console.print("[bold green]✓ Validation passed — no issues found.[/bold green]")
        return
    console.print("[bold]Validation report[/bold]")
    console.print("-" * 72)
    for issue in report.issues:
        style = level_style[issue.level]
        ref = f"  [dim]{issue.article}[/dim]" if issue.article else ""
        console.print(
            f"[{style}]{level_label[issue.level]}[/{style}]  [{style}]{issue.code}[/{style}]{ref}"
        )
        console.print(f"         [dim]{issue.field}[/dim]")
        console.print(f"         {issue.message}")
        console.print()
    e, w, i = len(report.errors), len(report.warnings), len(report.infos)
    summary_style = "bold red" if e else ("yellow" if w else "green")
    console.print("-" * 72)
    console.print(
        f"[{summary_style}]{e} error(s)[/{summary_style}]  [yellow]{w} warning(s)[/yellow]  [dim cyan]{i} info[/dim cyan]"
    )


@cli.command(name="validate")
@click.argument(
    "dossier_file", type=click.Path(exists=True, path_type=Path, dir_okay=False)
)
@click.option(
    "--strict",
    is_flag=True,
    default=False,
    help="Exit with code 1 if there are any warnings (not just errors).",
)
def validate_dossier(dossier_file: Path, strict: bool) -> None:
    """Check a dossier YAML for Annex IV completeness."""
    import sys
    import yaml
    from annex4.core.schema import AnnexIVDossier
    from annex4.core.validate import validate as run_validate

    console = Console()
    try:
        dossier = AnnexIVDossier.from_yaml_dict(
            yaml.safe_load(open(dossier_file, encoding="utf-8")) or {}
        )
    except Exception as e:
        console.print(f"[bold red]Failed to load dossier:[/bold red] {e}")
        sys.exit(1)
    report = run_validate(dossier)
    _print_validation_report(console, report)
    if not report.is_valid or (strict and report.warnings):
        sys.exit(1)


@cli.command()
@click.argument(
    "dossier_file", type=click.Path(exists=True, path_type=Path, dir_okay=False)
)
@click.option(
    "--output",
    "-o",
    "output_path",
    type=click.Path(path_type=Path, dir_okay=False, writable=True),
    required=True,
    help="Path to save the generated document.",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["markdown", "html", "pdf"], case_sensitive=False),
    default=None,
    help="Output format. Inferred from --output extension if not specified.",
)
@click.option(
    "--no-disclaimer",
    "no_disclaimer",
    is_flag=True,
    default=False,
    hidden=True,
    help="[BLOCKED] The disclaimer cannot be disabled.",
)
def render(
    dossier_file: Path, output_path: Path, fmt: Optional[str], no_disclaimer: bool
) -> None:
    """Generate a complete Annex IV document from a filled dossier YAML file."""
    if no_disclaimer:
        raise DisclaimerRequiredError(
            "The disclaimer cannot be disabled. All annex4-cli outputs must carry the mandatory legal disclaimer."
        )

    import yaml
    from annex4.core.schema import AnnexIVDossier
    from annex4.core.validate import validate as run_validate
    from annex4.generator.engine import GeneratorEngine

    console = Console()
    if fmt is None:
        suffix = output_path.suffix.lower()
        fmt = {".html": "html", ".pdf": "pdf", ".md": "markdown"}.get(
            suffix, "markdown"
        )

    try:
        dossier = AnnexIVDossier.from_yaml_dict(
            yaml.safe_load(open(dossier_file, encoding="utf-8")) or {}
        )
        report = run_validate(dossier)
        _print_validation_report(console, report)
        if not report.is_valid:
            console.print(
                f"\n[bold red]Render aborted:[/bold red] resolve the {len(report.errors)} error(s) above before generating the document."
            )
            raise click.Abort()
        if report.warnings:
            console.print(
                f"[yellow]Continuing with {len(report.warnings)} warning(s) — the document will be generated but may be incomplete.[/yellow]\n"
            )
        if fmt == "html":
            from annex4.render.html import render_html

            output_path.write_text(render_html(dossier), encoding="utf-8")
        elif fmt == "pdf":
            from annex4.render.pdf import render_pdf

            render_pdf(dossier, output_path)
        else:
            output_path.write_text(
                GeneratorEngine().render_dossier(dossier_file), encoding="utf-8"
            )
        console.print(
            f"[bold green]Success![/bold green] Annex IV document ({fmt}) generated at [cyan]{output_path.resolve()}[/cyan]"
        )
    except click.Abort:
        raise
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise click.Abort()


@cli.command(name="ingest")
@click.option("--mlflow-run", "mlflow_run_id", default=None)
@click.option("--mlflow-uri", "mlflow_uri", default=None)
@click.option("--hf-model", "hf_model_id", default=None)
@click.option("--hf-token", "hf_token", default=None, envvar="HF_TOKEN")
@click.option(
    "--override",
    "override_paths",
    type=click.Path(exists=True, path_type=Path, dir_okay=False),
    multiple=True,
)
@click.option(
    "--output",
    "-o",
    "output_path",
    type=click.Path(path_type=Path, dir_okay=False, writable=True),
    default="dossier.yaml",
    show_default=True,
)
def ingest(
    mlflow_run_id: Optional[str],
    mlflow_uri: Optional[str],
    hf_model_id: Optional[str],
    hf_token: Optional[str],
    override_paths: tuple[Path, ...],
    output_path: Path,
) -> None:
    """Pull metadata from ML platforms and merge into a dossier YAML."""
    import sys
    import yaml
    from annex4.core.merge import merge_ingestor_outputs

    console = Console()

    if not mlflow_run_id and not hf_model_id and not override_paths:
        console.print(
            "[bold red]Error:[/bold red] Specify at least one source: --mlflow-run, --hf-model, or --override."
        )
        sys.exit(1)

    outputs = []
    if mlflow_run_id:
        try:
            from annex4.ingestors.mlflow_ingestor import MLflowIngestor

            console.print(f"[dim]Ingesting MLflow run {mlflow_run_id}…[/dim]")
            outputs.append(
                MLflowIngestor(tracking_uri=mlflow_uri).ingest(run_id=mlflow_run_id)
            )
            console.print("[green]✓[/green] MLflow run ingested.")
        except ImportError as e:
            console.print(f"[bold red]MLflow error:[/bold red] {e}")
            sys.exit(1)
        except Exception as e:
            console.print(f"[bold red]MLflow ingestion failed:[/bold red] {e}")
            sys.exit(1)

    if hf_model_id:
        try:
            from annex4.ingestors.hf_ingestor import HuggingFaceIngestor

            console.print(f"[dim]Ingesting HuggingFace model {hf_model_id}…[/dim]")
            outputs.append(
                HuggingFaceIngestor().ingest(model_id=hf_model_id, token=hf_token)
            )
            console.print("[green]✓[/green] HuggingFace model ingested.")
        except ImportError as e:
            console.print(f"[bold red]HuggingFace error:[/bold red] {e}")
            sys.exit(1)
        except Exception as e:
            console.print(f"[bold red]HuggingFace ingestion failed:[/bold red] {e}")
            sys.exit(1)

    for path in override_paths:
        from annex4.ingestors.yaml_override import YAMLOverrideIngestor

        console.print(f"[dim]Applying override {path}…[/dim]")
        outputs.append(YAMLOverrideIngestor().ingest(path=path))
        console.print(f"[green]✓[/green] Override {Path(path).name} applied.")

    base: Dict[str, Any] = {}
    if output_path.exists():
        with open(output_path, encoding="utf-8") as f:
            base = yaml.safe_load(f) or {}
        console.print(f"[dim]Merging into existing {output_path.name}…[/dim]")

    merged = merge_ingestor_outputs(outputs, base=base)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        yaml.dump(
            merged, f, allow_unicode=True, sort_keys=False, default_flow_style=False
        )
    console.print(
        f"\n[bold green]Done.[/bold green] Dossier written to [cyan]{output_path.resolve()}[/cyan] ({len(outputs)} source(s) merged)."
    )


@cli.command()
@click.argument(
    "old_file", type=click.Path(exists=True, path_type=Path, dir_okay=False)
)
@click.argument(
    "new_file", type=click.Path(exists=True, path_type=Path, dir_okay=False)
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["cli", "json", "markdown", "html"]),
    default="cli",
)
@click.option(
    "--output",
    "-o",
    "output_path",
    type=click.Path(path_type=Path, dir_okay=False, writable=True),
    default=None,
    help="Write report to file instead of stdout.",
)
def diff(old_file: Path, new_file: Path, fmt: str, output_path: Optional[Path]) -> None:
    """Compare two dossier YAML files and report material changes."""
    import yaml
    from annex4.core.schema import AnnexIVDossier
    from annex4.core.diff import diff_dossiers, _field_str
    from jinja2 import Environment, FileSystemLoader

    console = Console()
    try:
        old_raw = yaml.safe_load(old_file.read_text(encoding="utf-8")) or {}
        new_raw = yaml.safe_load(new_file.read_text(encoding="utf-8")) or {}
    except Exception as e:
        console.print(f"[bold red]Failed to load dossiers:[/bold red] {e}")
        sys.exit(1)
    old_dossier = AnnexIVDossier.from_yaml_dict(old_raw)
    new_dossier = AnnexIVDossier.from_yaml_dict(new_raw)
    reg_version = (
        _field_str(old_dossier.general_description.system.regulation_version)
        or "2024-1689_base"
    )
    substantiality_map = get_regulation_loader(reg_version).load_diff_substantiality()
    report = diff_dossiers(old_dossier, new_dossier, substantiality_map)
    if fmt == "cli":
        if report.regulation_version_changed:
            console.print(
                Panel(
                    "[bold yellow]Regulation version changed between dossiers![/bold yellow]"
                )
            )
        if not report.entries:
            console.print("[dim]No changes detected.[/dim]")
        else:
            from rich.table import Table

            table = Table(title="Dossier Diff Report")
            table.add_column("Path", style="cyan")
            table.add_column("Kind", style="blue")
            table.add_column("Substantiality", style="bold")
            table.add_column("New Value", style="green")
            for entry in report.entries:
                sub_style = (
                    "red"
                    if entry.substantiality == "substantial"
                    else ("yellow" if entry.substantiality == "ambiguous" else "green")
                )
                table.add_row(
                    entry.path,
                    entry.kind,
                    f"[{sub_style}]{entry.substantiality}[/{sub_style}]",
                    str(entry.new_value) if entry.new_value is not None else "",
                )
            console.print(table)
    elif fmt == "json":
        json_text = report.model_dump_json(indent=2)
        if output_path:
            output_path.write_text(json_text, encoding="utf-8")
            console.print(f"[dim]Report written to {output_path}[/dim]")
        else:
            print(json_text)
    elif fmt in ("markdown", "html"):
        template_dir = Path(__file__).parent.parent / "render" / "templates"
        env = Environment(loader=FileSystemLoader(str(template_dir)))
        template_name = f"diff_report.{'md' if fmt == 'markdown' else fmt}"
        try:
            rendered = env.get_template(template_name).render(
                report=report.model_dump()
            )
            if output_path:
                output_path.write_text(rendered, encoding="utf-8")
                console.print(f"[dim]Report written to {output_path}[/dim]")
            else:
                print(rendered)
        except Exception as e:
            console.print(f"[red]Could not render {template_name}: {e}[/red]")
    if report.has_substantial_changes:
        sys.exit(2)
    elif any(e.substantiality == "ambiguous" for e in report.entries):
        sys.exit(3)
    elif report.entries:
        sys.exit(1)
    else:
        sys.exit(0)


@cli.group()
def bundle() -> None:
    """Create and verify evidence bundles (dossier + attachments + SHA-256 manifest)."""
    pass


@bundle.command(name="create")
@click.argument(
    "dossier_file", type=click.Path(exists=True, path_type=Path, dir_okay=False)
)
@click.option(
    "--output",
    "-o",
    "output_path",
    type=click.Path(path_type=Path, dir_okay=False, writable=True),
    required=True,
)
def bundle_create(dossier_file: Path, output_path: Path) -> None:
    """Package a dossier YAML with its evidence files and a SHA-256 manifest."""
    import sys
    from annex4.bundle.engine import create_bundle

    console = Console()
    try:
        manifest = create_bundle(dossier_file, output_path)
        console.print(
            f"[bold green]Bundle created:[/bold green] [cyan]{output_path.resolve()}[/cyan]"
        )
        console.print(f"  {len(manifest)} file(s) in manifest")
        for arc_path in manifest:
            console.print(f"  [dim]• {arc_path}[/dim]")
    except Exception as e:
        console.print(f"[bold red]Bundle creation failed:[/bold red] {e}")
        sys.exit(1)


@bundle.command(name="verify")
@click.argument(
    "bundle_file", type=click.Path(exists=True, path_type=Path, dir_okay=False)
)
def bundle_verify(bundle_file: Path) -> None:
    """Verify the SHA-256 manifest of an evidence bundle."""
    import sys
    from annex4.bundle.engine import verify_bundle

    console = Console()
    result = verify_bundle(bundle_file)
    if result["ok"]:
        console.print(
            f"[bold green]✓ Bundle verified:[/bold green] {result['checked']} file(s) intact."
        )
    else:
        console.print("[bold red]✗ Bundle verification FAILED[/bold red]")
        for failure in result.get("failures", []):
            console.print(f"  [red]{failure}[/red]")
        sys.exit(1)


@cli.group()
def regulation() -> None:
    """Inspect the regulation data packs."""
    pass


@regulation.command(name="list")
def list_regulations() -> None:
    """List all available regulation versions."""
    console = Console()
    try:
        import annex4.regulation.versions

        versions_path = Path(annex4.regulation.versions.__file__).parent
        versions = [
            d.name
            for d in versions_path.iterdir()
            if d.is_dir() and d.name != "__pycache__"
        ]
        console.print("[bold]Available Regulation Versions:[/bold]")
        for v in sorted(versions):
            console.print(f"- {v}")
    except (ImportError, AttributeError, FileNotFoundError):
        console.print("[red]Could not locate regulation versions.[/red]")


@regulation.command(name="show")
@click.argument("document_id", type=str)
@click.option("--version", default="2024-1689_base")
def show(document_id: str, version: str) -> None:
    """Show the content of a specific document (e.g., 'article_1', 'annex_iii')."""
    console = Console()
    regulation_obj = RegulationLoader(version).load_regulation()
    doc_type, _, doc_identifier = document_id.partition("_")
    document: Any = None
    if doc_type == "article":
        document = next(
            (d for d in regulation_obj.articles if d.identifier == doc_identifier), None
        )
    elif doc_type == "annex":
        document = next(
            (d for d in regulation_obj.annexes if d.identifier == doc_identifier), None
        )
    elif doc_type == "recital":
        document = next(
            (d for d in regulation_obj.recitals if d.identifier == doc_identifier), None
        )
    if document:
        console.print(
            Panel(
                f"[bold]{getattr(document, 'title', 'Recital')}[/bold]\n\n{document.text}",
                title=document_id,
                border_style="blue",
            )
        )
    else:
        console.print(f"Document '{document_id}' not found.")


@regulation.command(name="search")
@click.argument("query", type=str)
@click.option("--version", default="2024-1689_base")
def search(query: str, version: str) -> None:
    """Search through the regulation text."""
    regulation_obj = RegulationLoader(version).load_regulation()
    results = search_regulation(query, regulation_obj)
    if not results:
        click.echo("No results found.")
        return
    for doc_id, snippets in results.items():
        click.secho(f"\nResults in {doc_id}:", fg="cyan", bold=True)
        for snippet in snippets:
            click.echo(snippet)


@cli.group()
def schemas() -> None:
    """Commands for working with JSON schemas."""
    pass


@schemas.command(name="generate")
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(path_type=Path, file_okay=False, writable=True),
    default="schemas",
    show_default=True,
)
def generate_schemas_command(output_dir: Path) -> None:
    """Generate JSON schemas from the Pydantic data models."""
    from annex4.schemas.generator import generate_schemas

    console = Console()
    try:
        generate_schemas(output_dir)
        console.print(
            f"[bold green]Success![/bold green] Schemas generated in [cyan]{output_dir.resolve()}[/cyan]"
        )
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise click.Abort()


@cli.command()
@click.option(
    "--output",
    "-o",
    "output_path",
    type=click.Path(path_type=Path, dir_okay=False, writable=True),
    default="dossier.yaml",
    show_default=True,
)
@click.option(
    "--role",
    type=click.Choice(["provider", "deployer"], case_sensitive=False),
    default="provider",
    show_default=True,
)
def init(output_path: Path, role: str) -> None:
    """Initialize a new technical documentation dossier."""
    from annex4.dossier.generator import create_dossier_template

    console = Console()
    try:
        create_dossier_template(output_path, role)
        console.print(
            f"[bold green]Success![/bold green] New dossier created at [cyan]{output_path.resolve()}[/cyan]"
        )
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise click.Abort()


if __name__ == "__main__":
    cli()
