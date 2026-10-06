#!/bin/sh
export CAMEVISION_EGO_ROOT="$(CDPATH= cd -- "$(dirname "$0")" && pwd)"
cd "$CAMEVISION_EGO_ROOT" || exit 1
if [ ! -f "$CAMEVISION_EGO_ROOT/tools/cv_ego_setup.py" ]; then
	echo "CameVision-Ego.sh must sit in the unzipped package folder (next to tools/)." >&2
	exit 1
fi
exec "$CAMEVISION_EGO_ROOT/CameVision-Ego" "$@"
