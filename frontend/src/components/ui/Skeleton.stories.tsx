import type { Meta, StoryObj } from "@storybook/react";
import {
  Skeleton,
  SkeletonText,
  SkeletonAvatar,
  SkeletonCard,
  SkeletonPlaylistItem,
  SkeletonPlaylistQueue,
} from "./Skeleton";

// Meta for base Skeleton
const meta: Meta<typeof Skeleton> = {
  title: "UI/Skeleton",
  component: Skeleton,
  tags: ["autodocs"],
  parameters: {
    layout: "centered",
    docs: {
      description: {
        component:
          "Компоненты-скелетоны для отображения состояния загрузки. Включает базовый Skeleton и производные компоненты для типичных UI элементов.",
      },
    },
  },
  argTypes: {
    width: {
      control: "text",
      description: "Ширина (Tailwind класс или CSS значение)",
    },
    height: {
      control: "text",
      description: "Высота (Tailwind класс или CSS значение)",
    },
    rounded: {
      control: "select",
      options: ["none", "sm", "md", "lg", "xl", "full"],
      description: "Скругление углов",
    },
    animation: {
      control: "select",
      options: ["pulse", "shimmer", "none"],
      description: "Тип анимации",
    },
  },
};

export default meta;
type Story = StoryObj<typeof meta>;

// Base skeleton
export const Default: Story = {
  args: {
    className: "w-48 h-4",
    rounded: "md",
    animation: "pulse",
  },
};

// Different sizes
export const Sizes: Story = {
  render: () => (
    <div className="space-y-4 w-64">
      <Skeleton className="w-full h-2" />
      <Skeleton className="w-full h-4" />
      <Skeleton className="w-full h-6" />
      <Skeleton className="w-full h-8" />
      <Skeleton className="w-full h-12" />
    </div>
  ),
};

// Rounded variants
export const RoundedVariants: Story = {
  render: () => (
    <div className="flex gap-4">
      <Skeleton className="w-16 h-16" rounded="none" />
      <Skeleton className="w-16 h-16" rounded="sm" />
      <Skeleton className="w-16 h-16" rounded="md" />
      <Skeleton className="w-16 h-16" rounded="lg" />
      <Skeleton className="w-16 h-16" rounded="xl" />
      <Skeleton className="w-16 h-16" rounded="full" />
    </div>
  ),
};

// Animation variants
export const Animations: Story = {
  render: () => (
    <div className="space-y-4 w-48">
      <div>
        <p className="text-sm text-gray-500 mb-2">Pulse</p>
        <Skeleton className="w-full h-4" animation="pulse" />
      </div>
      <div>
        <p className="text-sm text-gray-500 mb-2">Shimmer</p>
        <Skeleton className="w-full h-4" animation="shimmer" />
      </div>
      <div>
        <p className="text-sm text-gray-500 mb-2">None</p>
        <Skeleton className="w-full h-4" animation="none" />
      </div>
    </div>
  ),
};

// SkeletonText stories
export const TextLines: Story = {
  render: () => (
    <div className="w-64 space-y-6">
      <div>
        <p className="text-sm text-gray-500 mb-2">1 line</p>
        <SkeletonText lines={1} />
      </div>
      <div>
        <p className="text-sm text-gray-500 mb-2">2 lines</p>
        <SkeletonText lines={2} />
      </div>
      <div>
        <p className="text-sm text-gray-500 mb-2">3 lines</p>
        <SkeletonText lines={3} />
      </div>
      <div>
        <p className="text-sm text-gray-500 mb-2">5 lines</p>
        <SkeletonText lines={5} />
      </div>
    </div>
  ),
};

// SkeletonAvatar stories
export const Avatars: Story = {
  render: () => (
    <div className="flex gap-4 items-center">
      <div className="text-center">
        <SkeletonAvatar size="sm" />
        <p className="text-xs text-gray-500 mt-1">Small</p>
      </div>
      <div className="text-center">
        <SkeletonAvatar size="md" />
        <p className="text-xs text-gray-500 mt-1">Medium</p>
      </div>
      <div className="text-center">
        <SkeletonAvatar size="lg" />
        <p className="text-xs text-gray-500 mt-1">Large</p>
      </div>
    </div>
  ),
};

// SkeletonCard story
export const Card: Story = {
  render: () => (
    <div className="w-80">
      <SkeletonCard />
    </div>
  ),
};

// SkeletonPlaylistItem story
export const PlaylistItem: Story = {
  render: () => (
    <div className="w-96">
      <SkeletonPlaylistItem />
    </div>
  ),
};

// SkeletonPlaylistQueue story
export const PlaylistQueue: Story = {
  render: () => (
    <div className="w-96">
      <SkeletonPlaylistQueue itemCount={3} />
    </div>
  ),
};

// Full page loading example
export const PageLoading: Story = {
  render: () => (
    <div className="w-[600px] p-6 bg-gray-50 dark:bg-gray-900 rounded-lg space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-10 w-24 rounded-lg" />
      </div>

      {/* Stats cards */}
      <div className="grid grid-cols-3 gap-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="p-4 bg-white dark:bg-gray-800 rounded-lg shadow-sm">
            <Skeleton className="h-4 w-20 mb-2" />
            <Skeleton className="h-8 w-16" />
          </div>
        ))}
      </div>

      {/* Content */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-4">
        <Skeleton className="h-6 w-32 mb-4" />
        <SkeletonPlaylistQueue itemCount={4} />
      </div>
    </div>
  ),
};

// Dark theme
export const DarkTheme: Story = {
  render: () => (
    <div className="p-6 bg-slate-900 rounded-lg">
      <div className="w-64 space-y-4">
        <Skeleton className="w-full h-4" />
        <Skeleton className="w-3/4 h-4" />
        <SkeletonCard className="dark:border-slate-700 dark:bg-slate-800" />
      </div>
    </div>
  ),
  parameters: {
    backgrounds: { default: "dark" },
  },
};
