from click.testing import CliRunner

from dev_digest import __version__
from dev_digest.cli import app

runner = CliRunner()


def test_hello_default():
    result = runner.invoke(app, ["hello"])
    assert result.exit_code == 0
    assert result.stdout == "Hello, world!\n"


def test_hello_with_options():
    result = runner.invoke(app, ["hello", "-n", "Alice", "-t", "2"])
    assert result.exit_code == 0
    # Expect exactly two lines, each greeting Alice
    assert result.stdout == "Hello, Alice!\nHello, Alice!\n"


def test_version_flag():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    # The output should include the version string.
    assert __version__ in result.stdout.strip()
