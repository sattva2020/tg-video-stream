import React from 'react';
import { useTranslation } from 'react-i18next';
import { motion } from 'framer-motion';
import { Card, CardBody, Button } from '@heroui/react';
import { Youtube, Vimeo, FolderOpen, type LucideIcon } from 'lucide-react';
import { ImportPlatform } from '../../types/import';

interface PlatformOption {
    value: ImportPlatform;
    label: string;
    icon: LucideIcon;
    description: string;
    color: 'primary' | 'success' | 'warning';
}

interface PlatformSelectorProps {
    /** Currently selected platform */
    selectedPlatform: ImportPlatform | null;
    /** Callback when platform is selected */
    onPlatformSelect: (platform: ImportPlatform) => void;
    /** Whether the selector is disabled */
    disabled?: boolean;
    /** Optional className for custom styling */
    className?: string;
}

const PlatformSelector: React.FC<PlatformSelectorProps> = ({
    selectedPlatform,
    onPlatformSelect,
    disabled = false,
    className = '',
}) => {
    const { t } = useTranslation();

    const platforms: PlatformOption[] = [
        {
            value: 'youtube',
            label: t('import.platform.youtube', 'YouTube'),
            icon: Youtube,
            description: t('import.platform.youtubeDescription', 'Import playlists and videos from YouTube'),
            color: 'danger',
        },
        {
            value: 'vimeo',
            label: t('import.platform.vimeo', 'Vimeo'),
            icon: Vimeo,
            description: t('import.platform.vimeoDescription', 'Import albums and videos from Vimeo'),
            color: 'primary',
        },
        {
            value: 'local',
            label: t('import.platform.local', 'Local Files'),
            icon: FolderOpen,
            description: t('import.platform.localDescription', 'Import from local media library'),
            color: 'success',
        },
    ];

    return (
        <Card className={`bg-[color:var(--color-panel)] border border-[color:var(--color-outline))] ${className}`}>
            <CardBody className="space-y-4">
                <div>
                    <h3 className="text-lg font-semibold text-[color:var(--color-text)] mb-2">
                        {t('import.platform.selectSource', 'Select Import Source')}
                    </h3>
                    <p className="text-sm text-[color:var(--color-text-muted)]">
                        {t('import.platform.selectSourceHint', 'Choose the platform you want to import content from')}
                    </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {platforms.map((platform) => {
                        const Icon = platform.icon;
                        const isSelected = selectedPlatform === platform.value;

                        return (
                            <motion.div
                                key={platform.value}
                                whileHover={{ scale: disabled ? 1 : 1.02 }}
                                whileTap={{ scale: disabled ? 1 : 0.98 }}
                                transition={{ duration: 0.2 }}
                            >
                                <Button
                                    onPress={() => !disabled && onPlatformSelect(platform.value)}
                                    isDisabled={disabled}
                                    variant={isSelected ? 'solid' : 'bordered'}
                                    color={isSelected ? platform.color : 'default'}
                                    className={`w-full h-auto py-4 px-4 flex flex-col items-start gap-2 transition-all ${
                                        isSelected
                                            ? 'border-[color:var(--color-accent)] shadow-lg'
                                            : 'border-[color:var(--color-outline)] hover:border-[color:var(--color-accent)]'
                                    }`}
                                    classNames={{
                                        content: 'w-full',
                                    }}
                                >
                                    <div className="flex items-center gap-3 w-full">
                                        <Icon
                                            className={`w-6 h-6 ${
                                                isSelected
                                                    ? 'text-white'
                                                    : 'text-[color:var(--color-text-muted)]'
                                            }`}
                                        />
                                        <div className="flex-1 text-left">
                                            <div
                                                className={`font-semibold ${
                                                    isSelected
                                                        ? 'text-white'
                                                        : 'text-[color:var(--color-text)]'
                                                }`}
                                            >
                                                {platform.label}
                                            </div>
                                            <div
                                                className={`text-xs mt-1 ${
                                                    isSelected
                                                        ? 'text-white/80'
                                                        : 'text-[color:var(--color-text-muted)]'
                                                }`}
                                            >
                                                {platform.description}
                                            </div>
                                        </div>
                                    </div>
                                </Button>
                            </motion.div>
                        );
                    })}
                </div>
            </CardBody>
        </Card>
    );
};

export default PlatformSelector;
