from __future__ import annotations

DEMO_PAGES: dict[str, dict[str, str]] = {
    "flawed-landing": {
        "label": "Лендинг студии дизайна (с ошибками SEO)",
        "url": "https://nordic-interior-demo.example/",
        "html": """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Главная</title>
</head>
<body>
  <header>
    <h1>Студия интерьера Nordic</h1>
    <a href="/projects">Проекты</a>
    <a href="#">Услуги</a>
  </header>
  <main>
    <h1>Создаем красивые пространства</h1>
    <p>Мы делаем дизайн квартир и домов в Москве. Работаем быстро и качественно.</p>
    <img src="/img/hero-loft.jpg">
    <img src="/img/kitchen.jpg">
    <img src="/img/bedroom.jpg" alt="Спальня в стиле минимализм">
    <p>Оставьте заявку, чтобы обсудить ваш проект с нашим менеджером.</p>
  </main>
</body>
</html>""",
    },
    "strong-saas": {
        "label": "SaaS-сервис (высокий скор + GEO)",
        "url": "https://metricflow-demo.example/seo-analytics",
        "html": """<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>MetricFlow — аналитика конверсии и аудит страниц</title>
  <meta name="description" content="Платформа MetricFlow отслеживает воронку, скорость загрузки и SEO-ошибки лендингов в реальном времени. Бесплатный тариф для команд до 3 проектов.">
  <link rel="canonical" href="https://metricflow-demo.example/seo-analytics">
  <link rel="icon" href="/favicon.ico">
  <meta property="og:title" content="MetricFlow — аналитика и SEO-аудит лендингов">
  <meta property="og:description" content="Находите узкие места в структуре, мета-тегах и скорости сайта за 30 секунд.">
  <meta property="og:image" content="https://metricflow-demo.example/og-cover.png">
  <meta property="og:url" content="https://metricflow-demo.example/seo-analytics">
  <meta property="og:type" content="website">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="MetricFlow — аналитика и SEO-аудит">
  <script type="application/ld+json">
  {
    "@context": "https://schema.org",
    "@type": "SoftwareApplication",
    "name": "MetricFlow",
    "applicationCategory": "BusinessApplication"
  }
  </script>
</head>
<body>
  <main>
    <h1>Аналитика посадочных страниц и автоматический SEO-аудит</h1>
    <p>MetricFlow помогает маркетологам и разработчикам контролировать техническое состояние сайтов, отслеживать падение позиций и быстро находить ошибки в верстке, мета-тегах и микроразметке. Сервис работает с любыми CMS, конструкторами и кастомными лендингами, позволяя команде заранее выявлять проблемы до запуска рекламных кампаний.</p>
    <h2>Какие метрики проверяет сервис?</h2>
    <ul>
      <li>Заголовки Title, длину сниппетов и пиксельную ширину в выдаче.</li>
      <li>Иерархию H1-H3, атрибуты изображений и стабильность верстки.</li>
      <li>Наличие микроразметки Schema.org для корректного цитирования в нейропоиске.</li>
    </ul>
    <h3>Техническая проверка за 10 секунд</h3>
    <p>После ввода адреса сервис формирует понятный отчет с приоритетами исправлений: сначала критические ошибки индексации, затем рекомендации по росту кликабельности в поисковой выдаче. Каждый пункт сопровождается конкретным решением, которое разработчик или контент-менеджер может внедрить за несколько минут.</p>
    <h2>Интеграция с рабочими процессами</h2>
    <p>Отчеты экспортируются в Markdown и JSON, что удобно для постановки задач в Notion, Jira или GitHub Issues. Вы можете сравнивать версии страницы до и после релиза, фиксировать изменения и отслеживать рост итоговой оценки качества страницы по всем ключевым категориям.</p>
    <h2>Тарифы и условия запуска</h2>
    <p>Стартовый план доступен бесплатно без привязки карты и включает до 50 проверок в месяц. Для агентств предусмотрены командные пространства, история сканирований, пакетная обработка списков URL и доступ по REST API для автоматических проверок качества верстки в CI/CD пайплайнах перед публикацией обновлений на продакшен.</p>
    <img src="/assets/dashboard.webp" width="1200" height="720" alt="Интерфейс отчета MetricFlow с графиком SEO-оценки">
    <a href="/pricing">Тарифы</a>
    <a href="/docs">Документация</a>
    <a href="https://github.com/metricflow" target="_blank" rel="noopener noreferrer">GitHub</a>
  </main>
</body>
</html>""",
    },
}
