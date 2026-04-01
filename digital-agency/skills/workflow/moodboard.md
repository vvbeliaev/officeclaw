# Sub-prompt: Moodboard

Цель — создать живой Pinterest board который передаёт вайб проекта.
Не коллекция картинок — визуальное высказывание.

## Шаг 1 — Подготовить поисковые запросы из брифа

Открой `clients/{chat_id}/brief.md`. Извлеки mood words, industry/context, color hints.

Составь 5-6 поисковых запросов:

| # | Тип | Пример |
|---|---|---|
| 1 | Веб-референсы | `{style} web design` |
| 2 | Брендинг в нише | `{industry} branding identity` |
| 3 | Фотография/настроение | `{mood_words} photography` |
| 4 | Арт и иллюстрации | `{mood_words} art poster` |
| 5 | Цветовые решения | `{color} color palette design` |
| 6 | Свободный / интуитивный | текстуры, природа, архитектура — доверяй ощущению |

Запрос #6 самый важный: не логика — вайб.

## Шаг 2 — Pinterest: войти в аккаунт

Перейди на `pinterest.com`. Если нет credentials → STOP, уведоми оператора.

## Шаг 3 — Создать board

- Название: `{client_name или chat_id} — {тип проекта}`
- Сделай board **секретным**
- Запиши URL в brief.md:

```yaml
moodboard:
  pinterest_url: {url}
  status: in_progress
```

## Шаг 4 — Собрать референсы

Для каждого запроса: открой `pinterest.com/search/pins/?q={query}`, просмотри 20-30 пинов, сохрани 3-5 которые передают вайб брифа.

Итого на board: **15-25 пинов**.

Типичные ошибки:
- Нет подходящих пинов → измени формулировку или попробуй на английском
- Запросы слишком конкретные → сделай абстрактнее

## Шаг 5 — Скриншот и отправка клиенту

Скриншот итогового board → `clients/{chat_id}/assets/moodboard/board_final.png`

Отправь клиенту:
> Собрал визуальное направление для проекта — посмотри что получилось.
> {pinterest_board_url}
>
> Что откликается? Что не то?

## Шаг 6 — Зафиксировать результат

```yaml
moodboard:
  pinterest_url: {url}
  status: sent_to_client  # или: approved / revision_requested
  date: {date}
  client_feedback: {краткая суть}
```

## Fallback: Pinterest недоступен

Используй Dribbble или Behance. Итог — папка со скриншотами + `moodboard_notes.md`.

**Terminal state:** клиент апрувнул мудборд, `moodboard.status: approved` в brief.md → переход в DEVELOPMENT.
