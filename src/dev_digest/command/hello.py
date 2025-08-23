def run(ns) -> int:
    """
    Execute the 'hello' subcommand.

    Args:
        ns: argparse.Namespace with attributes 'name' and 'times'
    Returns:
        int: process exit code (0 for success)
    """
    for _ in range(ns.times):
        print(f"Hello, {ns.name}!")
    return 0
