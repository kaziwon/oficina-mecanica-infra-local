#!/usr/bin/env python3
"""Aplica somente os agentes de observabilidade do kind local."""

import argparse
import os
import subprocess
import sys
from pathlib import Path

from local_runtime import operation_lock, require_cluster, runtime_home, terraform_apply
from new_relic_config import read_new_relic


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan-only", action="store_true")
    args = parser.parse_args()
    home = runtime_home()
    require_cluster(home)
    with operation_lock(home):
        settings = read_new_relic(home)
        if not (home / "secrets/newrelic.json").is_file():
            raise ValueError("Execute primeiro python3 scripts/configure_newrelic.py.")
        terraform_apply(Path(__file__).resolve().parents[1], Path("observability"), home,
                        "observability", settings, args.plan_only)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, TimeoutError, OSError, subprocess.CalledProcessError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
