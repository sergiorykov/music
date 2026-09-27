# SEO и AEO: что сделать руками

Сайт уже отдаёт всё, что нужно поисковикам и ИИ-агентам: мета-теги, hreflang, JSON-LD,
`sitemap.xml`, `llms.txt`, `robots.txt` (генерирует `build.py`, модуль `songbook/seo.py`).
Ниже — шаги, которые требуют вашего аккаунта. Порядок важен: 1 → 2 → 3 → 4.

Все значения, которые нужно будет вставить, лежат в `settings.json`:

```json
"verification": { "google": "", "bing": "" },   // коды подтверждения владения
"links": { ..., "wikidata": "" }                // ссылка на карточку Wikidata
```

После правки: `python build.py`, коммит, пуш в `main` — сайт пересоберётся сам.

---

## 1. robots.txt и llms.txt в корне домена

Краулеры читают `robots.txt` **только в корне домена**: `https://sergiorykov.github.io/robots.txt`.
Файл `https://sergiorykov.github.io/music/robots.txt` они игнорируют. Корень `github.io` обслуживает
отдельный репозиторий `sergiorykov/sergiorykov.github.io`.

1. Возьмите `robots.txt` и `llms.txt` из корня этого репозитория (их генерирует `python build.py`
   из `settings.json` → `site-url` и песен; они закоммичены, CI проверяет, что они актуальны).
2. Скопируйте оба файла в корень репозитория `sergiorykov/sergiorykov.github.io`, закоммитьте в его
   ветку, из которой публикуется Pages (Settings → Pages → Source).
3. Проверьте: `https://sergiorykov.github.io/robots.txt` и `https://sergiorykov.github.io/llms.txt`
   открываются.
4. Если песни или описание изменились — повторите копирование (файлы в корне сами не обновятся).

**Свой домен.** Если сайт переедет на свой домен (например `sergiorykov.com`), поменяйте `site-url`
в `settings.json` — `robots.txt`, `llms.txt`, `sitemap.xml`, canonical и JSON-LD пересоберутся с новым
адресом, и копировать ничего не придётся.

## 2. Google Search Console

Даёт: сайт быстрее попадает в индекс Google (а значит и в AI Overviews / AI Mode), видно ошибки и запросы.

1. Откройте <https://search.google.com/search-console> → **Добавить ресурс** → тип **«Ресурс с префиксом
   в URL»** → `https://sergiorykov.github.io/music/`.
   (Тип «Доменный ресурс» требует DNS-записи — для `github.io` недоступен, для своего домена — можно.)
2. Способ подтверждения — **HTML-тег**. Google покажет
   `<meta name="google-site-verification" content="XXXX">` — скопируйте только `XXXX`
   в `settings.json` → `verification.google`, соберите, запушьте в `main`, дождитесь деплоя
   (Actions → «Build and deploy site» зелёный) и нажмите **Подтвердить**.
3. **Файлы Sitemap** → введите `sitemap.xml` → Отправить.
4. **Проверка URL** → вставьте `https://sergiorykov.github.io/music/ru/` → **Запросить индексирование**.
   Повторите для `/en/` и `/pt/`.
5. Через несколько дней смотрите **Индексирование → Страницы**: сколько страниц в индексе и почему
   остальные нет.

## 3. Bing Webmaster Tools

Даёт: индекс Bing — его используют Bing, DuckDuckGo и Microsoft Copilot.

1. Откройте <https://www.bing.com/webmasters> → войдите.
2. Проще всего **«Импорт из Google Search Console»** — сайт и sitemap подтянутся после шага 2.
3. Если вручную: добавьте `https://sergiorykov.github.io/music/`, способ подтверждения **Meta tag**
   (`<meta name="msvalidate.01" content="XXXX">`) → `XXXX` в `settings.json` → `verification.bing`,
   соберите, запушьте, подтвердите. Затем **Sitemaps** → `https://sergiorykov.github.io/music/sitemap.xml`.

## 4. Wikidata

Даёт: ИИ-модели и поисковики берут факты о людях из Wikidata (граф знаний). Карточка связывает
«Сергей Рыков» и «Sergio Rykov», SoundCloud, Instagram и сайт в одну сущность.

**Сначала честно о риске.** У Wikidata есть критерии значимости
(<https://www.wikidata.org/wiki/Wikidata:Notability>): элемент должен описывать сущность,
которую можно подтвердить «серьёзными и общедоступными источниками». Если о вас есть только ваш сайт
и SoundCloud, элемент могут удалить. Помогают: статьи, интервью, упоминания на фестивалях, публикации
песен в сборниках. Если таких нет — этот шаг лучше отложить.

1. Зарегистрируйтесь на <https://www.wikidata.org> (аккаунт общий с Википедией).
2. Поищите «Sergio Rykov» и «Сергей Рыков» — вдруг элемент уже есть (тогда редактируйте его, а не
   создавайте дубль).
3. **Создать новый элемент** (левое меню → Create a new Item):
   - язык `ru`: метка `Сергей Рыков`, описание `автор-исполнитель из Лиссабона`, псевдоним `Sergio Rykov`
   - язык `en`: метка `Sergio Rykov`, описание `Lisbon-based singer-songwriter`, псевдоним `Сергей Рыков`
   - язык `pt`: метка `Sergio Rykov`, описание `cantautor radicado em Lisboa`
4. Добавьте утверждения (**+ add statement**). Свойства ищутся по названию — выбирайте из подсказки:
   - **instance of** → `human`
   - **occupation** → `singer-songwriter`
   - **genre** → `indie music` (или ближайшее из подсказки)
   - **residence** → `Lisbon`
   - **official website** → `https://sergiorykov.github.io/music/`
   - **SoundCloud ID** → `sergiorykov`
   - **Instagram username** → `sergiorykov`
   - **GitHub username** → `sergiorykov`
   - к каждому утверждению по возможности **+ add reference** → **reference URL** (ваш сайт,
     SoundCloud, статья)
5. Скопируйте адрес элемента (`https://www.wikidata.org/wiki/Q…`) в `settings.json` →
   `links.wikidata`, соберите, запушьте — ссылка попадёт в `sameAs` JSON-LD на главной.

## 5. Проверка

- Разметка: <https://validator.schema.org> → вставьте URL главной и любой песни — ошибок быть не должно.
- Расширенные результаты Google: <https://search.google.com/test/rich-results>.
- Превью в соцсетях: отправьте ссылку на песню себе в Telegram — должна появиться карточка с обложкой.
- Через 2–4 недели спросите у ChatGPT / Claude / Perplexity с веб-поиском: «Кто такой Sergio Rykov,
  автор песен?» — ответ покажет, что агенты уже нашли.
