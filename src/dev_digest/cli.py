import click

from dev_digest.command import digest as digest_cmd
from . import __version__


@click.group(name="dev-digest")
@click.version_option(version=__version__)
def app():
    pass


@app.command("run", help="Run dev-digest")
@click.option("-d", "--days",
              default=7,
              show_default=True,
              help="Name to greet.")
def hello(days: int) -> int:
    return int(digest_cmd.run(days=days) or 0)
