import { api } from '@/services/api';
import type { ProductType } from '@/types';

export const productTypesApi = {
  getAll: async (skip = 0, limit = 100): Promise<ProductType[]> => {
    const response = await api.get<{ items: ProductType[]; pagination: any } | ProductType[]>(
      '/api/v1/product-types',
      {
        params: { skip, limit },
      }
    );
    return Array.isArray(response.data)
      ? response.data
      : response.data.items !== undefined
      ? response.data.items
      : [];
  },

  getById: async (id: string): Promise<ProductType> => {
    const response = await api.get<ProductType>(`/api/v1/product-types/${id}`);
    return response.data;
  },

  create: async (data: Partial<ProductType>): Promise<ProductType> => {
    const response = await api.post<ProductType>('/api/v1/product-types', data);
    return response.data;
  },

  update: async (id: string, data: Partial<ProductType>): Promise<ProductType> => {
    const response = await api.put<ProductType>(`/api/v1/product-types/${id}`, data);
    return response.data;
  },

  delete: async (id: string): Promise<void> => {
    await api.delete(`/api/v1/product-types/${id}`);
  },
};
