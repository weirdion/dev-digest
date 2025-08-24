import logging
from collections.abc import Sequence
from types import SimpleNamespace

import click

from . import __version__
from .command import hello as hello_cmd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("dev-digest")

@click.group(name="dev-digest")
@click.version_option(version=__version__)
def app():
    pass

@app.command("hello", help="Print a friendly greeting.")
@click.option("-n", "--name", default="world", show_default=True, help="Name to greet.")
@click.option("-t", "--times", default=1, show_default=True, type=int, help="How many times to print the greeting.")
def hello(name: str, times: int) -> int:
    return int(hello_cmd.run(SimpleNamespace(name=name, times=times)) or 0)
