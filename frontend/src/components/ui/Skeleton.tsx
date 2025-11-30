import React from 'react';
import clsx from 'clsx';

interface SkeletonProps {
  className?: string;
  /** Width of the skeleton (can be Tailwind class like 'w-full' or CSS value) */
  width?: string;
  /** Height of the skeleton (can be Tailwind class like 'h-4' or CSS value) */
  height?: string;
  /** Whether to use rounded corners */
  rounded?: 'none' | 'sm' | 'md' | 'lg' | 'xl' | 'full';
  /** Animation variant */
  animation?: 'pulse' | 'shimmer' | 'none';
}

/**
 * Base skeleton component for loading states
 * 
 * @example
 * <Skeleton className="w-32 h-4" />
 * <Skeleton width="100%" height="20px" rounded="lg" />
 */
export const Skeleton: React.FC<SkeletonProps> = ({
  className,
  width,
  height,
  rounded = 'md',
  animation = 'pulse',
}) => {
  const roundedClasses = {
    none: '',
    sm: 'rounded-sm',
    md: 'rounded-md',
    lg: 'rounded-lg',
    xl: 'rounded-xl',
    full: 'rounded-full',
  };

  const animationClasses = {
    pulse: 'animate-pulse',
    shimmer: 'animate-shimmer bg-gradient-to-r from-transparent via-white/10 to-transparent bg-[length:200%_100%]',
    none: '',
  };

  const style: React.CSSProperties = {};
  if (width && !width.startsWith('w-')) style.width = width;
  if (height && !height.startsWith('h-')) style.height = height;

  return (
    <div
      className={clsx(
        'bg-gray-200 dark:bg-gray-700',
        roundedClasses[rounded],
        animationClasses[animation],
        width?.startsWith('w-') && width,
        height?.startsWith('h-') && height,
        className
      )}
      style={Object.keys(style).length > 0 ? style : undefined}
      aria-hidden="true"
    />
  );
};

/**
 * Skeleton for text lines
 */
export const SkeletonText: React.FC<{ lines?: number; className?: string }> = ({
  lines = 1,
  className,
}) => (
  <div className={clsx('space-y-2', className)}>
    {Array.from({ length: lines }).map((_, i) => (
      <Skeleton
        key={i}
        className={clsx('h-4', i === lines - 1 && lines > 1 ? 'w-3/4' : 'w-full')}
      />
    ))}
  </div>
);

/**
 * Skeleton for avatar/profile pictures
 */
export const SkeletonAvatar: React.FC<{ size?: 'sm' | 'md' | 'lg'; className?: string }> = ({
  size = 'md',
  className,
}) => {
  const sizeClasses = {
    sm: 'w-8 h-8',
    md: 'w-10 h-10',
    lg: 'w-12 h-12',
  };

  return <Skeleton className={clsx(sizeClasses[size], className)} rounded="full" />;
};

/**
 * Skeleton for card content
 */
export const SkeletonCard: React.FC<{ className?: string }> = ({ className }) => (
  <div className={clsx('p-4 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800', className)}>
    <div className="flex items-center gap-3 mb-4">
      <SkeletonAvatar />
      <div className="flex-1">
        <Skeleton className="h-4 w-24 mb-2" />
        <Skeleton className="h-3 w-16" />
      </div>
    </div>
    <SkeletonText lines={3} />
  </div>
);

/**
 * Skeleton for playlist/queue items
 */
export const SkeletonPlaylistItem: React.FC<{ className?: string }> = ({ className }) => (
  <div
    className={clsx(
      'p-3 border rounded flex justify-between items-center',
      'bg-[color:var(--color-surface)] border-[color:var(--color-outline)]',
      className
    )}
  >
    <div className="flex-1 min-w-0">
      <div className="flex items-center gap-2 mb-1">
        <Skeleton className="h-4 w-48" />
        <Skeleton className="h-3 w-12" />
      </div>
      <Skeleton className="h-3 w-64" />
    </div>
    <div className="text-right ml-4">
      <Skeleton className="h-3 w-10 mb-1" />
      <Skeleton className="h-3 w-14" />
    </div>
  </div>
);

/**
 * Skeleton for playlist queue
 */
export const SkeletonPlaylistQueue: React.FC<{ itemCount?: number; className?: string }> = ({
  itemCount = 3,
  className,
}) => (
  <div className={clsx('space-y-2', className)}>
    {Array.from({ length: itemCount }).map((_, i) => (
      <SkeletonPlaylistItem key={i} />
    ))}
  </div>
);

/**
 * Skeleton for table rows
 */
export const SkeletonTableRow: React.FC<{ columns?: number; className?: string }> = ({
  columns = 3,
  className,
}) => (
  <div className={clsx('flex items-center gap-4 py-3 border-b border-gray-200 dark:border-gray-700', className)}>
    {Array.from({ length: columns }).map((_, i) => (
      <Skeleton key={i} className={clsx('h-4', i === 0 ? 'w-1/3' : 'w-1/4')} />
    ))}
  </div>
);

/**
 * Skeleton for stats/metric cards
 */
export const SkeletonStatCard: React.FC<{ className?: string }> = ({ className }) => (
  <div className={clsx('p-4 rounded-lg border border-gray-200 dark:border-gray-700', className)}>
    <Skeleton className="h-3 w-20 mb-2" />
    <Skeleton className="h-8 w-16" />
  </div>
);

/**
 * Skeleton for channel cards
 */
export const SkeletonChannelCard: React.FC<{ className?: string }> = ({ className }) => (
  <div
    className={clsx(
      'bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden',
      className
    )}
  >
    <div className="p-5">
      <div className="flex justify-between items-start mb-4">
        <div>
          <Skeleton className="h-5 w-32 mb-2" />
          <Skeleton className="h-3 w-24" />
        </div>
        <Skeleton className="h-6 w-16 rounded-full" />
      </div>
      <div className="space-y-2 mb-6">
        <div className="flex justify-between">
          <Skeleton className="h-3 w-16" />
          <Skeleton className="h-3 w-12" />
        </div>
      </div>
      <div className="flex gap-3">
        <Skeleton className="h-10 flex-1 rounded-lg" />
        <Skeleton className="h-10 w-10 rounded-lg" />
      </div>
    </div>
  </div>
);

/**
 * Full-page loading skeleton
 */
export const SkeletonPage: React.FC<{ className?: string }> = ({ className }) => (
  <div className={clsx('space-y-6 p-4', className)}>
    {/* Header */}
    <div className="flex items-center justify-between">
      <Skeleton className="h-8 w-48" />
      <Skeleton className="h-10 w-32 rounded-lg" />
    </div>
    
    {/* Stats grid */}
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
      <SkeletonStatCard />
      <SkeletonStatCard />
      <SkeletonStatCard />
    </div>
    
    {/* Content */}
    <SkeletonCard />
  </div>
);

export default Skeleton;
