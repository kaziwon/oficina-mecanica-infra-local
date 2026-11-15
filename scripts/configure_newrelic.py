#!/usr/bin/env python3
"""Habilita/desabilita New Relic sem gravar a license key nos repositorios."""

import argparse
import getpass
import os
import re
import sys

from local_runtime import operation_lock, private_json, runtime_home, write_private_json


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--disable", action="store_true")
    args = parser.parse_args()
    home = runtime_home()
    path = home / "secrets" / "newrelic.json"
    with operation_lock(home):
        if args.disable:
            existing = private_json(path) if path.exists() or path.is_symlink() else {}
            settings = {"enabled": False, "license_key": existing.get("license_key", "")}
        else:
            key = os.environ.get("NEW_RELIC_LICENSE_KEY", "")
            if not key and sys.stdin.isatty():
                key = getpass.getpass("New Relic license key (nao sera exibida): ")
            key = key.strip()
            if not re.fullmatch(r"[A-Za-z0-9_-]{20,256}", key):
                raise ValueError("Informe uma license key valida pelo prompt ou NEW_RELIC_LICENSE_KEY.")
            settings = {"enabled": True, "license_key": key}
        write_private_json(path, settings)
    print("New Relic " + ("desabilitado" if args.disable else "habilitado") + " na configuracao privada.")
    print("Aplique observability/ e os deploys dos servicos para atualizar os processos em execucao.")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
