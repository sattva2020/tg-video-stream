# Источник плейлистов: публичная папка Google Drive

## Назначение
Позволяет указать **публичную** папку Google Drive как источник плейлиста и транслировать аудио/видео-файлы из неё.

Ключевые свойства реализации:
- без OAuth (только **API key** для Google Drive API v3 на сервере);
- файлы листятся на backend и сохраняются в `playlist.items`;
- воспроизведение идёт через backend-прокси `/api/media/gdrive/files/...` (чтобы не раскрывать ключ и поддержать `Range`).

## Требования
- Папка Google Drive должна быть открыта «Доступ по ссылке».
- На сервере должен быть задан `GOOGLE_DRIVE_API_KEY`.

## Настройка
1) Включите **Google Drive API** в Google Cloud Console.
2) Создайте API key.
3) Добавьте переменную в `backend/.env` (см. пример в [backend/.env.example](../../backend/.env.example)):

```dotenv
GOOGLE_DRIVE_API_KEY=...
```

## Использование в UI
1) Откройте создание плейлиста.
2) Выберите источник **Google Drive папка**.
3) Вставьте URL папки вида:

```text
https://drive.google.com/drive/folders/<FOLDER_ID>?usp=sharing
```

4) Сохраните плейлист.

## Как это работает технически
- Backend листит файлы папки через Drive API v3 `files.list`.
- В плейлист попадают только файлы с `mimeType` начинающимся на `audio/` или `video/`.
- Для каждого файла формируется item URL:

```text
/api/media/gdrive/files/<FILE_ID>/<FILENAME>
```

- Стример при воспроизведении автоматически превращает относительные `/api/...` URL в абсолютные (через `BACKEND_URL`).

## Ограничения
- Поддерживаются только файлы, которые Google Drive отдаёт как `alt=media`.
- Если файл недоступен по публичной ссылке (ограничения доступа), backend вернёт ошибку.
