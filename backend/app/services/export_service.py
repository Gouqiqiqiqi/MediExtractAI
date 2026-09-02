"""Export service — converts extraction results to CSV / Excel.

The export is where a reviewed dataset leaves this system, so it is also where
the review has to mean something. Two rules live here rather than in the UI,
because a gate a client enforces is not a gate:

* An unapproved export is labelled as one — in the filename, in a column on
  every row, and on a sheet of its own in the workbook. Blocking draft exports
  outright would only push people to screenshots and retyping, which is the
  same data leaving with none of the caveats attached.
* An approved export carries who signed it off and when, so the file can still
  answer that question after it has been emailed on twice.
"""

from __future__ import annotations

import io
from typing import Any

import pandas as pd

from app.models.schemas import ColumnDefinition

# The column added to a draft export. Named as a sentence because it is read by
# whoever opens the spreadsheet, not by a developer.
STATUS_COLUMN = "Review status"

# Multi-value cells ("text[]" columns — symptoms, medications) are joined with
# this rather than with a comma: the values themselves routinely contain commas
# ("Amoxicillin 500mg PO TDS, then review"), and a reader splitting on one would
# quietly get the wrong number of drugs.
LIST_SEPARATOR = "; "


def _flatten(value: Any) -> Any:
    """Make one cell value fit in a spreadsheet cell.

    A list reached pandas untouched before this, and it wrote the Python repr —
    ``['fall', 'dizziness']``, quotes and brackets included — into the CSV.
    openpyxl does not even accept a list, so Excel export of any ``text[]``
    column failed outright.
    """
    if isinstance(value, (list, tuple)):
        return LIST_SEPARATOR.join(_flatten(v) for v in value if v is not None)
    if isinstance(value, dict):
        # Not something the schema can produce today, but a model that returns
        # one should not take the export down with it.
        return str(value)
    if value is None:
        return ""
    if isinstance(value, bool):
        return "yes" if value else "no"
    return str(value) if not isinstance(value, (int, float)) else value


class ExportService:
    """Stateless export helpers."""

    @staticmethod
    def _frame(
        columns: list[ColumnDefinition],
        rows: list[dict[str, Any]],
        extra_columns: list[str] | None = None,
    ) -> pd.DataFrame:
        col_names = [c.name for c in columns] + (extra_columns or [])
        flattened = [{k: _flatten(v) for k, v in row.items()} for row in rows]
        return pd.DataFrame(flattened, columns=col_names)

    @staticmethod
    def to_csv(
        columns: list[ColumnDefinition],
        rows: list[dict[str, Any]],
        extra_columns: list[str] | None = None,
    ) -> io.BytesIO:
        df = ExportService._frame(columns, rows, extra_columns)
        buffer = io.BytesIO()
        # No comment header, deliberately: a leading "# draft" line would make
        # the file unreadable to every CSV parser that receives it. The status
        # travels as a column instead, which survives being loaded.
        df.to_csv(buffer, index=False, encoding="utf-8-sig")
        buffer.seek(0)
        return buffer

    @staticmethod
    def to_excel(
        columns: list[ColumnDefinition],
        rows: list[dict[str, Any]],
        extra_columns: list[str] | None = None,
        about: list[tuple[str, str]] | None = None,
    ) -> io.BytesIO:
        df = ExportService._frame(columns, rows, extra_columns)
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Extraction")
            if about:
                # header=False: the sheet is a list of label/value pairs, and a
                # header row of two blank column names reads as a missing title.
                pd.DataFrame(about).to_excel(
                    writer, index=False, header=False, sheet_name="About this export"
                )
        buffer.seek(0)
        return buffer
