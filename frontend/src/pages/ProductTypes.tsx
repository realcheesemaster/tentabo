import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { productTypesApi } from '@/api/productTypes';
import { type ProductType } from '@/types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { LoadingSpinner } from '@/components/common/LoadingSpinner';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { formatDate } from '@/lib/utils';
import { DataTable, type Column } from '@/components/common/DataTable';
import { Plus, Edit, Trash2 } from 'lucide-react';
import { useToast } from '@/components/ui/use-toast';
import { ProductTypeDialog } from '@/components/product-types/ProductTypeDialog';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';

export const ProductTypes: React.FC = () => {
  const { t } = useTranslation('common');
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [editingProductType, setEditingProductType] = useState<ProductType | null>(null);
  const [deletingProductType, setDeletingProductType] = useState<ProductType | null>(null);

  const { data: productTypes, isLoading } = useQuery({
    queryKey: ['product-types'],
    queryFn: () => productTypesApi.getAll(),
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (id: string) => productTypesApi.delete(id),
    onSuccess: () => {
      toast({
        title: t('success'),
        description: t('product_type_deleted_successfully'),
      });
      queryClient.invalidateQueries({ queryKey: ['product-types'] });
      setDeleteDialogOpen(false);
      setDeletingProductType(null);
    },
    onError: (error: any) => {
      toast({
        title: t('error'),
        description: error.response?.data?.detail || t('failed_to_delete_product_type'),
        variant: 'destructive',
      });
    },
  });

  const handleAdd = () => {
    setEditingProductType(null);
    setDialogOpen(true);
  };

  const handleEdit = (productType: ProductType) => {
    setEditingProductType(productType);
    setDialogOpen(true);
  };

  const handleDelete = (productType: ProductType) => {
    setDeletingProductType(productType);
    setDeleteDialogOpen(true);
  };

  const columns: Column<ProductType>[] = [
    {
      key: 'name',
      header: t('product_type_name'),
    },
    {
      key: 'description',
      header: t('description'),
      render: (productType) => productType.description || '-',
    },
    {
      key: 'is_active',
      header: t('status'),
      render: (productType) => (
        <Badge variant={productType.is_active ? 'success' : 'secondary'}>
          {productType.is_active ? t('active') : t('inactive')}
        </Badge>
      ),
    },
    {
      key: 'created_at',
      header: t('created_at'),
      render: (productType) => formatDate(productType.created_at),
    },
    {
      key: 'actions',
      header: t('actions'),
      render: (productType) => (
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={() => handleEdit(productType)}
          >
            <Edit className="h-4 w-4" />
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => handleDelete(productType)}
          >
            <Trash2 className="h-4 w-4 text-destructive" />
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
          <h1 className="text-3xl font-bold">{t('product_types')}</h1>
          <p className="text-muted-foreground">{t('manage_product_types')}</p>
        </div>
        <Button onClick={handleAdd}>
          <Plus className="h-4 w-4 mr-2" />
          {t('add_product_type')}
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{t('product_types')}</CardTitle>
        </CardHeader>
        <CardContent>
          <DataTable data={productTypes || []} columns={columns} />
        </CardContent>
      </Card>

      {/* ProductType Dialog */}
      <ProductTypeDialog
        productType={editingProductType}
        open={dialogOpen}
        onOpenChange={(open) => {
          setDialogOpen(open);
          if (!open) {
            setEditingProductType(null);
          }
        }}
      />

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t('confirm_deletion')}</AlertDialogTitle>
            <AlertDialogDescription>
              {t('are_you_sure_delete_product_type', { name: deletingProductType?.name })}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t('cancel')}</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => deletingProductType && deleteMutation.mutate(deletingProductType.id)}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {t('delete')}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};
