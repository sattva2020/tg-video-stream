import type { Meta, StoryObj } from "@storybook/react";
import { Pagination } from "./Pagination";
import { useState } from "react";

const meta: Meta<typeof Pagination> = {
  title: "UI/Pagination",
  component: Pagination,
  tags: ["autodocs"],
  parameters: {
    layout: "centered",
    docs: {
      description: {
        component:
          "Компонент пагинации для навигации по страницам. Поддерживает настройку размера страницы, отображение информации о текущей позиции и различные состояния.",
      },
    },
  },
  argTypes: {
    page: {
      control: { type: "number", min: 1 },
      description: "Текущая страница",
    },
    totalPages: {
      control: { type: "number", min: 1 },
      description: "Общее количество страниц",
    },
    total: {
      control: { type: "number", min: 0 },
      description: "Общее количество элементов",
    },
    pageSize: {
      control: { type: "number", min: 1 },
      description: "Количество элементов на странице",
    },
    hasNext: {
      control: "boolean",
      description: "Есть ли следующая страница",
    },
    hasPrev: {
      control: "boolean",
      description: "Есть ли предыдущая страница",
    },
    isLoading: {
      control: "boolean",
      description: "Состояние загрузки",
    },
    pageSizeOptions: {
      control: "object",
      description: "Варианты размера страницы",
    },
  },
};

export default meta;
type Story = StoryObj<typeof meta>;

// Basic story with controls
export const Default: Story = {
  args: {
    page: 1,
    totalPages: 10,
    total: 100,
    pageSize: 10,
    hasNext: true,
    hasPrev: false,
    onPageChange: () => {},
    onPageSizeChange: () => {},
    isLoading: false,
    pageSizeOptions: [10, 20, 50],
  },
};

// Interactive example
export const Interactive: Story = {
  render: function InteractivePagination() {
    const [page, setPage] = useState(1);
    const [pageSize, setPageSize] = useState(10);
    const total = 95;
    const totalPages = Math.ceil(total / pageSize);

    return (
      <div className="w-full max-w-2xl p-4">
        <Pagination
          page={page}
          totalPages={totalPages}
          total={total}
          pageSize={pageSize}
          hasNext={page < totalPages}
          hasPrev={page > 1}
          onPageChange={setPage}
          onPageSizeChange={setPageSize}
          pageSizeOptions={[10, 20, 50]}
        />
      </div>
    );
  },
};

// Middle page
export const MiddlePage: Story = {
  args: {
    page: 5,
    totalPages: 10,
    total: 100,
    pageSize: 10,
    hasNext: true,
    hasPrev: true,
    onPageChange: () => {},
    onPageSizeChange: () => {},
  },
};

// Last page
export const LastPage: Story = {
  args: {
    page: 10,
    totalPages: 10,
    total: 100,
    pageSize: 10,
    hasNext: false,
    hasPrev: true,
    onPageChange: () => {},
    onPageSizeChange: () => {},
  },
};

// Single page
export const SinglePage: Story = {
  args: {
    page: 1,
    totalPages: 1,
    total: 5,
    pageSize: 10,
    hasNext: false,
    hasPrev: false,
    onPageChange: () => {},
    onPageSizeChange: () => {},
  },
};

// Loading state
export const Loading: Story = {
  args: {
    page: 1,
    totalPages: 10,
    total: 100,
    pageSize: 10,
    hasNext: true,
    hasPrev: false,
    onPageChange: () => {},
    onPageSizeChange: () => {},
    isLoading: true,
  },
};

// Many pages with ellipsis
export const ManyPages: Story = {
  args: {
    page: 25,
    totalPages: 100,
    total: 1000,
    pageSize: 10,
    hasNext: true,
    hasPrev: true,
    onPageChange: () => {},
    onPageSizeChange: () => {},
  },
};

// Custom page size options
export const CustomPageSizeOptions: Story = {
  args: {
    page: 1,
    totalPages: 5,
    total: 250,
    pageSize: 50,
    hasNext: true,
    hasPrev: false,
    onPageChange: () => {},
    onPageSizeChange: () => {},
    pageSizeOptions: [25, 50, 100, 250],
  },
};
