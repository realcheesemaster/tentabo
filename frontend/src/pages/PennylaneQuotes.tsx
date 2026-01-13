import React, { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { useSearchParams, Link } from 'react-router-dom';
import { pennylaneApi } from '@/services/api';
import { type PennylaneQuote, type PennylaneConnection } from '@/types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Checkbox } from '@/components/ui/checkbox';
import { formatCurrency, formatDate } from '@/lib/utils';
import {
  ServerDataTable,
  useServerTableState,
  type ServerColumn,
  type PaginationInfo,
} from '@/components/common/ServerDataTable';
import { FileCheck, Search, ChevronDown, X } from 'lucide-react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';

const QUOTE_STATUSES = ['draft', 'pending', 'sent', 'accepted', 'rejected', 'expired'] as const;

const getQuoteStatusVariant = (status?: string): "default" | "secondary" | "destructive" | "outline" | "success" | "warning" | "info" => {
  switch (status?.toLowerCase()) {
    case 'pending':
      return 'secondary';
    case 'sent':
      return 'info';
    case 'accepted':
      return 'success';
    case 'rejected':
      return 'destructive';
    case 'expired':
      return 'warning';
    default:
      return 'outline';
  }
};

export const PennylaneQuotes: React.FC = () => {
  const { t } = useTranslation(['pennylane', 'common']);
  const [searchParams, setSearchParams] = useSearchParams();

  // Initialize state from URL params
  const [connectionFilter, setConnectionFilter] = useState<string>(
    searchParams.get('connection') || 'all'
  );
  const [statusFilter, setStatusFilter] = useState<string[]>(() => {
    const statusParam = searchParams.get('status');
    return statusParam ? statusParam.split(',') : [];
  });
  const [statusPopoverOpen, setStatusPopoverOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState<string>(searchParams.get('search') || '');
  const [debouncedSearch, setDebouncedSearch] = useState<string>(searchParams.get('search') || '');

  const {
    page,
    pageSize,
    sort,
    sortParam,
    handleSort,
    handlePageChange,
    handlePageSizeChange,
    resetPagination,
  } = useServerTableState(25);

  // Debounce search input
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchQuery);
      resetPagination();
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery, resetPagination]);

  // Update URL params when filters change
  useEffect(() => {
    const params = new URLSearchParams();
    if (connectionFilter !== 'all') params.set('connection', connectionFilter);
    if (statusFilter.length > 0) params.set('status', statusFilter.join(','));
    if (debouncedSearch) params.set('search', debouncedSearch);
    setSearchParams(params, { replace: true });
  }, [connectionFilter, statusFilter, debouncedSearch, setSearchParams]);

  const { data: connections } = useQuery({
    queryKey: ['pennylane-connections'],
    queryFn: () => pennylaneApi.getConnections(),
  });

  const { data: quotesData, isLoading, isFetching } = useQuery({
    queryKey: [
      'pennylane-quotes',
      page,
      pageSize,
      connectionFilter,
      statusFilter,
      debouncedSearch,
      sortParam,
    ],
    queryFn: () =>
      pennylaneApi.getQuotes(page, pageSize, {
        connection_id: connectionFilter !== 'all' ? connectionFilter : undefined,
        status: statusFilter.length > 0 ? statusFilter.join(',') : undefined,
        search: debouncedSearch || undefined,
        sort: sortParam,
      }),
  });

  const quotes = quotesData?.items || [];
  const pagination: PaginationInfo = quotesData?.pagination || {
    page: 1,
    page_size: pageSize,
    total_items: 0,
    total_pages: 1,
    has_next: false,
    has_prev: false,
  };

  const handleConnectionChange = (value: string) => {
    setConnectionFilter(value);
    resetPagination();
  };

  const handleStatusToggle = (status: string) => {
    setStatusFilter((prev) => {
      if (prev.includes(status)) {
        return prev.filter((s) => s !== status);
      } else {
        return [...prev, status];
      }
    });
    resetPagination();
  };

  const handleClearStatuses = () => {
    setStatusFilter([]);
    resetPagination();
  };

  const renderCustomerLink = (quote: PennylaneQuote) => {
    if (quote.customer_id && quote.customer_name) {
      return (
        <Link
          to={`/pennylane/customers?pennylane_id=${encodeURIComponent(quote.customer_id)}`}
          className="text-blue-600 hover:text-blue-800 hover:underline"
          onClick={(e) => e.stopPropagation()}
        >
          {quote.customer_name}
        </Link>
      );
    }
    return quote.customer_name || '-';
  };

  const columns: ServerColumn<PennylaneQuote>[] = [
    {
      key: 'quote_number',
      header: t('quote_number', 'Quote #'),
      sortable: true,
      render: (quote) => (
        <div className="flex items-center gap-2">
          <FileCheck className="h-4 w-4 text-muted-foreground" />
          <span className="font-medium">{quote.quote_number || '-'}</span>
        </div>
      ),
    },
    {
      key: 'customer_name',
      header: t('common:customer_name', 'Customer'),
      sortable: true,
      render: renderCustomerLink,
    },
    {
      key: 'status',
      header: t('common:status', 'Status'),
      sortable: true,
      render: (quote) => (
        <Badge variant={getQuoteStatusVariant(quote.status)}>
          {quote.status ? t(`status.${quote.status}`, quote.status) : 'unknown'}
        </Badge>
      ),
    },
    {
      key: 'amount',
      header: t('amount', 'Amount'),
      sortable: true,
      className: 'text-right',
      render: (quote) =>
        quote.amount != null ? formatCurrency(quote.amount, quote.currency) : '-',
    },
    {
      key: 'currency',
      header: t('currency', 'Currency'),
      render: (quote) => quote.currency || '-',
    },
    {
      key: 'issue_date',
      header: t('issue_date', 'Issue Date'),
      sortable: true,
      render: (quote) => (quote.issue_date ? formatDate(quote.issue_date) : '-'),
    },
    {
      key: 'valid_until',
      header: t('valid_until', 'Valid Until'),
      sortable: true,
      render: (quote) => (quote.valid_until ? formatDate(quote.valid_until) : '-'),
    },
    {
      key: 'connection_name',
      header: t('connection', 'Connection'),
      render: (quote) => quote.connection_name || '-',
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">{t('quotes_title', 'Pennylane Quotes')}</h1>
          <p className="text-muted-foreground">
            {t('quotes_description', 'View synced quotes from Pennylane')}
          </p>
        </div>
      </div>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base font-medium">{t('filters', 'Filters')}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-4">
            <div className="w-64 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder={t('search_quotes', 'Search by number or customer...')}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9"
              />
            </div>
            <div className="w-48">
              <Select value={connectionFilter} onValueChange={handleConnectionChange}>
                <SelectTrigger>
                  <SelectValue placeholder={t('all_connections', 'All Connections')} />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">{t('all_connections', 'All Connections')}</SelectItem>
                  {connections?.map((conn: PennylaneConnection) => (
                    <SelectItem key={conn.id} value={conn.id}>
                      {conn.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="w-48">
              <Popover open={statusPopoverOpen} onOpenChange={setStatusPopoverOpen}>
                <PopoverTrigger asChild>
                  <Button
                    variant="outline"
                    className="w-full justify-between font-normal"
                  >
                    <span className="truncate">
                      {statusFilter.length === 0
                        ? t('all_statuses', 'All Statuses')
                        : statusFilter.length === 1
                          ? t(`status.${statusFilter[0]}`, statusFilter[0])
                          : t('selected_count', '{{count}} selected', { count: statusFilter.length })}
                    </span>
                    <ChevronDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-48 p-2" align="start">
                  <div className="space-y-2">
                    {statusFilter.length > 0 && (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="w-full justify-start text-muted-foreground"
                        onClick={handleClearStatuses}
                      >
                        <X className="mr-2 h-4 w-4" />
                        {t('clear_selection', 'Clear')}
                      </Button>
                    )}
                    {QUOTE_STATUSES.map((status) => (
                      <div
                        key={status}
                        className="flex items-center space-x-2 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800 rounded px-2 py-1"
                        onClick={() => handleStatusToggle(status)}
                      >
                        <Checkbox
                          checked={statusFilter.includes(status)}
                          onCheckedChange={() => handleStatusToggle(status)}
                        />
                        <span className="text-sm">
                          {t(`status.${status}`, status)}
                        </span>
                      </div>
                    ))}
                  </div>
                </PopoverContent>
              </Popover>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base font-medium">
            {t('quotes_list', 'Quotes')} ({pagination.total_items})
          </CardTitle>
        </CardHeader>
        <CardContent>
          <ServerDataTable
            data={quotes}
            columns={columns}
            pagination={pagination}
            sort={sort}
            isLoading={isLoading || isFetching}
            onSort={handleSort}
            onPageChange={handlePageChange}
            onPageSizeChange={handlePageSizeChange}
          />
        </CardContent>
      </Card>
    </div>
  );
};
