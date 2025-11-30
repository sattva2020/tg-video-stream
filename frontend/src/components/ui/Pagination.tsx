import React from 'react';
import { Button } from '@heroui/react';
import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from 'lucide-react';
import { useTranslation } from 'react-i18next';

interface PaginationProps {
  page: number;
  totalPages: number;
  total: number;
  pageSize: number;
  hasNext: boolean;
  hasPrev: boolean;
  onPageChange: (page: number) => void;
  onPageSizeChange?: (size: number) => void;
  pageSizeOptions?: number[];
  isLoading?: boolean;
  className?: string;
}

export const Pagination: React.FC<PaginationProps> = ({
  page,
  totalPages,
  total,
  pageSize,
  hasNext,
  hasPrev,
  onPageChange,
  onPageSizeChange,
  pageSizeOptions = [10, 20, 50],
  isLoading = false,
  className = '',
}) => {
  const { t } = useTranslation();

  // Generate page numbers to show
  const getPageNumbers = () => {
    const pages: (number | 'ellipsis')[] = [];
    const maxVisible = 5;
    
    if (totalPages <= maxVisible) {
      for (let i = 1; i <= totalPages; i++) {
        pages.push(i);
      }
    } else {
      // Always show first page
      pages.push(1);
      
      if (page > 3) {
        pages.push('ellipsis');
      }
      
      // Show pages around current
      const start = Math.max(2, page - 1);
      const end = Math.min(totalPages - 1, page + 1);
      
      for (let i = start; i <= end; i++) {
        if (!pages.includes(i)) {
          pages.push(i);
        }
      }
      
      if (page < totalPages - 2) {
        pages.push('ellipsis');
      }
      
      // Always show last page
      if (!pages.includes(totalPages)) {
        pages.push(totalPages);
      }
    }
    
    return pages;
  };

  const startItem = (page - 1) * pageSize + 1;
  const endItem = Math.min(page * pageSize, total);

  return (
    <div className={`flex flex-col sm:flex-row items-center justify-between gap-4 ${className}`}>
      {/* Info */}
      <div className="text-sm text-[color:var(--color-text-muted)] order-2 sm:order-1">
        {t('pagination.showing', 'Показано')} {startItem}–{endItem} {t('pagination.of', 'из')} {total}
      </div>

      {/* Pagination controls */}
      <div className="flex items-center gap-1 order-1 sm:order-2">
        {/* First page */}
        <Button
          size="sm"
          variant="flat"
          isIconOnly
          isDisabled={!hasPrev || isLoading}
          onPress={() => onPageChange(1)}
          aria-label={t('pagination.first', 'Первая страница')}
        >
          <ChevronsLeft className="w-4 h-4" />
        </Button>

        {/* Previous page */}
        <Button
          size="sm"
          variant="flat"
          isIconOnly
          isDisabled={!hasPrev || isLoading}
          onPress={() => onPageChange(page - 1)}
          aria-label={t('pagination.prev', 'Предыдущая')}
        >
          <ChevronLeft className="w-4 h-4" />
        </Button>

        {/* Page numbers - hidden on mobile */}
        <div className="hidden sm:flex items-center gap-1">
          {getPageNumbers().map((p, idx) => (
            p === 'ellipsis' ? (
              <span key={`ellipsis-${idx}`} className="px-2 text-[color:var(--color-text-muted)]">
                …
              </span>
            ) : (
              <Button
                key={p}
                size="sm"
                variant={p === page ? 'solid' : 'flat'}
                color={p === page ? 'primary' : 'default'}
                isDisabled={isLoading}
                onPress={() => onPageChange(p)}
                className="min-w-[32px]"
              >
                {p}
              </Button>
            )
          ))}
        </div>

        {/* Current page indicator - mobile only */}
        <span className="sm:hidden px-3 text-sm text-[color:var(--color-text)]">
          {page} / {totalPages}
        </span>

        {/* Next page */}
        <Button
          size="sm"
          variant="flat"
          isIconOnly
          isDisabled={!hasNext || isLoading}
          onPress={() => onPageChange(page + 1)}
          aria-label={t('pagination.next', 'Следующая')}
        >
          <ChevronRight className="w-4 h-4" />
        </Button>

        {/* Last page */}
        <Button
          size="sm"
          variant="flat"
          isIconOnly
          isDisabled={!hasNext || isLoading}
          onPress={() => onPageChange(totalPages)}
          aria-label={t('pagination.last', 'Последняя страница')}
        >
          <ChevronsRight className="w-4 h-4" />
        </Button>
      </div>

      {/* Page size selector */}
      {onPageSizeChange && (
        <div className="flex items-center gap-2 order-3">
          <span className="text-sm text-[color:var(--color-text-muted)] hidden sm:inline">
            {t('pagination.perPage', 'На странице')}:
          </span>
          <select
            value={pageSize}
            onChange={(e) => onPageSizeChange(Number(e.target.value))}
            disabled={isLoading}
            className="text-sm border border-[color:var(--color-border)] bg-[color:var(--color-surface)] text-[color:var(--color-text)] rounded-lg px-2 py-1"
          >
            {pageSizeOptions.map((size) => (
              <option key={size} value={size}>
                {size}
              </option>
            ))}
          </select>
        </div>
      )}
    </div>
  );
};
