import React from 'react';
import { useTranslation } from 'react-i18next';
import { ChevronUp, ChevronDown, ChevronsUpDown, ChevronLeft, ChevronRight } from 'lucide-react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { cn } from '@/lib/utils';

export type SortDirection = 'asc' | 'desc' | null;

export interface SortState {
  column: string | null;
  direction: SortDirection;
}

export interface ServerColumn<T> {
  key: string;
  header: string;
  sortable?: boolean;
  render?: (item: T) => React.ReactNode;
  className?: string;
}

export interface PaginationInfo {
  page: number;
  page_size: number;
  total_items: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
}

interface ServerDataTableProps<T> {
  data: T[];
  columns: ServerColumn<T>[];
  pagination: PaginationInfo;
  sort: SortState;
  isLoading?: boolean;
  onRowClick?: (item: T) => void;
  onSort: (column: string) => void;
  onPageChange: (page: number) => void;
  onPageSizeChange: (pageSize: number) => void;
  pageSizeOptions?: number[];
}

export function ServerDataTable<T extends { id: string | number }>({
  data,
  columns,
  pagination,
  sort,
  isLoading,
  onRowClick,
  onSort,
  onPageChange,
  onPageSizeChange,
  pageSizeOptions = [25, 50, 100],
}: ServerDataTableProps<T>) {
  const { t } = useTranslation('common');

  const getSortIcon = (columnKey: string) => {
    if (sort.column !== columnKey) {
      return <ChevronsUpDown className="h-4 w-4 ml-1 opacity-50" />;
    }
    if (sort.direction === 'asc') {
      return <ChevronUp className="h-4 w-4 ml-1" />;
    }
    return <ChevronDown className="h-4 w-4 ml-1" />;
  };

  const handleSort = (columnKey: string) => {
    onSort(columnKey);
  };

  // Calculate display range
  const startItem = (pagination.page - 1) * pagination.page_size + 1;
  const endItem = Math.min(pagination.page * pagination.page_size, pagination.total_items);

  // Generate page numbers to display
  const getPageNumbers = () => {
    const pages: (number | string)[] = [];
    const totalPages = pagination.total_pages;
    const currentPage = pagination.page;

    if (totalPages <= 7) {
      for (let i = 1; i <= totalPages; i++) {
        pages.push(i);
      }
    } else {
      pages.push(1);

      if (currentPage > 3) {
        pages.push('...');
      }

      const start = Math.max(2, currentPage - 1);
      const end = Math.min(totalPages - 1, currentPage + 1);

      for (let i = start; i <= end; i++) {
        if (!pages.includes(i)) {
          pages.push(i);
        }
      }

      if (currentPage < totalPages - 2) {
        pages.push('...');
      }

      if (!pages.includes(totalPages)) {
        pages.push(totalPages);
      }
    }

    return pages;
  };

  if (isLoading) {
    return (
      <div className="w-full">
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                {columns.map((column) => (
                  <TableHead key={column.key} className={column.className}>
                    {column.header}
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {[...Array(5)].map((_, index) => (
                <TableRow key={index}>
                  {columns.map((column) => (
                    <TableCell key={column.key}>
                      <div className="h-4 bg-muted animate-pulse rounded" />
                    </TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className="w-full">
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                {columns.map((column) => (
                  <TableHead key={column.key} className={column.className}>
                    {column.header}
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>
          </Table>
        </div>
        <div className="text-center py-8 text-muted-foreground">
          {t('no_data_available', 'No data available')}
        </div>
      </div>
    );
  }

  return (
    <div className="w-full space-y-4">
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              {columns.map((column) => (
                <TableHead
                  key={column.key}
                  className={cn(
                    column.className,
                    column.sortable && 'cursor-pointer select-none hover:bg-muted/50'
                  )}
                  onClick={column.sortable ? () => handleSort(column.key) : undefined}
                >
                  <div className="flex items-center">
                    {column.header}
                    {column.sortable && getSortIcon(column.key)}
                  </div>
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.map((item) => (
              <TableRow
                key={item.id}
                onClick={() => onRowClick?.(item)}
                className={cn(onRowClick && 'cursor-pointer hover:bg-muted/50')}
              >
                {columns.map((column) => (
                  <TableCell key={column.key} className={column.className}>
                    {column.render
                      ? column.render(item)
                      : String((item as Record<string, unknown>)[column.key] || '')}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {/* Pagination Controls */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <span>
            {t('showing', 'Showing')} {startItem}-{endItem} {t('of', 'of')} {pagination.total_items}
          </span>
          <span className="hidden sm:inline">|</span>
          <div className="flex items-center gap-2">
            <span className="hidden sm:inline">{t('per_page', 'Per page')}:</span>
            <Select
              value={String(pagination.page_size)}
              onValueChange={(value) => onPageSizeChange(Number(value))}
            >
              <SelectTrigger className="h-8 w-[70px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {pageSizeOptions.map((size) => (
                  <SelectItem key={size} value={String(size)}>
                    {size}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        <div className="flex items-center gap-1">
          <Button
            variant="outline"
            size="sm"
            onClick={() => onPageChange(pagination.page - 1)}
            disabled={!pagination.has_prev}
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>

          {getPageNumbers().map((pageNum, index) =>
            pageNum === '...' ? (
              <span key={`ellipsis-${index}`} className="px-2 text-muted-foreground">
                ...
              </span>
            ) : (
              <Button
                key={pageNum}
                variant={pagination.page === pageNum ? 'default' : 'outline'}
                size="sm"
                onClick={() => onPageChange(Number(pageNum))}
                className="min-w-[32px]"
              >
                {pageNum}
              </Button>
            )
          )}

          <Button
            variant="outline"
            size="sm"
            onClick={() => onPageChange(pagination.page + 1)}
            disabled={!pagination.has_next}
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}

// Helper hook for managing server-side table state
export function useServerTableState(defaultPageSize = 25) {
  const [page, setPage] = React.useState(1);
  const [pageSize, setPageSize] = React.useState(defaultPageSize);
  const [sort, setSort] = React.useState<SortState>({ column: null, direction: null });

  const handleSort = React.useCallback((column: string) => {
    setSort((prev) => {
      if (prev.column === column) {
        // Cycle: asc -> desc -> null
        if (prev.direction === 'asc') {
          return { column, direction: 'desc' };
        } else if (prev.direction === 'desc') {
          return { column: null, direction: null };
        }
      }
      return { column, direction: 'asc' };
    });
    setPage(1); // Reset to first page on sort change
  }, []);

  const handlePageChange = React.useCallback((newPage: number) => {
    setPage(newPage);
  }, []);

  const handlePageSizeChange = React.useCallback((newPageSize: number) => {
    setPageSize(newPageSize);
    setPage(1); // Reset to first page on page size change
  }, []);

  // Convert sort state to API parameter format
  const sortParam = React.useMemo(() => {
    if (!sort.column) return undefined;
    return sort.direction === 'desc' ? `-${sort.column}` : sort.column;
  }, [sort]);

  const resetPagination = React.useCallback(() => {
    setPage(1);
  }, []);

  return {
    page,
    pageSize,
    sort,
    sortParam,
    handleSort,
    handlePageChange,
    handlePageSizeChange,
    resetPagination,
  };
}
