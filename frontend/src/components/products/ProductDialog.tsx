import React, { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { useMutation, useQueryClient, useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { productsApi } from '@/services/api';
import { productTypesApi } from '@/api/productTypes';
import { type Product, type PriceTier } from '@/types';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

interface ProductFormData {
  name: string;
  type_id: string;
  unit: string;
  description?: string;
  is_active: boolean;
}

interface ProductDialogProps {
  product: Product | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export const ProductDialog: React.FC<ProductDialogProps> = ({
  product,
  open,
  onOpenChange,
}) => {
  const { t } = useTranslation('common');
  const queryClient = useQueryClient();
  const { register, handleSubmit, reset, setValue, watch } = useForm<ProductFormData>();

  const [priceTiers, setPriceTiers] = useState<PriceTier[]>([]);

  // Fetch product types for dropdown
  const { data: productTypes, isLoading: isLoadingTypes } = useQuery({
    queryKey: ['product-types'],
    queryFn: () => productTypesApi.getAll(),
  });

  const selectedTypeId = watch('type_id');
  const [editingTier, setEditingTier] = useState<PriceTier | null>(null);
  const [tierFormData, setTierFormData] = useState<Partial<PriceTier>>({
    min_quantity: 1,
    max_quantity: null,
    price_per_unit: '',
    period: 'month',
  });
  const [validationError, setValidationError] = useState<string>('');

  useEffect(() => {
    if (product) {
      reset({
        name: product.name,
        type_id: product.type_id,
        unit: product.unit,
        description: product.description || '',
        is_active: product.is_active,
      });
      setPriceTiers(product.price_tiers || []);
    } else {
      reset({
        name: '',
        type_id: '',
        unit: '',
        description: '',
        is_active: true,
      });
      setPriceTiers([]);
    }
    setEditingTier(null);
    setValidationError('');
  }, [product, reset, open]);

  const mutation = useMutation({
    mutationFn: (data: Partial<Product>) =>
      product ? productsApi.update(product.id, data) : productsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['products'] });
      onOpenChange(false);
    },
  });

  const validateTier = (tier: Partial<PriceTier>, isEditing: boolean = false): string | null => {
    // Validate required fields
    if (!tier.min_quantity || tier.min_quantity < 1) {
      return t('tier_min_quantity_required');
    }
    if (!tier.price_per_unit || parseFloat(tier.price_per_unit) <= 0) {
      return t('tier_price_required');
    }
    if (tier.max_quantity !== null && tier.max_quantity !== undefined) {
      if (tier.max_quantity <= tier.min_quantity) {
        return t('tier_max_greater_than_min');
      }
    }

    // Validate no overlaps or gaps with other tiers
    const otherTiers = isEditing && editingTier
      ? priceTiers.filter(t => t !== editingTier)
      : priceTiers;

    for (const existingTier of otherTiers) {
      const newMin = tier.min_quantity;
      const newMax = tier.max_quantity;
      const existingMin = existingTier.min_quantity;
      const existingMax = existingTier.max_quantity;

      // Check for overlap
      if (newMax === null || newMax === undefined) {
        // New tier goes to infinity
        if (existingMax === null || existingMax === undefined || existingMax >= newMin) {
          return t('tier_overlap_detected');
        }
      } else {
        if (existingMax === null || existingMax === undefined) {
          // Existing tier goes to infinity
          if (newMax >= existingMin) {
            return t('tier_overlap_detected');
          }
        } else {
          // Both have max values
          if (!(newMax < existingMin || newMin > existingMax)) {
            return t('tier_overlap_detected');
          }
        }
      }
    }

    return null;
  };

  const handleAddOrUpdateTier = () => {
    const validationResult = validateTier(tierFormData as PriceTier, !!editingTier);
    if (validationResult) {
      setValidationError(validationResult);
      return;
    }

    const newTier: PriceTier = {
      min_quantity: tierFormData.min_quantity!,
      max_quantity: tierFormData.max_quantity,
      price_per_unit: tierFormData.price_per_unit!,
      period: tierFormData.period as 'month' | 'year',
    };

    if (editingTier) {
      // Update existing tier
      setPriceTiers(priceTiers.map(tier => tier === editingTier ? newTier : tier));
      setEditingTier(null);
    } else {
      // Add new tier
      setPriceTiers([...priceTiers, newTier]);
    }

    // Reset form
    setTierFormData({
      min_quantity: 1,
      max_quantity: null,
      price_per_unit: '',
      period: 'month',
    });
    setValidationError('');
  };

  const handleEditTier = (tier: PriceTier) => {
    setEditingTier(tier);
    setTierFormData({
      min_quantity: tier.min_quantity,
      max_quantity: tier.max_quantity,
      price_per_unit: tier.price_per_unit,
      period: tier.period,
    });
    setValidationError('');
  };

  const handleDeleteTier = (tier: PriceTier) => {
    setPriceTiers(priceTiers.filter(t => t !== tier));
    if (editingTier === tier) {
      setEditingTier(null);
      setTierFormData({
        min_quantity: 1,
        max_quantity: null,
        price_per_unit: '',
        period: 'month',
      });
    }
  };

  const handleCancelEdit = () => {
    setEditingTier(null);
    setTierFormData({
      min_quantity: 1,
      max_quantity: null,
      price_per_unit: '',
      period: 'month',
    });
    setValidationError('');
  };

  const onSubmit = (data: ProductFormData) => {
    const productData: Partial<Product> = {
      ...data,
      price_tiers: priceTiers,
    };
    mutation.mutate(productData);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{product ? t('edit_product') : t('add_product')}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="name">{t('name')}</Label>
              <Input id="name" {...register('name', { required: true })} />
            </div>
            <div>
              <Label htmlFor="type_id">{t('product_type')}</Label>
              {isLoadingTypes ? (
                <Input disabled value={t('loading')} />
              ) : (
                <Select
                  value={selectedTypeId}
                  onValueChange={(value) => setValue('type_id', value)}
                >
                  <SelectTrigger className="text-gray-900 dark:text-gray-100">
                    <SelectValue placeholder={t('select_product_type')} />
                  </SelectTrigger>
                  <SelectContent className="bg-popover text-popover-foreground">
                    {productTypes?.map((type) => (
                      <SelectItem
                        key={type.id}
                        value={type.id}
                        className="text-gray-900 dark:text-gray-100"
                      >
                        {type.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            </div>
            <div>
              <Label htmlFor="unit">{t('unit')}</Label>
              <Input id="unit" {...register('unit', { required: true })} />
            </div>
            <div className="flex items-center gap-2">
              <Label htmlFor="is_active">{t('active')}</Label>
              <input
                id="is_active"
                type="checkbox"
                {...register('is_active')}
                className="h-4 w-4"
              />
            </div>
          </div>
          <div>
            <Label htmlFor="description">{t('description')}</Label>
            <Input id="description" {...register('description')} />
          </div>

          {/* Price Tiers Section */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold">{t('price_tiers')}</h3>
            </div>

            {/* Price Tiers Table */}
            {priceTiers.length > 0 && (
              <div className="border rounded-md">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>{t('min_quantity')}</TableHead>
                      <TableHead>{t('max_quantity')}</TableHead>
                      <TableHead>{t('price_per_unit')}</TableHead>
                      <TableHead>{t('period')}</TableHead>
                      <TableHead>{t('actions')}</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {priceTiers.map((tier, index) => (
                      <TableRow key={index}>
                        <TableCell>{tier.min_quantity}</TableCell>
                        <TableCell>
                          {tier.max_quantity === null || tier.max_quantity === undefined
                            ? t('unlimited')
                            : tier.max_quantity}
                        </TableCell>
                        <TableCell>{tier.price_per_unit}</TableCell>
                        <TableCell>{tier.period === 'month' ? t('month') : t('year')}</TableCell>
                        <TableCell>
                          <div className="flex gap-2">
                            <Button
                              type="button"
                              variant="outline"
                              size="sm"
                              onClick={() => handleEditTier(tier)}
                            >
                              {t('edit')}
                            </Button>
                            <Button
                              type="button"
                              variant="outline"
                              size="sm"
                              onClick={() => handleDeleteTier(tier)}
                            >
                              {t('delete')}
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}

            {/* Add/Edit Price Tier Form */}
            <div className="border rounded-md p-4 space-y-4">
              <h4 className="font-medium">
                {editingTier ? t('edit_tier') : t('add_tier')}
              </h4>
              {validationError && (
                <div className="text-sm text-red-600 bg-red-50 p-2 rounded">
                  {validationError}
                </div>
              )}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="tier_min_quantity">{t('min_quantity')}</Label>
                  <Input
                    id="tier_min_quantity"
                    type="number"
                    min="1"
                    value={tierFormData.min_quantity || ''}
                    onChange={(e) =>
                      setTierFormData({
                        ...tierFormData,
                        min_quantity: parseInt(e.target.value) || 1,
                      })
                    }
                  />
                </div>
                <div>
                  <Label htmlFor="tier_max_quantity">
                    {t('max_quantity')} ({t('optional_unlimited')})
                  </Label>
                  <Input
                    id="tier_max_quantity"
                    type="number"
                    min="1"
                    value={tierFormData.max_quantity || ''}
                    onChange={(e) =>
                      setTierFormData({
                        ...tierFormData,
                        max_quantity: e.target.value ? parseInt(e.target.value) : null,
                      })
                    }
                    placeholder={t('unlimited')}
                  />
                </div>
                <div>
                  <Label htmlFor="tier_price">{t('price_per_unit')}</Label>
                  <Input
                    id="tier_price"
                    type="text"
                    value={tierFormData.price_per_unit || ''}
                    onChange={(e) =>
                      setTierFormData({
                        ...tierFormData,
                        price_per_unit: e.target.value,
                      })
                    }
                    placeholder="0.00"
                  />
                </div>
                <div>
                  <Label htmlFor="tier_period">{t('period')}</Label>
                  <Select
                    value={tierFormData.period || 'month'}
                    onValueChange={(value) =>
                      setTierFormData({
                        ...tierFormData,
                        period: value as 'month' | 'year',
                      })
                    }
                  >
                    <SelectTrigger className="text-gray-900 dark:text-gray-100">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="bg-popover text-popover-foreground">
                      <SelectItem value="month" className="text-gray-900 dark:text-gray-100">
                        {t('month')}
                      </SelectItem>
                      <SelectItem value="year" className="text-gray-900 dark:text-gray-100">
                        {t('year')}
                      </SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="flex gap-2">
                <Button type="button" onClick={handleAddOrUpdateTier}>
                  {editingTier ? t('update_tier') : t('add_tier')}
                </Button>
                {editingTier && (
                  <Button type="button" variant="outline" onClick={handleCancelEdit}>
                    {t('cancel')}
                  </Button>
                )}
              </div>
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-4 border-t">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              {t('cancel')}
            </Button>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? t('saving') : t('save')}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
};
