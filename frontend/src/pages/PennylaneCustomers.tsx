import React, { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { useSearchParams } from 'react-router-dom';
import { pennylaneApi } from '@/services/api';
import { type PennylaneCustomer, type PennylaneConnection } from '@/types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { formatDate } from '@/lib/utils';
import {
  ServerDataTable,
  useServerTableState,
  type ServerColumn,
  type PaginationInfo,
} from '@/components/common/ServerDataTable';
import { Users, Search, X } from 'lucide-react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';

const CUSTOMER_TYPES = ['individual', 'company'] as const;

export const PennylaneCustomers: React.FC = () => {
  const { t } = useTranslation(['pennylane', 'common']);
  const [searchParams, setSearchParams] = useSearchParams();

  // Initialize state from URL params
  const [connectionFilter, setConnectionFilter] = useState<string>(
    searchParams.get('connection') || 'all'
  );
  const [customerTypeFilter, setCustomerTypeFilter] = useState<string>(
    searchParams.get('type') || 'all'
  );
  const [pennylaneIdFilter, setPennylaneIdFilter] = useState<string>(
    searchParams.get('pennylane_id') || ''
  );
  const [searchQuery, setSearchQuery] = useState<string>(searchParams.get('search') || '');
  const [debouncedSearch, setDebouncedSearch] = useState<string>(searchParams.get('search') || '');
  const [selectedCustomer, setSelectedCustomer] = useState<PennylaneCustomer | null>(null);
  const [isDetailOpen, setIsDetailOpen] = useState(false);

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
    if (customerTypeFilter !== 'all') params.set('type', customerTypeFilter);
    if (pennylaneIdFilter) params.set('pennylane_id', pennylaneIdFilter);
    if (debouncedSearch) params.set('search', debouncedSearch);
    setSearchParams(params, { replace: true });
  }, [connectionFilter, customerTypeFilter, pennylaneIdFilter, debouncedSearch, setSearchParams]);

  const { data: connections } = useQuery({
    queryKey: ['pennylane-connections'],
    queryFn: () => pennylaneApi.getConnections(),
  });

  const { data: customersData, isLoading, isFetching } = useQuery({
    queryKey: [
      'pennylane-customers',
      page,
      pageSize,
      connectionFilter,
      customerTypeFilter,
      pennylaneIdFilter,
      debouncedSearch,
      sortParam,
    ],
    queryFn: () =>
      pennylaneApi.getCustomers(page, pageSize, {
        connection_id: connectionFilter !== 'all' ? connectionFilter : undefined,
        search: debouncedSearch || undefined,
        customer_type: customerTypeFilter !== 'all' ? customerTypeFilter : undefined,
        pennylane_id: pennylaneIdFilter || undefined,
        sort: sortParam,
      }),
  });

  // Ensure customers is always an array (in case API returns single object when filtering by ID)
  const customersRaw = customersData?.items;
  const customers = Array.isArray(customersRaw) ? customersRaw : customersRaw ? [customersRaw] : [];
  const pagination: PaginationInfo = customersData?.pagination || {
    page: 1,
    page_size: pageSize,
    total_items: 0,
    total_pages: 1,
    has_next: false,
    has_prev: false,
  };

  const handleRowClick = (customer: PennylaneCustomer) => {
    setSelectedCustomer(customer);
    setIsDetailOpen(true);
  };

  const handleConnectionChange = (value: string) => {
    setConnectionFilter(value);
    resetPagination();
  };

  const handleCustomerTypeChange = (value: string) => {
    setCustomerTypeFilter(value);
    resetPagination();
  };

  const columns: ServerColumn<PennylaneCustomer>[] = [
    {
      key: 'name',
      header: t('name', 'Name'),
      sortable: true,
      render: (customer) => (
        <div className="flex items-center gap-2">
          <Users className="h-4 w-4 text-muted-foreground" />
          <span className="font-medium">{customer.name || '-'}</span>
        </div>
      ),
    },
    {
      key: 'email',
      header: t('common:email', 'Email'),
      sortable: true,
      render: (customer) => customer.email || '-',
    },
    {
      key: 'phone',
      header: t('common:phone', 'Phone'),
      render: (customer) => customer.phone || '-',
    },
    {
      key: 'city',
      header: t('city', 'City'),
      sortable: true,
      render: (customer) => customer.city || '-',
    },
    {
      key: 'country_code',
      header: t('country', 'Country'),
      sortable: true,
      render: (customer) => customer.country_code || '-',
    },
    {
      key: 'customer_type',
      header: t('type', 'Type'),
      sortable: true,
      render: (customer) => (
        <span className="capitalize">{customer.customer_type || '-'}</span>
      ),
    },
    {
      key: 'connection_name',
      header: t('connection', 'Connection'),
      render: (customer) => customer.connection_name || '-',
    },
    {
      key: 'synced_at',
      header: t('synced_at', 'Synced At'),
      sortable: true,
      render: (customer) => formatDate(customer.synced_at, 'dd/MM/yyyy HH:mm'),
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">{t('customers_title', 'Pennylane Customers')}</h1>
          <p className="text-muted-foreground">
            {t('customers_description', 'View synced customers from Pennylane')}
          </p>
        </div>
      </div>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base font-medium">{t('filters', 'Filters')}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-4">
            {pennylaneIdFilter && (
              <div className="w-full flex items-center gap-2 p-2 bg-blue-50 dark:bg-blue-900/20 rounded-md text-sm text-blue-700 dark:text-blue-300">
                <span>{t('filtering_by_customer_id', 'Filtering by customer ID')}: {pennylaneIdFilter}</span>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 px-2"
                  onClick={() => setPennylaneIdFilter('')}
                >
                  <X className="h-4 w-4" />
                  {t('clear_filter', 'Clear filter')}
                </Button>
              </div>
            )}
            <div className="w-64 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder={t('search_customers', 'Search by name or email...')}
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
              <Select value={customerTypeFilter} onValueChange={handleCustomerTypeChange}>
                <SelectTrigger>
                  <SelectValue placeholder={t('all_types', 'All Types')} />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">{t('all_types', 'All Types')}</SelectItem>
                  {CUSTOMER_TYPES.map((type) => (
                    <SelectItem key={type} value={type}>
                      {type.charAt(0).toUpperCase() + type.slice(1)}
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
            {t('customers_list', 'Customers')} ({pagination.total_items})
          </CardTitle>
        </CardHeader>
        <CardContent>
          <ServerDataTable
            data={customers}
            columns={columns}
            pagination={pagination}
            sort={sort}
            isLoading={isLoading || isFetching}
            onRowClick={handleRowClick}
            onSort={handleSort}
            onPageChange={handlePageChange}
            onPageSizeChange={handlePageSizeChange}
          />
        </CardContent>
      </Card>

      <Dialog open={isDetailOpen} onOpenChange={setIsDetailOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>{t('customer_details', 'Customer Details')}</DialogTitle>
          </DialogHeader>
          {selectedCustomer && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-medium text-muted-foreground">
                    {t('name', 'Name')}
                  </label>
                  <p className="text-sm">{selectedCustomer.name || '-'}</p>
                </div>
                {selectedCustomer.first_name && (
                  <div>
                    <label className="text-sm font-medium text-muted-foreground">
                      {t('first_name', 'First Name')}
                    </label>
                    <p className="text-sm">{selectedCustomer.first_name}</p>
                  </div>
                )}
                {selectedCustomer.last_name && (
                  <div>
                    <label className="text-sm font-medium text-muted-foreground">
                      {t('last_name', 'Last Name')}
                    </label>
                    <p className="text-sm">{selectedCustomer.last_name}</p>
                  </div>
                )}
                <div>
                  <label className="text-sm font-medium text-muted-foreground">
                    {t('common:email', 'Email')}
                  </label>
                  <p className="text-sm">{selectedCustomer.email || '-'}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-muted-foreground">
                    {t('common:phone', 'Phone')}
                  </label>
                  <p className="text-sm">{selectedCustomer.phone || '-'}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-muted-foreground">
                    {t('type', 'Type')}
                  </label>
                  <p className="text-sm capitalize">{selectedCustomer.customer_type || '-'}</p>
                </div>
              </div>
              <div className="border-t pt-4">
                <h4 className="text-sm font-medium mb-3">{t('address', 'Address')}</h4>
                <div className="grid grid-cols-2 gap-4">
                  <div className="col-span-2">
                    <label className="text-sm font-medium text-muted-foreground">
                      {t('street', 'Street')}
                    </label>
                    <p className="text-sm">{selectedCustomer.address || '-'}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-muted-foreground">
                      {t('city', 'City')}
                    </label>
                    <p className="text-sm">{selectedCustomer.city || '-'}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-muted-foreground">
                      {t('postal_code', 'Postal Code')}
                    </label>
                    <p className="text-sm">{selectedCustomer.postal_code || '-'}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-muted-foreground">
                      {t('country', 'Country')}
                    </label>
                    <p className="text-sm">{selectedCustomer.country_code || '-'}</p>
                  </div>
                  {selectedCustomer.vat_number && (
                    <div>
                      <label className="text-sm font-medium text-muted-foreground">
                        {t('vat_number', 'VAT Number')}
                      </label>
                      <p className="text-sm">{selectedCustomer.vat_number}</p>
                    </div>
                  )}
                </div>
              </div>
              <div className="border-t pt-4">
                <h4 className="text-sm font-medium mb-3">{t('business_information', 'Informations commerciales')}</h4>
                <div className="grid grid-cols-2 gap-4">
                  {selectedCustomer.reg_no && (
                    <div>
                      <label className="text-sm font-medium text-muted-foreground">
                        {t('reg_no', 'N° SIRET/SIREN')}
                      </label>
                      <p className="text-sm">{selectedCustomer.reg_no}</p>
                    </div>
                  )}
                  {selectedCustomer.billing_iban && (
                    <div>
                      <label className="text-sm font-medium text-muted-foreground">
                        {t('billing_iban', 'IBAN')}
                      </label>
                      <p className="text-sm">{selectedCustomer.billing_iban}</p>
                    </div>
                  )}
                  <div>
                    <label className="text-sm font-medium text-muted-foreground">
                      {t('billing_language', 'Langue')}
                    </label>
                    <p className="text-sm">{selectedCustomer.billing_language || '-'}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-muted-foreground">
                      {t('payment_conditions', 'Conditions de paiement')}
                    </label>
                    <p className="text-sm">{selectedCustomer.payment_conditions || '-'}</p>
                  </div>
                  {selectedCustomer.reference && (
                    <div>
                      <label className="text-sm font-medium text-muted-foreground">
                        {t('reference', 'Référence')}
                      </label>
                      <p className="text-sm">{selectedCustomer.reference}</p>
                    </div>
                  )}
                  {selectedCustomer.external_reference && (
                    <div>
                      <label className="text-sm font-medium text-muted-foreground">
                        {t('external_reference', 'Réf. externe')}
                      </label>
                      <p className="text-sm">{selectedCustomer.external_reference}</p>
                    </div>
                  )}
                </div>
              </div>
              {(selectedCustomer.delivery_address || selectedCustomer.delivery_city || selectedCustomer.delivery_postal_code || selectedCustomer.delivery_country_code) && (
                <div className="border-t pt-4">
                  <h4 className="text-sm font-medium mb-3">{t('delivery_address', 'Adresse de livraison')}</h4>
                  <div className="grid grid-cols-2 gap-4">
                    {selectedCustomer.delivery_address && (
                      <div className="col-span-2">
                        <label className="text-sm font-medium text-muted-foreground">
                          {t('street', 'Street')}
                        </label>
                        <p className="text-sm">{selectedCustomer.delivery_address}</p>
                      </div>
                    )}
                    {selectedCustomer.delivery_city && (
                      <div>
                        <label className="text-sm font-medium text-muted-foreground">
                          {t('city', 'City')}
                        </label>
                        <p className="text-sm">{selectedCustomer.delivery_city}</p>
                      </div>
                    )}
                    {selectedCustomer.delivery_postal_code && (
                      <div>
                        <label className="text-sm font-medium text-muted-foreground">
                          {t('postal_code', 'Postal Code')}
                        </label>
                        <p className="text-sm">{selectedCustomer.delivery_postal_code}</p>
                      </div>
                    )}
                    {selectedCustomer.delivery_country_code && (
                      <div>
                        <label className="text-sm font-medium text-muted-foreground">
                          {t('country', 'Country')}
                        </label>
                        <p className="text-sm">{selectedCustomer.delivery_country_code}</p>
                      </div>
                    )}
                  </div>
                </div>
              )}
              <div className="border-t pt-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm font-medium text-muted-foreground">
                      {t('connection', 'Connection')}
                    </label>
                    <p className="text-sm">{selectedCustomer.connection_name || '-'}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-muted-foreground">
                      {t('synced_at', 'Synced At')}
                    </label>
                    <p className="text-sm">
                      {formatDate(selectedCustomer.synced_at, 'dd/MM/yyyy HH:mm')}
                    </p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-muted-foreground">
                      {t('pennylane_id', 'Pennylane ID')}
                    </label>
                    <p className="text-sm font-mono text-xs">{selectedCustomer.pennylane_id}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-muted-foreground">
                      {t('pennylane_created_at', 'Créé dans Pennylane')}
                    </label>
                    <p className="text-sm">
                      {formatDate(selectedCustomer.pennylane_created_at, 'dd/MM/yyyy')}
                    </p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-muted-foreground">
                      {t('pennylane_updated_at', 'Modifié dans Pennylane')}
                    </label>
                    <p className="text-sm">
                      {formatDate(selectedCustomer.pennylane_updated_at, 'dd/MM/yyyy')}
                    </p>
                  </div>
                  {selectedCustomer.notes && (
                    <div className="col-span-2">
                      <label className="text-sm font-medium text-muted-foreground">
                        {t('notes', 'Notes')}
                      </label>
                      <p className="text-sm whitespace-pre-wrap">{selectedCustomer.notes}</p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};
