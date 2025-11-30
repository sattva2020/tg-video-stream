import React from 'react';
import { useTranslation } from 'react-i18next';
import { Globe } from 'lucide-react';
import { clsx } from 'clsx';
import { Dropdown, DropdownTrigger, DropdownMenu, DropdownItem, Button } from "@heroui/react";

interface LanguageSwitcherProps {
  className?: string;
}

export const LanguageSwitcher: React.FC<LanguageSwitcherProps> = ({ className }) => {
  const { i18n } = useTranslation();

  const changeLanguage = (lng: string) => {
    i18n.changeLanguage(lng);
  };

  // Get the base language code (e.g., 'en' from 'en-US')
  const currentLang = i18n.resolvedLanguage?.split('-')[0] || 'en';

  return (
    <Dropdown>
      <DropdownTrigger>
        <Button 
          variant="light" 
          className={clsx("min-w-0 px-2 gap-2 bg-transparent data-[hover=true]:bg-transparent", className)}
          disableAnimation
        >
          <Globe size={20} />
          <span className="text-sm font-medium uppercase">{currentLang}</span>
        </Button>
      </DropdownTrigger>
      <DropdownMenu 
        aria-label="Language selection" 
        onAction={(key) => changeLanguage(key as string)}
        selectedKeys={new Set([currentLang])}
        selectionMode="single"
        className="bg-black/90 backdrop-blur-md text-[#F5E6D3] rounded-xl border border-[#F5E6D3]/30"
        itemClasses={{
          base: "data-[hover=true]:bg-[#F5E6D3]/20 data-[hover=true]:text-[#F5E6D3] text-[#F5E6D3]/80",
        }}
      >
        <DropdownItem key="ru">Русский</DropdownItem>
        <DropdownItem key="uk">Українська</DropdownItem>
        <DropdownItem key="de">Deutsch</DropdownItem>
        <DropdownItem key="en">English</DropdownItem>
      </DropdownMenu>
    </Dropdown>
  );
};
