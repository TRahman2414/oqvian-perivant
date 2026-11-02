#!/usr/bin/env bash
set -euo pipefail
python3 - <<'PY'
from urllib.request import Request, urlopen

request = Request("http://127.0.0.1:8010/api/demo/reset", method="POST")
with urlopen(request, timeout=5) as response:
    print(response.read().decode())
PY
