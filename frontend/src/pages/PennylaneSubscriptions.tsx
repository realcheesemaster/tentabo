import React, { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { useSearchParams, Link } from 'react-router-dom';
import { pennylaneApi } from '@/services/api';
import { type PennylaneSubscription, type PennylaneConnection } from '@/types';
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
import { RefreshCw, Search, ChevronDown, X } from 'lucide-react';
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

const SUBSCRIPTION_STATUSES = ['active', 'in_progress', 'not_started', 'paused', 'stopped', 'cancelled'] as const;
const SUBSCRIPTION_INTERVALS = ['monthly', 'yearly'] as const;

const getSubscriptionStatusVariant = (status?: string): "default" | "secondary" | "destructive" | "outline" | "success" | "warning" | "info" => {
  switch (status?.toLowerCase()) {
    case 'active':
      return 'success';
    case 'in_progress':
      return 'info';
    case 'not_started':
      return 'warning';
    case 'paused':
      return 'secondary';
    case 'stopped':
    case 'cancelled':
      return 'destructive';
    default:
      return 'outline';
  }
};

export const PennylaneSubscriptions: React.FC = () => {
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
  const [intervalFilter, setIntervalFilter] = useState<string>(
    searchParams.get('interval') || 'all'
  );
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
    if (intervalFilter !== 'all') params.set('interval', intervalFilter);
    if (debouncedSearch) params.set('search', debouncedSearch);
    setSearchParams(params, { replace: true });
  }, [connectionFilter, statusFilter, intervalFilter, debouncedSearch, setSearchParams]);

  const { data: connections } = useQuery({
    queryKey: ['pennylane-connections'],
    queryFn: () => pennylaneApi.getConnections(),
  });

  const { data: subscriptionsData, isLoading, isFetching } = useQuery({
    queryKey: [
      'pennylane-subscriptions',
      page,
      pageSize,
      connectionFilter,
      statusFilter,
      intervalFilter,
      debouncedSearch,
      sortParam,
    ],
    queryFn: () =>
      pennylaneApi.getSubscriptions(page, pageSize, {
        connection_id: connectionFilter !== 'all' ? connectionFilter : undefined,
        status: statusFilter.length > 0 ? statusFilter.join(',') : undefined,
        interval: intervalFilter !== 'all' ? intervalFilter : undefined,
        search: debouncedSearch || undefined,
        sort: sortParam,
      }),
  });

  const subscriptions = subscriptionsData?.items || [];
  const pagination: PaginationInfo = subscriptionsData?.pagination || {
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

  const handleIntervalChange = (value: string) => {
    setIntervalFilter(value);
    resetPagination();
  };

  const renderCustomerLink = (subscription: PennylaneSubscription) => {
    if (subscription.customer_id && subscription.customer_name) {
      return (
        <div className="flex items-center gap-2">
          <RefreshCw className="h-4 w-4 text-muted-foreground" />
          <Link
            to={`/pennylane/customers?pennylane_id=${encodeURIComponent(subscription.customer_id)}`}
            className="text-blue-600 hover:text-blue-800 hover:underline font-medium"
            onClick={(e) => e.stopPropagation()}
          >
            {subscription.customer_name}
          </Link>
        </div>
      );
    }
    return (
      <div className="flex items-center gap-2">
        <RefreshCw className="h-4 w-4 text-muted-foreground" />
        <span className="font-medium">{subscription.customer_name || '-'}</span>
      </div>
    );
  };

  const columns: ServerColumn<PennylaneSubscription>[] = [
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
      render: (subscription) => (
        <Badge variant={getSubscriptionStatusVariant(subscription.status)}>
          {subscription.status ? t(`status.${subscription.status}`, subscription.status) : 'unknown'}
        </Badge>
      ),
    },
    {
      key: 'amount',
      header: t('amount', 'Amount'),
      sortable: true,
      className: 'text-right',
      render: (subscription) =>
        subscription.amount != null
          ? formatCurrency(subscription.amount, subscription.currency)
          : '-',
    },
    {
      key: 'currency',
      header: t('currency', 'Currency'),
      render: (subscription) => subscription.currency || '-',
    },
    {
      key: 'interval',
      header: t('interval', 'Interval'),
      sortable: true,
      render: (subscription) => (
        <span className="capitalize">{subscription.interval || '-'}</span>
      ),
    },
    {
      key: 'start_date',
      header: t('start_date', 'Start Date'),
      sortable: true,
      render: (subscription) =>
        subscription.start_date ? formatDate(subscription.start_date) : '-',
    },
    {
      key: 'next_billing_date',
      header: t('next_billing', 'Next Billing'),
      sortable: true,
      render: (subscription) =>
        subscription.next_billing_date ? formatDate(subscription.next_billing_date) : '-',
    },
    {
      key: 'connection_name',
      header: t('connection', 'Connection'),
      render: (subscription) => subscription.connection_name || '-',
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">
            {t('subscriptions_title', 'Pennylane Subscriptions')}
          </h1>
          <p className="text-muted-foreground">
            {t('subscriptions_description', 'View synced subscriptions from Pennylane')}
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
                placeholder={t('search_subscriptions', 'Search by customer name...')}
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
                    {SUBSCRIPTION_STATUSES.map((status) => (
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
            <div className="w-40">
              <Select value={intervalFilter} onValueChange={handleIntervalChange}>
                <SelectTrigger>
                  <SelectValue placeholder={t('all_intervals', 'All Intervals')} />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">{t('all_intervals', 'All Intervals')}</SelectItem>
                  {SUBSCRIPTION_INTERVALS.map((interval) => (
                    <SelectItem key={interval} value={interval}>
                      {interval.charAt(0).toUpperCase() + interval.slice(1)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base font-medium">
            {t('subscriptions_list', 'Subscriptions')} ({pagination.total_items})
          </CardTitle>
        </CardHeader>
        <CardContent>
          <ServerDataTable
            data={subscriptions}
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
