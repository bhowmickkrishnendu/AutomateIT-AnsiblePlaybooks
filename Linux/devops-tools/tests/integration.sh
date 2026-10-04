#!/usr/bin/env bash
# Run ONLY on an explicitly selected disposable Linux host/inventory.
# Example: bash tests/integration.sh -i inventory.test.ini -e @config.test.yml -K
set -euo pipefail
cd "$(dirname "$0")/.."
run_log="$(mktemp)"
trap 'rm -f "$run_log"' EXIT
export ANSIBLE_NOCOLOR=1
ansible-playbook playbook.yml "$@"
ansible-playbook playbook.yml "$@" | tee "$run_log"
python3 - "$run_log" <<'PY'
import pathlib
import re
import sys
text = pathlib.Path(sys.argv[1]).read_text()
recaps = re.findall(r'^\S+\s+:\s+ok=\d+\s+changed=(\d+)\s+unreachable=(\d+)\s+failed=(\d+)', text, re.M)
if not recaps or any(any(int(n) for n in row) for row in recaps):
    raise SystemExit('Repeat-run idempotency check failed: expected changed=0, unreachable=0, failed=0 for every host')
print('Repeat-run idempotency check passed for every host')
PY
