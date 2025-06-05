#!/usr/bin/env python

import sys

from vulture.config import make_config
from vulture.core import Vulture


def report_only_interesting(
    vulture,
    min_confidence=0,
    sort_by_size=False,
    make_whitelist=False,
    show_all=False,
):
    vulture.defined_imports = []
    vulture.defined_props = []
    vulture.defined_vars = []
    vulture.defined_attrs = []

    for item in vulture.get_unused_code(
        min_confidence=min_confidence, sort_by_size=sort_by_size
    ):
        if not (show_all or item.typ == "function"):
            continue

        print(
            item.get_whitelist_string()
            if make_whitelist
            else item.get_report(add_size=sort_by_size)
        )
        vulture.found_dead_code_or_error = True

    return vulture.found_dead_code_or_error


def main(options):
    config = make_config(argv=[])
    vulture = Vulture(
        verbose=config["verbose"],
        ignore_names=config["ignore_names"],
        ignore_decorators=config["ignore_decorators"],
    )
    vulture.scavenge(config["paths"], exclude=config["exclude"])
    sys.exit(
        report_only_interesting(
            vulture,
            min_confidence=config["min_confidence"],
            sort_by_size=config["sort_by_size"],
            make_whitelist=config["make_whitelist"],
            show_all=options.all,
        )
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true")

    options = parser.parse_args(sys.argv[1:])
    main(options)
