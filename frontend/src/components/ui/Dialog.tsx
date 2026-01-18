import * as React from 'react';
import * as RadixDialog from '@radix-ui/react-dialog';
import { cn } from '../../lib/utils';

export const Dialog = RadixDialog.Root;
export const DialogTrigger = RadixDialog.Trigger;

export const DialogContent = React.forwardRef<HTMLDivElement, React.ComponentPropsWithoutRef<typeof RadixDialog.Content>>( 
  ({ className, children, ...props }, ref) => (
    <RadixDialog.Portal>
      <RadixDialog.Overlay className="fixed inset-0 z-50 bg-black/50" />
      <RadixDialog.Content
        ref={ref}
        className={cn(
          'fixed left-1/2 top-1/2 z-50 w-full max-w-lg -translate-x-1/2 -translate-y-1/2 rounded-xl',
          'bg-[color:var(--color-panel)] p-6 shadow-lg border border-[color:var(--color-border)]',
          'focus:outline-none',
          className,
        )}
        {...props}
      >
        {children}
      </RadixDialog.Content>
    </RadixDialog.Portal>
  )
);
DialogContent.displayName = 'DialogContent';

export const DialogHeader: React.FC<{ className?: string; children?: React.ReactNode }> = ({ className, ...props }) => (
  <div className={cn('flex flex-col space-y-1.5 text-left', className)} {...props} />
);

export const DialogTitle = React.forwardRef<HTMLHeadingElement, React.ComponentPropsWithoutRef<typeof RadixDialog.Title>>( 
  ({ className, ...props }, ref) => (
    <RadixDialog.Title
      ref={ref}
      className={cn('text-lg font-semibold leading-none tracking-tight', className)}
      {...props}
    />
  )
);
DialogTitle.displayName = 'DialogTitle';

export const DialogDescription = React.forwardRef<HTMLParagraphElement, React.ComponentPropsWithoutRef<typeof RadixDialog.Description>>( 
  ({ className, ...props }, ref) => (
    <RadixDialog.Description
      ref={ref}
      className={cn('text-sm text-[color:var(--color-text-secondary)]', className)}
      {...props}
    />
  )
);
DialogDescription.displayName = 'DialogDescription';

export const DialogFooter: React.FC<{ className?: string; children?: React.ReactNode }> = ({ className, ...props }) => (
  <div className={cn('mt-6 flex justify-end gap-2', className)} {...props} />
);
