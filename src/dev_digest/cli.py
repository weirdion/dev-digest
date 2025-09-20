import click

from dev_digest.command import digest as digest_cmd
from dev_digest.utility.constants import MODEL_PROFILES, DEFAULT_MODEL_KEY

from . import __version__


@click.group(name="dev-digest")
@click.version_option(version=__version__)
def app():
    pass


@app.command("run", help="Run dev-digest")
@click.option("-d", "--debug",
              is_flag=True, default=False,
              show_default=True, help="Enable debug mode")
@click.option("--days",
              default=7,
              show_default=True,
              help="Number of days to look back for items.")
@click.option(
    "--model-key",
    type=click.Choice(sorted(list(MODEL_PROFILES.keys()))),
    default=DEFAULT_MODEL_KEY,
    show_default=True,
    help="Model profile to use for summarization and cost."
)
@click.option(
    "--ai/--no-ai",
    is_flag=True,
    default=False,
    show_default=True,
    help="Use deterministic pipeline (or AI)"
)
@click.option(
    "-wf",
    "--with-footer",
    is_flag=True,
    default=False,
    show_default=True,
    help="Include footer"
)
@click.option(
    "--overwrite",
    is_flag=True,
    default=False,
    show_default=True,
    help="If today's output folder exists, clear it before running."
)
def run(debug: bool, days: int, model_key: str, ai: bool, with_footer: bool, overwrite: bool) -> int:
    return int(
        digest_cmd.run(
            debug, days=days, model_key=model_key,
            ai_generated=ai, include_footer=with_footer,
            overwrite=overwrite
            )
        or 0)
