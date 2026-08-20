"""Export service — converts extraction results to CSV / Excel / JSON."""

from __future__ import annotations

import io
from typing import Any

import pandas as pd

from app.models.schemas import ColumnDefinition


class ExportService:
    """Stateless export helpers."""

    @staticmethod
    def to_csv(
        columns: list[ColumnDefinition],
        rows: list[dict[str, Any]],
    ) -> io.BytesIO:
        col_names = [c.name for c in columns]
        df = pd.DataFrame(rows, columns=col_names)
        buffer = io.BytesIO()
        df.to_csv(buffer, index=False, encoding="utf-8-sig")
        buffer.seek(0)
        return buffer

    @staticmethod
    def to_excel(
        columns: list[ColumnDefinition],
        rows: list[dict[str, Any]],
    ) -> io.BytesIO:
        col_names = [c.name for c in columns]
        df = pd.DataFrame(rows, columns=col_names)
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Extraction")
        buffer.seek(0)
        return buffer
