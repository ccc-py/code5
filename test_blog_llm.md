```sh
(.venv) cccuser@cccimacdeiMac code5 % TEST_LLM=1 ./test_blog.sh --llm
++ dirname ./test_blog.sh
+ cd .
+ RUN_LLM=false
+ [[ 1 -gt 0 ]]
+ case $1 in
+ RUN_LLM=true
+ shift
+ [[ 0 -gt 0 ]]
+ echo '=== Installing package in development mode ==='
=== Installing package in development mode ===
+ pip3 install -e '.[dev]' -q

[notice] A new release of pip is available: 24.0 -> 26.1.1
[notice] To update, run: pip3 install --upgrade pip
+ echo '=== Running ruff linter ==='
=== Running ruff linter ===
+ ruff check src/ tests/test_blog.py
I001 [*] Import block is un-sorted or un-formatted
  --> src/code5/web/app.py:3:1
   |
 1 |   """FastAPI application for code5 web interface."""
 2 |
 3 | / from __future__ import annotations
 4 | |
 5 | | import json
 6 | | import os
 7 | | import uuid
 8 | | from contextlib import asynccontextmanager
 9 | | from dataclasses import dataclass, field
10 | | from pathlib import Path
11 | | from typing import Any
12 | |
13 | | from fastapi import FastAPI
   | |___________________________^
   |
help: Organize imports

F401 [*] `os` imported but unused
 --> src/code5/web/app.py:6:8
  |
5 | import json
6 | import os
  |        ^^
7 | import uuid
8 | from contextlib import asynccontextmanager
  |
help: Remove unused import: `os`

Found 2 errors.
[*] 2 fixable with the `--fix` option.
+ true
+ echo '=== Running blog tests (Mock mode) ==='
=== Running blog tests (Mock mode) ===
+ python3 -m pytest tests/test_blog.py -v --tb=short -W ignore
================================ test session starts ================================
platform darwin -- Python 3.11.15, pytest-9.0.3, pluggy-1.6.0 -- /Users/cccuser/.venv/bin/python3
cachedir: .pytest_cache
rootdir: /Users/Shared/ccc/project/code5
configfile: pyproject.toml
plugins: mock-3.15.1, asyncio-1.3.0, anyio-4.13.0
asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collected 1 item                                                                    

tests/test_blog.py::TestFastAPIBlog::test_llm_generates_and_runs_blog PASSED  [100%]

=========================== 1 passed in 92.51s (0:01:32) ============================
+ '[' true = true ']'
+ echo ''

+ echo '=== Running blog tests (Real LLM mode) ==='
=== Running blog tests (Real LLM mode) ===
+ TEST_LLM=1
+ python3 -m pytest tests/test_blog.py::TestFastAPIBlog -v --tb=short -W ignore
================================ test session starts ================================
platform darwin -- Python 3.11.15, pytest-9.0.3, pluggy-1.6.0 -- /Users/cccuser/.venv/bin/python3
cachedir: .pytest_cache
rootdir: /Users/Shared/ccc/project/code5
configfile: pyproject.toml
plugins: mock-3.15.1, asyncio-1.3.0, anyio-4.13.0
asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collected 1 item                                                                    

tests/test_blog.py::TestFastAPIBlog::test_llm_generates_and_runs_blog PASSED  [100%]

=========================== 1 passed in 69.27s (0:01:09) ============================
+ echo ''

+ echo '=== Test complete ==='
=== Test complete ===
```
