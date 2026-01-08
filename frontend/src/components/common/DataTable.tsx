import React from 'react';
import { useTranslation } from 'react-i18next';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

export interface Column<T> {
  key: string;
  header: string;
  render?: (item: T) => React.ReactNode;
}

interface DataTableProps<T> {
  data: T[];
  columns: Column<T>[];
  onRowClick?: (item: T) => void;
  isLoading?: boolean;
}

export function DataTable<T extends { id: number | string }>({
  data,
  columns,
  onRowClick,
  isLoading,
}: DataTableProps<T>) {
  const { t } = useTranslation('common');

  if (isLoading) {
    return <div className="text-center py-4">{t('loading')}</div>;
  }

  if (data.length === 0) {
    return <div className="text-center py-4 text-muted-foreground">{t('no_data_available')}</div>;
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          {columns.map((column) => (
            <TableHead key={column.key}>{column.header}</TableHead>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {data.map((item) => (
          <TableRow
            key={item.id}
            onClick={() => onRowClick?.(item)}
            className={onRowClick ? 'cursor-pointer' : ''}
          >
            {columns.map((column) => (
              <TableCell key={column.key}>
                {column.render ? column.render(item) : String((item as any)[column.key] || '')}
              </TableCell>
            ))}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
