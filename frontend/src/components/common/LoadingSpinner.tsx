import React from 'react';
import { Loader2 } from 'lucide-react';

export const LoadingSpinner: React.FC<{ className?: string }> = ({ className = "h-8 w-8" }) => {
  return (
    <div className="flex items-center justify-center p-8">
      <Loader2 className={`animate-spin ${className}`} />
    </div>
  );
};
