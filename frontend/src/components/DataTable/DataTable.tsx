/**
 * DataTable — renders extraction results with inline editing using TanStack Table.
 */

import { useMemo, useState } from 'react';
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
}

export default function DataTable({ columns, data, onDataChange }: Props) {
  const [tableData, setTableData] = useState(data);

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
        header: '#',
        cell: ({ row }) => (
          <span className="text-on-surface-variant text-label-md">{row.index + 1}</span>
        ),
        size: 40,
      },
      ...columns.map((col) => ({
        accessorKey: col.name,
        header: () => (
          <div>
            <span className="font-medium text-on-surface">{col.name}</span>
            <span className="text-label-md text-on-surface-variant ml-1">({col.data_type})</span>
          </div>
        ),
        cell: ({ row, column }: { row: { index: number; original: Record<string, unknown> }; column: { id: string } }) => (
          <EditableCell
            value={row.original[column.id]}
            onChange={(val) => updateCell(row.index, column.id, val)}
            dataType={col.data_type}
          />
        ),
      })),
    ],
    [columns, tableData],
  );

  const table = useReactTable({
    data: tableData,
    columns: tableColumns,
    getCoreRowModel: getCoreRowModel(),
  });

  if (tableData.length === 0) {
    return (
      <div className="card-elevated text-center py-12">
        <p className="text-body-md text-on-surface-variant">
          No extraction results yet. Run an extraction to see data here.
        </p>
      </div>
    );
  }

  return (
    <div className="card-elevated overflow-hidden p-0">
      <div className="overflow-x-auto">
        <table className="w-full text-body-md">
          <thead>
            {table.getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id} className="bg-surface-container border-b border-outline/40">
                {headerGroup.headers.map((header) => (
                  <th
                    key={header.id}
                    className="text-left px-4 py-3 text-label-lg font-medium text-on-surface-variant"
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
                className="border-b border-outline/20 hover:bg-surface-container transition-colors duration-150"
              >
                {row.getVisibleCells().map((cell) => (
                  <td key={cell.id} className="px-4 py-2.5">
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="px-4 py-3 bg-surface-container border-t border-outline/40 text-label-md text-on-surface-variant">
        {tableData.length} row{tableData.length !== 1 ? 's' : ''} extracted
      </div>
    </div>
  );
}
