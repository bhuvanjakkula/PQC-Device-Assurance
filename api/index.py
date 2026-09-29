"""
Vercel Serverless Entrypoint for Continuous PQC Updateability Assurance.
Provides the HTTP request handler compatible with @vercel/python.
"""

import os
import shutil
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Seed SQLite database to /tmp in Vercel serverless environment
if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
    tmp_db = Path("/tmp/pqc_assurance.db")
    orig_db = PROJECT_ROOT / "data" / "pqc_assurance.db"
    if not tmp_db.exists() and orig_db.exists():
        shutil.copyfile(str(orig_db), str(tmp_db))
    os.environ["PQC_DB_PATH"] = str(tmp_db)

from api.server import AssuranceAPIHandler

# Export handler for @vercel/python
class handler(AssuranceAPIHandler):
    pass
