import React, { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Card, CardBody, CardHeader, Button, Input, Select, SelectItem } from '@heroui/react'
import { Plus, Music, Youtube, FileAudio } from 'lucide-react'
import * as playlistService from '../services/playlist'
import { useToast } from '../hooks/useToast'

const trackTypes = [
  { key: 'stream', label: 'Stream', icon: Music },
  { key: 'youtube', label: 'YouTube', icon: Youtube },
  { key: 'local', label: 'Local', icon: FileAudio },
]

const AddTrackForm: React.FC<{ onAdded?: () => void }> = ({ onAdded }) => {
  const { t } = useTranslation()
  const [url, setUrl] = useState('')
  const [title, setTitle] = useState('')
  const [type, setType] = useState<'stream' | 'youtube' | 'local'>('stream')
  const [loading, setLoading] = useState(false)
  const toast = useToast()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!url) return
    setLoading(true)
    try {
      await playlistService.addTrack({ url, title: title || undefined, type })
      setUrl('')
      setTitle('')
      toast.success(t('playlist.trackAdded', 'Трек успешно добавлен'))
      if (onAdded) onAdded()
    } catch (err) {
      console.error('Failed to add track', err)
      toast.error(t('playlist.addError', 'Не удалось добавить трек'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card className="bg-[color:var(--color-panel)] border border-[color:var(--color-outline)]">
      <CardHeader className="pb-0">
        <h3 className="text-lg font-semibold text-[color:var(--color-text)]">
          {t('playlist.addTrack', 'Добавить трек')}
        </h3>
      </CardHeader>
      <CardBody>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="flex gap-3">
            <Input
              placeholder={t('playlist.urlPlaceholder', 'URL трека')}
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              required
              classNames={{
                input: 'text-[color:var(--color-text)]',
                inputWrapper: 'bg-[color:var(--color-surface-muted)] border-[color:var(--color-outline)]',
              }}
              className="flex-1"
            />
            <Select
              selectedKeys={[type]}
              onSelectionChange={(keys) => {
                const selected = Array.from(keys)[0] as string
                if (selected) setType(selected as typeof type)
              }}
              classNames={{
                trigger: 'bg-[color:var(--color-surface-muted)] border-[color:var(--color-outline)] min-w-[140px]',
                value: 'text-[color:var(--color-text)]',
              }}
              aria-label={t('playlist.selectType', 'Выберите тип')}
            >
              {trackTypes.map((tt) => (
                <SelectItem key={tt.key} startContent={<tt.icon className="w-4 h-4" />}>
                  {tt.label}
                </SelectItem>
              ))}
            </Select>
          </div>
          
          <Input
            placeholder={t('playlist.titlePlaceholder', 'Название (необязательно)')}
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            classNames={{
              input: 'text-[color:var(--color-text)]',
              inputWrapper: 'bg-[color:var(--color-surface-muted)] border-[color:var(--color-outline)]',
            }}
          />
          
          <div className="flex justify-end">
            <Button
              type="submit"
              isLoading={loading}
              color="primary"
              startContent={!loading && <Plus className="w-4 h-4" />}
            >
              {t('playlist.add', 'Добавить')}
            </Button>
          </div>
        </form>
      </CardBody>
    </Card>
  )
}

export default AddTrackForm
