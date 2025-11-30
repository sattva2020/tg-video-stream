import type { Meta, StoryObj } from "@storybook/react";
import { PasswordInput } from "./PasswordInput";

const meta: Meta<typeof PasswordInput> = {
  title: "UI/PasswordInput",
  component: PasswordInput,
  tags: ["autodocs"],
  parameters: {
    layout: "centered",
    docs: {
      description: {
        component:
          "Компонент ввода пароля с возможностью переключения видимости. Поддерживает все стандартные атрибуты input и кастомизацию через className.",
      },
    },
  },
  argTypes: {
    placeholder: {
      control: "text",
      description: "Placeholder текст",
    },
    disabled: {
      control: "boolean",
      description: "Отключённое состояние",
    },
    iconSize: {
      control: { type: "number", min: 12, max: 32 },
      description: "Размер иконки в пикселях",
    },
    className: {
      control: "text",
      description: "CSS классы для input",
    },
    wrapperClassName: {
      control: "text",
      description: "CSS классы для wrapper div",
    },
    buttonClassName: {
      control: "text",
      description: "CSS классы для кнопки toggle",
    },
  },
};

export default meta;
type Story = StoryObj<typeof meta>;

// Default styled input
const defaultClassName =
  "w-full px-4 py-2 pr-12 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-slate-800 dark:border-slate-600 dark:text-white";

// Basic story
export const Default: Story = {
  args: {
    placeholder: "Введите пароль",
    className: defaultClassName,
  },
  decorators: [
    (Story) => (
      <div className="w-80">
        <Story />
      </div>
    ),
  ],
};

// With value
export const WithValue: Story = {
  args: {
    placeholder: "Введите пароль",
    defaultValue: "mySecretPassword123",
    className: defaultClassName,
  },
  decorators: [
    (Story) => (
      <div className="w-80">
        <Story />
      </div>
    ),
  ],
};

// Disabled state
export const Disabled: Story = {
  args: {
    placeholder: "Пароль",
    defaultValue: "disabled-password",
    disabled: true,
    className: `${defaultClassName} opacity-50 cursor-not-allowed`,
  },
  decorators: [
    (Story) => (
      <div className="w-80">
        <Story />
      </div>
    ),
  ],
};

// Custom icon size
export const LargeIcon: Story = {
  args: {
    placeholder: "Пароль",
    iconSize: 24,
    className: defaultClassName,
  },
  decorators: [
    (Story) => (
      <div className="w-80">
        <Story />
      </div>
    ),
  ],
};

// Small icon
export const SmallIcon: Story = {
  args: {
    placeholder: "Пароль",
    iconSize: 14,
    className: defaultClassName,
  },
  decorators: [
    (Story) => (
      <div className="w-80">
        <Story />
      </div>
    ),
  ],
};

// With label (composition example)
export const WithLabel: Story = {
  render: (args) => (
    <div className="w-80 space-y-2">
      <label htmlFor="password-input" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
        Пароль
      </label>
      <PasswordInput
        id="password-input"
        {...args}
        className={defaultClassName}
      />
      <p className="text-xs text-gray-500 dark:text-gray-400">
        Минимум 8 символов
      </p>
    </div>
  ),
  args: {
    placeholder: "Введите пароль",
  },
};

// Error state
export const WithError: Story = {
  render: (args) => (
    <div className="w-80 space-y-2">
      <label htmlFor="password-error" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
        Пароль
      </label>
      <PasswordInput
        id="password-error"
        {...args}
        className="w-full px-4 py-2 pr-12 border border-red-500 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-transparent dark:bg-slate-800 dark:text-white"
      />
      <p className="text-xs text-red-500">
        Пароль слишком короткий
      </p>
    </div>
  ),
  args: {
    placeholder: "Введите пароль",
    defaultValue: "123",
  },
};

// Dark theme preview
export const DarkTheme: Story = {
  args: {
    placeholder: "Введите пароль",
    className: "w-full px-4 py-2 pr-12 border border-slate-600 rounded-md bg-slate-800 text-white focus:outline-none focus:ring-2 focus:ring-blue-500",
  },
  decorators: [
    (Story) => (
      <div className="w-80 p-4 bg-slate-900 rounded-lg">
        <Story />
      </div>
    ),
  ],
  parameters: {
    backgrounds: { default: "dark" },
  },
};
