# Исправление краша PlaylistManager.tsx

**Дата:** 2025-06-XX  
**Категория:** Критический bugfix  
**Версия:** Prod hotfix  
**Файл:** `frontend/src/components/PlaylistManager.tsx`

## Проблема

В production среде возникала ошибка:
```
TypeError: g.map is not a function at PlaylistManager.tsx:333
```

**Причина:** State `items` мог стать не-массивом после ошибки API или некорректного WebSocket сообщения, что приводило к краху при попытке вызова `.map()`.

## Решение

Добавлены защитные проверки `Array.isArray()` во всех местах работы с `items`:

### 1. Fetch плейлиста (строки 116-128)
```tsx
const fetchPlaylist = useCallback(async () => {
    setLoading(true);
    try {
        const response = await client.get('/api/playlist/');
        // Защита от невалидных данных: всегда устанавливаем массив
        const data = Array.isArray(response.data) ? response.data : [];
        setItems(data);
    } catch (err) {
        console.error('Failed to fetch playlist', err);
        toast.error(t('playlist.loadError', 'Не удалось загрузить плейлист'));
        // При ошибке устанавливаем пустой массив
        setItems([]);
    } finally {
        setLoading(false);
    }
}, [toast, t]);
```

### 2. Обработка reorder (строки 157-160)
```tsx
const handleReorder = (newItems: PlaylistItem[]) => {
    // Защита от невалидных данных при reorder
    const validItems = Array.isArray(newItems) ? newItems : [];
    setItems(validItems);
};
```

### 3. Сохранение порядка (строки 162-182)
```tsx
const saveOrder = async () => {
    setSaving(true);
    try {
        // Защита: если items не массив, пропускаем сохранение
        if (!Array.isArray(items) || items.length === 0) {
            toast.warning(t('playlist.emptyPlaylist', 'Плейлист пуст'));
            return;
        }
        
        const updates = items.map((item, index) => ({
            id: item.id,
            position: index,
        }));
        await client.patch('/api/playlist/reorder', { items: updates });
        toast.success(t('playlist.orderSaved', 'Порядок сохранён'));
    } catch (err) {
        console.error('Failed to save order', err);
        toast.error(t('playlist.orderError', 'Не удалось сохранить порядок'));
        fetchPlaylist();
    } finally {
        setSaving(false);
    }
};
```

### 4. Рендер (строки 235, 333, 341, 358)
```tsx
// Заголовок с подсказкой
{Array.isArray(items) && items.length > 1 && (
    <span>⇅ Перетащите для сортировки</span>
)}

// Проверка пустого плейлиста
{!Array.isArray(items) || items.length === 0 ? (
    <p>Плейлист пуст. Добавьте видео!</p>
) : (
    <Reorder.Group>
        {/* Дополнительная защита перед map */}
        {(Array.isArray(items) ? items : []).map((item, index) => (
            <DraggablePlaylistItem ... />
        ))}
    </Reorder.Group>
)}

// Кнопка сохранения порядка
{Array.isArray(items) && items.length > 1 && (
    <Button onPress={saveOrder}>Сохранить порядок</Button>
)}
```

## Проверка

✅ TypeScript компиляция: без ошибок  
✅ Vite build: успешно (18.03s)  
✅ Runtime защита: все операции с `items` обёрнуты в `Array.isArray()`

## Деплой

1. Собрать production build:
   ```bash
   cd frontend && npm run build
   ```

2. Загрузить `dist/` на сервер:
   ```bash
   rsync -avz --delete dist/ root@sattva-streamer.top:/app/frontend/dist/
   ```

3. Перезапустить nginx (если нужно):
   ```bash
   ssh root@sattva-streamer.top "systemctl reload nginx"
   ```

## Превентивные меры

- **WebSocket:** Хук `usePlaylistWebSocket` уже имеет `Array.isArray()` проверки (строка 104)
- **API контракт:** Backend должен всегда возвращать массив в `GET /api/playlist/`
- **Мониторинг:** Добавить Sentry/Datadog для отслеживания подобных ошибок в production

## Связанные задачи

- [ ] Добавить unit-тесты для `fetchPlaylist` с мокированными ошибками API
- [ ] Добавить e2e тест для сценария "API возвращает невалидный response"
- [ ] Документировать API контракт для `/api/playlist/` в OpenAPI/Swagger

---

**Статус:** ✅ Исправлено  
**Тестирование:** ✅ Build успешен  
**Production:** ⏳ Ожидает деплоя
