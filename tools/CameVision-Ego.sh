#!/bin/sh
HERE=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
if [ -f "$HERE/cv_ego_setup.py" ]; then
  ROOT=$(CDPATH= cd -- "$HERE/.." && pwd)
else
  echo "CameVision-Ego.sh in tools/ is missing cv_ego_setup.py" >&2
  exit 1
fi
if [ ! -f "$ROOT/tools/cv_ego_setup.py" ] || [ ! -x "$ROOT/CameVision-Ego" ]; then
  echo "This tools/ launcher must stay inside the unzipped package." >&2
  exit 1
fi
exec "$ROOT/CameVision-Ego" "$@"
