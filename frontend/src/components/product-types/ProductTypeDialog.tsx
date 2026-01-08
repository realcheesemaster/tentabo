import React, { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { productTypesApi } from '@/api/productTypes';
import { type ProductType } from '@/types';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { useToast } from '@/components/ui/use-toast';

interface ProductTypeFormData {
  name: string;
  description: string;
  is_active: boolean;
}

interface ProductTypeDialogProps {
  productType: ProductType | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export const ProductTypeDialog: React.FC<ProductTypeDialogProps> = ({
  productType,
  open,
  onOpenChange,
}) => {
  const { t } = useTranslation('common');
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const { register, handleSubmit, reset, setValue, watch } = useForm<ProductTypeFormData>({
    defaultValues: {
      name: '',
      description: '',
      is_active: true,
    },
  });

  const isActive = watch('is_active');

  useEffect(() => {
    if (productType) {
      reset({
        name: productType.name,
        description: productType.description || '',
        is_active: productType.is_active,
      });
    } else {
      reset({
        name: '',
        description: '',
        is_active: true,
      });
    }
  }, [productType, reset, open]);

  // Create mutation
  const createMutation = useMutation({
    mutationFn: (data: Partial<ProductType>) => productTypesApi.create(data),
    onSuccess: () => {
      toast({
        title: t('success'),
        description: t('product_type_created_successfully'),
      });
      queryClient.invalidateQueries({ queryKey: ['product-types'] });
      onOpenChange(false);
    },
    onError: (error: any) => {
      toast({
        title: t('error'),
        description: error.response?.data?.detail || t('failed_to_create_product_type'),
        variant: 'destructive',
      });
    },
  });

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<ProductType> }) =>
      productTypesApi.update(id, data),
    onSuccess: () => {
      toast({
        title: t('success'),
        description: t('product_type_updated_successfully'),
      });
      queryClient.invalidateQueries({ queryKey: ['product-types'] });
      onOpenChange(false);
    },
    onError: (error: any) => {
      toast({
        title: t('error'),
        description: error.response?.data?.detail || t('failed_to_update_product_type'),
        variant: 'destructive',
      });
    },
  });

  const onSubmit = (data: ProductTypeFormData) => {
    const submitData = {
      ...data,
      description: data.description || undefined,
    };

    if (productType) {
      updateMutation.mutate({ id: productType.id, data: submitData });
    } else {
      createMutation.mutate(submitData);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>
            {productType ? t('edit_product_type') : t('add_product_type')}
          </DialogTitle>
          <DialogDescription>
            {productType
              ? t('update_product_type_information')
              : t('create_new_product_type')}
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit(onSubmit)}>
          <div className="grid gap-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="name">
                {t('product_type_name')} <span className="text-destructive">*</span>
              </Label>
              <Input
                id="name"
                {...register('name', { required: true })}
                placeholder={t('product_type_name')}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="description">{t('product_type_description')}</Label>
              <Input
                id="description"
                {...register('description')}
                placeholder={t('product_type_description')}
              />
            </div>
            <div className="flex items-center space-x-2">
              <Switch
                id="is_active"
                checked={isActive}
                onCheckedChange={(checked) => setValue('is_active', checked)}
              />
              <Label htmlFor="is_active">{t('active')}</Label>
            </div>
          </div>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
            >
              {t('cancel')}
            </Button>
            <Button
              type="submit"
              disabled={createMutation.isPending || updateMutation.isPending}
            >
              {productType ? t('update') : t('create')}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};
