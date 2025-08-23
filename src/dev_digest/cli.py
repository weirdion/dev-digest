from collections.abc import Sequence
from types import SimpleNamespace
from typing import Any

import typer

from . import __version__
from .command import hello as hello_cmd

app = typer.Typer(add_completion=True, no_args_is_help=True)


def _version_callback(ctx: typer.Context, param: Any, value: bool | None) -> None:
    if value:
        prog = ctx.info_name or "dev-digest"
        typer.echo(f"{prog} {__version__}")
        raise typer.Exit()


@app.callback()
def _main_callback(
    version: bool | None = typer.Option(
        None,
        "--version",
        help="Show the version and exit.",
        is_eager=True,
        callback=_version_callback,
    ),
) -> None:
    """Developer Digest CLI."""
    return


@app.command("hello", help="Print a friendly greeting.")
def hello(
    name: str = typer.Option("world", "--name", "-n", help="Name to greet."),
    times: int = typer.Option(1, "--times", "-t", help="How many times to print the greeting."),
) -> int:
    return int(hello_cmd.run(SimpleNamespace(name=name, times=times)) or 0)


def main(argv: Sequence[str] | None = None):
    if argv is None:
        argv = []
    app(argv)
