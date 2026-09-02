/**
 * DataTable — extraction results, with inline correction.
 *
 * A review surface: dense rows, a sticky header so the column you are checking
 * stays named while you scroll, and provenance columns pinned at the left as
 * read-only text.
 */

import { useEffect, useMemo, useState } from 'react';
import {
  useReactTable,
  getCoreRowModel,
  flexRender,
  type ColumnDef,
} from '@tanstack/react-table';
import type { ColumnDefinition } from '../../types';
import EditableCell from './EditableCell';

interface Props {
  columns: ColumnDefinition[];
  data: Record<string, unknown>[];
  onDataChange?: (data: Record<string, unknown>[]) => void;
  /**
   * Columns rendered as read-only text. Used for provenance — which note a row
   * came from is a record of fact, not a value a reviewer should be able to
   * edit away from the note it describes.
   */
  readOnlyColumns?: string[];
}

export default function DataTable({
  columns,
  data,
  onDataChange,
  readOnlyColumns = [],
}: Props) {
  const [tableData, setTableData] = useState(data);
  const readOnly = useMemo(() => new Set(readOnlyColumns), [readOnlyColumns]);

  // A fresh extraction replaces the rows; without this the table would keep
  // showing the previous run's data.
  useEffect(() => setTableData(data), [data]);

  const updateCell = (rowIndex: number, columnId: string, value: unknown) => {
    const updated = tableData.map((row, i) =>
      i === rowIndex ? { ...row, [columnId]: value } : row,
    );
    setTableData(updated);
    onDataChange?.(updated);
  };

  const tableColumns = useMemo<ColumnDef<Record<string, unknown>>[]>(
    () => [
      {
        id: 'row_number',
        header: () => <span className="text-on-surface-variant/70">#</span>,
        cell: ({ row }) => (
          <span className="text-label-md text-on-surface-variant tabular">
            {row.index + 1}
          </span>
        ),
        size: 36,
      },
      ...columns.map((col) => {
        const isReadOnly = readOnly.has(col.name);
        return {
          accessorKey: col.name,
          header: () => (
            <span className="flex items-baseline gap-1.5 whitespace-nowrap">
              <span className="text-title-sm text-on-surface">{col.name}</span>
              <span className="text-label-sm text-on-surface-variant/70 normal-case">
                {isReadOnly ? 'source' : col.data_type}
              </span>
            </span>
          ),
          cell: ({
            row,
            column,
          }: {
            row: { index: number; original: Record<string, unknown> };
            column: { id: string };
          }) =>
            isReadOnly ? (
              <span className="mono text-on-surface-variant whitespace-nowrap">
                {String(row.original[column.id] ?? '')}
              </span>
            ) : (
              <EditableCell
                value={row.original[column.id]}
                onChange={(val) => updateCell(row.index, column.id, val)}
                dataType={col.data_type}
              />
            ),
        };
      }),
    ],
    [columns, tableData, readOnly],
  );

  const table = useReactTable({
    data: tableData,
    columns: tableColumns,
    getCoreRowModel: getCoreRowModel(),
  });

  if (tableData.length === 0) {
    return (
      <div className="card px-6 py-12 text-center">
        <p className="text-body-md text-on-surface-variant">
          No extraction results yet. Run an extraction to see data here.
        </p>
      </div>
    );
  }

  return (
    <div className="card overflow-hidden">
      <div className="overflow-x-auto max-h-[32rem] overflow-y-auto">
        <table className="w-full border-collapse">
          <thead className="sticky top-0 z-10">
            {table.getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id} className="bg-surface-dim">
                {headerGroup.headers.map((header) => (
                  <th
                    key={header.id}
                    className="text-left px-3 py-2 border-b border-outline font-normal"
                  >
                    {flexRender(header.column.columnDef.header, header.getContext())}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.map((row) => (
              <tr
                key={row.id}
                className="border-b border-outline-variant last:border-0 hover:bg-surface-dim
                           transition-colors duration-100"
              >
                {row.getVisibleCells().map((cell) => (
                  <td key={cell.id} className="px-3 py-1.5 align-top">
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="px-3 py-2 border-t border-outline bg-surface-dim flex items-center gap-2">
        <span className="text-label-md text-on-surface-variant tabular">
          {tableData.length} row{tableData.length === 1 ? '' : 's'}
        </span>
        {onDataChange && (
          <span className="text-label-md text-on-surface-variant/80">
            · click any editable cell to correct it
          </span>
        )}
      </div>
    </div>
  );
}
