import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { productsApi } from '@/services/api';
import { type Product } from '@/types';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { DataTable, type Column } from '@/components/common/DataTable';
import { LoadingSpinner } from '@/components/common/LoadingSpinner';
import { Badge } from '@/components/ui/badge';
import { Plus, Pencil, Trash2 } from 'lucide-react';
import { ProductDialog } from '@/components/products/ProductDialog';

export const Products: React.FC = () => {
  const { t } = useTranslation('common');
  const queryClient = useQueryClient();
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);

  const { data: products, isLoading } = useQuery({
    queryKey: ['products'],
    queryFn: () => productsApi.getAll(),
  });

  const deleteMutation = useMutation({
    mutationFn: productsApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['products'] });
    },
  });

  const columns: Column<Product>[] = [
    {
      key: 'name',
      header: t('name'),
    },
    {
      key: 'type',
      header: t('product_type'),
    },
    {
      key: 'unit',
      header: t('unit'),
    },
    {
      key: 'description',
      header: t('description'),
      render: (product) => product.description || '-',
    },
    {
      key: 'price_tiers',
      header: t('price_tiers'),
      render: (product) => (
        <Badge variant="secondary">
          {product.price_tiers?.length || 0} {product.price_tiers?.length === 1 ? 'tier' : 'tiers'}
        </Badge>
      ),
    },
    {
      key: 'is_active',
      header: t('status'),
      render: (product) => (
        <Badge variant={product.is_active ? 'success' : 'secondary'}>
          {product.is_active ? t('active') : t('inactive')}
        </Badge>
      ),
    },
    {
      key: 'actions',
      header: t('actions'),
      render: (product) => (
        <div className="flex gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={(e) => {
              e.stopPropagation();
              setSelectedProduct(product);
              setIsDialogOpen(true);
            }}
          >
            <Pencil className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={(e) => {
              e.stopPropagation();
              if (confirm(t('delete_confirmation'))) {
                deleteMutation.mutate(product.id);
              }
            }}
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      ),
    },
  ];

  if (isLoading) {
    return <LoadingSpinner />;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">{t('products')}</h1>
          <p className="text-muted-foreground">{t('manage_product_catalog')}</p>
        </div>
        <Button
          onClick={() => {
            setSelectedProduct(null);
            setIsDialogOpen(true);
          }}
        >
          <Plus className="h-4 w-4 mr-2" />
          {t('add')} {t('products')}
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{t('products')}</CardTitle>
        </CardHeader>
        <CardContent>
          <DataTable data={products || []} columns={columns} />
        </CardContent>
      </Card>

      <ProductDialog
        product={selectedProduct}
        open={isDialogOpen}
        onOpenChange={setIsDialogOpen}
      />
    </div>
  );
};
