# Sub-prompt: Site Build

## Стек

Astro 5 + React 19 + Tailwind CSS 4 + shadcn v4 (radix-maia) + HugeIcons

<HARD-GATE>
Проверь brief.md перед стартом:
1. `moodboard.status` = `approved`
2. `moodboard.pinterest_url` заполнен

Если нет → STOP. Сообщи оператору: "Сайт нельзя начинать без апрувнутого мудборда. Статус: {status}"
Переходи в фазу MOODBOARD.
</HARD-GATE>

## Фаза 1 — Планирование

Прочитай brief.md. Создай `clients/{chat_id}/artifacts/site_plan.md`:

```yaml
pages:
  - name: index
    sections:
      - type: hero
      - type: services
      - type: about
      - type: testimonials
      - type: faq
      - type: cta
      - type: footer

theme:
  primary_color: "#..."
  font: "..."
  tone: light | dark

components_needed:
  - button
  - card
  - accordion
  # только то что реально нужно
```

## Фаза 2 — Разработка через субагент

Запусти Claude Code агент:

```bash
claude --print "{промпт}" --output-format text
```

**DESIGN MANDATE — прочитай скилл `frontend_design` перед любой работой с темой:**

- Выбери одно эстетическое направление и выполни его до конца
- НЕ используй Inter, Roboto, Arial, Space Grotesk — выбери характерный шрифт
- НЕ делай фиолетовые градиенты на белом — generic AI slop
- Смелость важнее безопасности

Промпт для агента включает: полный brief.md + site_plan.md + инструкции по шаблону.

Шаги агента:

1. Скопировать шаблон: `rsync -av --exclude='node_modules' --exclude='.git' --exclude='.astro' {AGENT_DIR}/skills/site_development/assets/website/ clients/{chat_id}/artifacts/site/`
2. `pnpm install`
3. Настроить тему в `src/styles/global.css` (oklch цвета)
4. Обновить layout (`<title>`, meta теги)
5. Создать компоненты секций в `src/components/sections/`
6. Собрать `src/pages/index.astro`
7. `pnpm build` — исправить ошибки если есть
8. `pnpm preview` + скриншот

## Фаза 3 — Проверка (читай скилл `code_review`)

Используй `agent_browser`:

- Десктоп 1440px
- Мобилка 375px
- Нет консольных ошибок

Чеклист:

- [ ] Тема соответствует мудборду
- [ ] Все секции отображаются корректно
- [ ] Адаптив на 375px работает
- [ ] Нет TypeScript/build ошибок

## Выход

```yaml
# clients/{chat_id}/artifacts/phase_site_summary.yaml
status: delivered
url: https://...
deployed_at: { timestamp }
stack: astro5-shadcn-radix-maia
client_notified: true
```

**Terminal state:** сайт задеплоен, клиент уведомлен, summary заполнен → уведоми оператора с URL.
