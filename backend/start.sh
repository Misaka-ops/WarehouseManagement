#!/bin/sh
set -eu

echo "[backend] Preparing runtime directories..."
mkdir -p /app/backend/data /app/backend/logs /app/采购 /app/仓库 /app/采购/uploaded

if [ -z "${AUTH_ADMIN_PASSWORD:-}" ]; then
  echo "[backend] AUTH_ADMIN_PASSWORD is required." >&2
  exit 1
fi

if [ -z "${AUTH_TOKEN_SECRET:-}" ]; then
  echo "[backend] AUTH_TOKEN_SECRET is required." >&2
  exit 1
fi

echo "[backend] Validating workbook files and writable paths..."
python - <<'PY'
from pathlib import Path
import os
import sys

from openpyxl import load_workbook


def fail(message: str) -> None:
    print(f"[backend] {message}", file=sys.stderr)
    raise SystemExit(1)


def require_directory(path: Path, *, writable: bool = False) -> None:
    if not path.exists():
        fail(f"Required directory is missing: {path}")
    if not path.is_dir():
        fail(f"Expected a directory but found something else: {path}")
    if writable and not os.access(path, os.W_OK):
        fail(f"Directory is not writable: {path}")


def require_file(path: Path, *, writable: bool = False) -> None:
    if not path.exists():
        fail(f"Required file is missing: {path}")
    if not path.is_file():
        fail(f"Expected a file but found something else: {path}")
    if not os.access(path, os.R_OK):
        fail(f"File is not readable: {path}")
    if writable and not os.access(path, os.W_OK):
        fail(f"File is not writable: {path}")


purchase_workbook = Path("/app/采购/物料采购清单列表0226.xlsx")
warehouse_workbook = Path("/app/仓库/仓库库存2026最新版_备注并入规格型号.xlsx")
purchase_archive_dir = purchase_workbook.parent / "uploaded"

require_directory(Path("/app/backend/data"), writable=True)
require_directory(Path("/app/backend/logs"), writable=True)
require_directory(purchase_workbook.parent, writable=True)
require_directory(purchase_archive_dir, writable=True)
require_directory(warehouse_workbook.parent, writable=True)
require_file(purchase_workbook)
require_file(warehouse_workbook, writable=True)

try:
    purchase_book = load_workbook(purchase_workbook, data_only=True, read_only=True)
except Exception as exc:
    fail(f"Failed to open purchase workbook {purchase_workbook}: {exc}")

required_purchase_sheets = {"Sheet1", "佳时坤"}
missing_purchase_sheets = sorted(required_purchase_sheets.difference(purchase_book.sheetnames))
if missing_purchase_sheets:
    fail(
        "Purchase workbook is missing required sheets: "
        + ", ".join(missing_purchase_sheets)
    )

try:
    warehouse_book = load_workbook(warehouse_workbook, data_only=True, read_only=True)
except Exception as exc:
    fail(f"Failed to open warehouse workbook {warehouse_workbook}: {exc}")

if "原物料库存清单" not in warehouse_book.sheetnames:
    fail("Warehouse workbook is missing required sheet: 原物料库存清单")

print("[backend] Runtime preflight passed.")
PY

echo "[backend] Starting API server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
