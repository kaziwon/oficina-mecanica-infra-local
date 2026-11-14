#!/usr/bin/env python3
"""Provisiona somente as dependencias compartilhadas do kind da Fase 4."""

import argparse
from pathlib import Path

from local_runtime import common_secrets, ensure_kind, operation_lock, require_cluster, runtime_home, terraform_apply


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan-only", action="store_true")
    args = parser.parse_args()
    home = runtime_home()
    require_cluster(home)
    with operation_lock(home):
        common_secrets(home, create=True)
        ensure_kind(home)
        terraform_apply(Path(__file__).resolve().parents[1], Path("platform"), home,
                        "platform", {}, args.plan_only)


if __name__ == "__main__":
    main()
