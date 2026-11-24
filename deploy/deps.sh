#!/usr/bin/env bash
# Si se invoca con sh/dash, vuelve a ejecutarse con bash: allí no existe BASH_SOURCE.
if [ -z "${BASH_VERSION:-}" ]; then
    exec bash "$0" "$@"
fi
set -euo pipefail

# Recoge los paquetes APT declarados en los manifiestos de los módulos y los
# instala. Es el único camino por el que las dependencias de sistema llegan al
# equipo: se ejecuta durante la instalación y en cada actualización.
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

packages="$(
    python3 - "$APP_DIR" <<'EOF'
import glob
import os
import sys

root = sys.argv[1]
packages = []
for path in sorted(glob.glob(os.path.join(root, "modules", "*", "manifest.yaml"))):
    in_deps = False
    with open(path, encoding="utf-8") as manifest:
        for line in manifest:
            if line.startswith("deps:"):
                in_deps = True
                continue
            if not in_deps:
                continue
            if line[:1] and not line[0].isspace() and line.strip():
                in_deps = False
                continue
            item = line.strip()
            if item.startswith("-"):
                item = item[1:].strip()
            item = item.split("#", 1)[0].strip()
            if item:
                packages.append(item)

for package in sorted(set(packages)):
    print(package)
EOF
)"

if [[ -z "$packages" ]]; then
    echo "No hay paquetes declarados en los manifiestos de módulos."
    exit 0
fi

apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y $packages
