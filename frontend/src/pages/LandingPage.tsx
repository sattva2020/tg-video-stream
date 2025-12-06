import { Fragment, useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import type { LocaleKey } from '../components/landing';
import ThemeToggle from '../components/landing/ThemeToggle';
import { useThemePreference } from '../hooks/useThemePreference';
import { useLandingLocale } from '../lib/landing/useLandingLocale';
import './landing-reference.css';

const navLinks = [
  { labelKey: 'landing_ref_nav_features', fallbackLabel: 'Возможности', target: 'features' },
  { labelKey: 'landing_ref_nav_workflow', fallbackLabel: 'Процесс', target: 'workflow' },
  { labelKey: 'landing_ref_nav_cases', fallbackLabel: 'Сценарии', target: 'use-cases' },
];

const heroStats = [
  { valueKey: 'landing_ref_stat_days_value', fallbackValue: '365', labelKey: 'landing_ref_stat_days_label', fallbackLabel: 'дней в эфире', color: '#3BA8FF' },
  { valueKey: 'landing_ref_stat_latency_value', fallbackValue: '<100 мс', labelKey: 'landing_ref_stat_latency_label', fallbackLabel: 'задержка', color: '#9F6BFF' },
  { valueKey: 'landing_ref_stat_runner_value', fallbackValue: 'Fail-safe', labelKey: 'landing_ref_stat_runner_label', fallbackLabel: 'раннер', color: '#F59E0B' },
];

const featureCards = [
  {
    titleKey: 'landing_ref_feature_sources_title',
    fallbackTitle: 'Источники контента',
    icon: 'ri-video-upload-line',
    badge: 'bg-cyan-light',
    points: [
      { key: 'landing_ref_feature_sources_point_streams', fallback: 'Потоки с YouTube' },
      { key: 'landing_ref_feature_sources_point_uploads', fallback: 'Загрузка MP4/MKV' },
      { key: 'landing_ref_feature_sources_point_rtmp', fallback: 'RTMP Ingest' },
    ],
  },
  {
    titleKey: 'landing_ref_feature_schedule_title',
    fallbackTitle: 'Автоматика расписаний',
    icon: 'ri-time-line',
    badge: 'bg-purple-light',
    points: [
      { key: 'landing_ref_feature_schedule_point_calendar', fallback: 'Визуальный календарь' },
      { key: 'landing_ref_feature_schedule_point_templates', fallback: 'Шаблоны эфиров' },
      { key: 'landing_ref_feature_schedule_point_timezone', fallback: 'Часовые пояса' },
    ],
  },
  {
    titleKey: 'landing_ref_feature_security_title',
    fallbackTitle: 'Безопасный RBAC',
    icon: 'ri-shield-keyhole-line',
    badge: 'bg-amber-light',
    points: [
      { key: 'landing_ref_feature_security_point_roles', fallback: 'Роли и доступы' },
      { key: 'landing_ref_feature_security_point_workflow', fallback: 'Workflow approvals' },
      { key: 'landing_ref_feature_security_point_mfa', fallback: '2FA/MFA защита' },
    ],
  },
  {
    titleKey: 'landing_ref_feature_resilience_title',
    fallbackTitle: 'Отказоустойчивость',
    icon: 'ri-pulse-line',
    badge: 'bg-cyan-light',
    points: [
      { key: 'landing_ref_feature_resilience_point_health', fallback: 'Health-checks 24/7' },
      { key: 'landing_ref_feature_resilience_point_failover', fallback: 'Автофейловеры' },
      { key: 'landing_ref_feature_resilience_point_backup', fallback: 'Резервные потоки' },
    ],
  },
];

const workflowSteps = [
  {
    badge: 'bg-cyan-light',
    labelKey: 'landing_ref_step_setup_label',
    fallbackLabel: 'Setup',
    titleKey: 'landing_ref_step_setup_title',
    fallbackTitle: 'Подключите аккаунты',
    descriptionKey: 'landing_ref_step_setup_description',
    fallbackDescription: 'Свяжите ваши Telegram-каналы или чаты через безопасный API токен.',
    color: '#3BA8FF',
  },
  {
    badge: 'bg-purple-light',
    labelKey: 'landing_ref_step_build_label',
    fallbackLabel: 'Build',
    titleKey: 'landing_ref_step_build_title',
    fallbackTitle: 'Соберите плейлист',
    descriptionKey: 'landing_ref_step_build_description',
    fallbackDescription: 'Загрузите видеофайлы или укажите ссылки на внешние потоки для трансляции.',
    color: '#9F6BFF',
  },
  {
    badge: 'bg-amber-light',
    labelKey: 'landing_ref_step_plan_label',
    fallbackLabel: 'Plan',
    titleKey: 'landing_ref_step_plan_title',
    fallbackTitle: 'Запланируйте неделю',
    descriptionKey: 'landing_ref_step_plan_description',
    fallbackDescription: 'Расставьте контент в сетке вещания, настройте повторы и перерывы.',
    color: '#F59E0B',
  },
  {
    badge: 'bg-cyan-light',
    labelKey: 'landing_ref_step_live_label',
    fallbackLabel: 'Live',
    titleKey: 'landing_ref_step_live_title',
    fallbackTitle: 'Мониторьте эфир',
    descriptionKey: 'landing_ref_step_live_description',
    fallbackDescription: 'Следите за статусом стрима, качеством сигнала и зрителями в реальном времени.',
    color: '#3BA8FF',
  },
];

const useCaseCards = [
  {
    icon: 'ri-newspaper-line',
    titleKey: 'landing_ref_case_news_title',
    fallbackTitle: 'Новостные каналы',
    descriptionKey: 'landing_ref_case_news_description',
    fallbackDescription: 'Автоматическая ротация новостных выпусков с живыми включениями.',
    className: 'case-cyan',
    color: '#3BA8FF',
  },
  {
    icon: 'ri-radio-2-line',
    titleKey: 'landing_ref_case_radio_title',
    fallbackTitle: '24/7 Радио и стримы',
    descriptionKey: 'landing_ref_case_radio_description',
    fallbackDescription: 'Круглосуточное музыкальное вещание и подкаст-марафоны без пауз.',
    className: 'case-purple',
    color: '#9F6BFF',
  },
  {
    icon: 'ri-live-line',
    titleKey: 'landing_ref_case_media_title',
    fallbackTitle: 'Автотрансляции медиа',
    descriptionKey: 'landing_ref_case_media_description',
    fallbackDescription: 'Ретрансляция эфиров ТВ-каналов в экосистему Telegram.',
    className: 'case-amber',
    color: '#F59E0B',
  },
];
const preferredLocales: LocaleKey[] = ['ru', 'uk', 'de', 'en'];

const LandingPage = () => {
  const { t } = useTranslation();
  const { theme } = useThemePreference();
  const { locale, setLocale, supportedLocales } = useLandingLocale();
  const [showScrollTop, setShowScrollTop] = useState(false);
  const navigate = useNavigate();

  const orderedLocales = useMemo(() => {
    const prioritized = preferredLocales.filter((code) => supportedLocales.includes(code));
    const fallback = supportedLocales.filter((code) => !preferredLocales.includes(code));
    return [...prioritized, ...fallback];
  }, [supportedLocales]);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return undefined;
    }
    const onScroll = () => {
      setShowScrollTop(window.scrollY > 400);
    };
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  const handleLocaleChange = (code: LocaleKey) => {
    if (code === locale) {
      return;
    }
    setLocale(code);
  };

  const handleScrollTop = () => {
    if (typeof window === 'undefined') {
      return;
    }
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const languageLabel = (code: LocaleKey) => t(`language_name_${code}` as const, code.toUpperCase());
  const languageBadge = (code: LocaleKey) => (code === 'uk' ? 'UA' : code.toUpperCase());

  return (
    <div className="landing-reference" data-theme={theme}>
      <div className="ray-bg">
        <div className="ray" style={{ top: '-120px', left: '-80px' }} />
        <div className="ray" style={{ bottom: '-200px', right: '-100px' }} />
      </div>
      <div className="neon-glow" style={{ top: '-200px', right: '10%' }} />
      <div className="neon-glow" style={{ bottom: '-250px', left: '5%' }} />

      <header>
        <div className="logo">
          <i className="ri-telegram-fill" />
          Telegram Streamer
        </div>
        <nav className="nav-links">
          {navLinks.map(({ labelKey, fallbackLabel, target }) => (
            <a href={`#${target}`} key={target}>{t(labelKey, fallbackLabel)}</a>
          ))}
        </nav>
        <div className="header-actions">
          <div
            className="lang-toggle"
            role="group"
            aria-label={t('language_switcher_label', 'Сменить язык лендинга')}
          >
            {orderedLocales.map((code, index) => (
              <Fragment key={code}>
                <button
                  type="button"
                  className={`lang-option${locale === code ? ' is-active' : ''}`}
                  aria-pressed={locale === code}
                  title={languageLabel(code)}
                  onClick={() => handleLocaleChange(code)}
                >
                  {languageBadge(code)}
                </button>
                {index < orderedLocales.length - 1 ? (
                  <span className="lang-separator">/</span>
                ) : null}
              </Fragment>
            ))}
          </div>
          <ThemeToggle />
          <button className="btn btn-primary" type="button" onClick={() => navigate('/auth')}>
            {t('landing_ref_hero_cta_primary', 'Начать работу')}
          </button>
        </div>
      </header>

      <section className="hero">
        <div className="hero-content">
          <div className="badge-hero">
            <i className="ri-broadcast-line" /> {t('landing_ref_hero_badge', 'v2.0 Стриминг платформа')}
          </div>
          <h1 className="font-heading">{t('landing_ref_hero_title', '24/7 трансляции в Telegram без OBS и серверов')}</h1>
          <p className="hero-subtitle">
            {t('landing_ref_hero_subtitle', 'Управляйте плейлистами, настраивайте фейловеры и планируйте эфиры через единую облачную консоль. Стабильность вещания 99.9%.')}
          </p>
          <div className="hero-btns">
            <button className="btn btn-primary" type="button" onClick={() => navigate('/auth')}>
              {t('landing_ref_hero_cta_primary', 'Начать работу')} <i className="ri-arrow-right-line" style={{ marginLeft: 8 }} />
            </button>
            <button className="btn btn-secondary" type="button" onClick={() => navigate('/auth')}>
              {t('landing_ref_hero_cta_secondary', 'Посмотреть демо')}
            </button>
          </div>
          <div className="hero-stats">
            {heroStats.map((stat) => (
              <div className="stat-item" key={stat.labelKey}>
                <div className="stat-value" style={{ color: stat.color }}>
                  {t(stat.valueKey, stat.fallbackValue)}
                </div>
                <div className="stat-label">{t(stat.labelKey, stat.fallbackLabel)}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="hero-visual" aria-hidden>
          <div className="dash-sidebar">
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 24, color: '#334155', fontWeight: 700 }}>
              <div style={{ width: 24, height: 24, background: '#3BA8FF', borderRadius: 6 }} />
              Console
            </div>
            {['Дашборд', 'Расписание', 'Медиатека', 'Настройки'].map((item, idx) => (
              <div className={`dash-menu-item${idx === 0 ? ' active' : ''}`} key={item}>
                {idx === 0 && <i className="ri-dashboard-line" />} 
                {idx === 1 && <i className="ri-calendar-event-line" />} 
                {idx === 2 && <i className="ri-folder-music-line" />} 
                {idx === 3 && <i className="ri-settings-3-line" />} 
                {item}
              </div>
            ))}
          </div>
          <div className="dash-main">
            <div className="dash-header">
              <div>
                <h3 style={{ fontFamily: 'MiSans', fontSize: 18 }}>Главный канал</h3>
                <span style={{ fontSize: 12, color: 'var(--text-tertiary, #94A3B8)' }}>rtmp://tg-streamer.io/live/key_...</span>
              </div>
              <div style={{ display: 'flex', gap: 12 }}>
                <div style={{ padding: '8px 16px', background: '#F1F5F9', borderRadius: 8, fontSize: 12, fontWeight: 600 }}>1080p 60fps</div>
                <div style={{ padding: '8px 16px', background: '#DCFCE7', color: '#166534', borderRadius: 8, fontSize: 12, fontWeight: 600 }}>Stable</div>
              </div>
            </div>
            <div className="dash-preview">
              <div style={{ position: 'absolute', inset: 0, background: 'linear-gradient(45deg, #0f172a, #1e293b)' }} />
              <div style={{ display: 'flex', gap: 4, alignItems: 'flex-end', height: 60, opacity: 0.7 }}>
                {[40, 60, 30, 50, 45].map((h) => (
                  <div
                    key={h}
                    style={{ width: 8, height: h, background: '#3BA8FF', borderRadius: 4 }}
                  />
                ))}
              </div>
              <div className="live-badge">LIVE</div>
              <div className="viewer-count"><i className="ri-user-line" /> 12,402</div>
              <div style={{ position: 'absolute', bottom: 20, left: 20, right: 20, display: 'flex', justifyContent: 'space-between', color: '#fff', fontSize: 12 }}>
                <span>Evening News / Main Block</span>
                <span>00:14:23 / 01:00:00</span>
              </div>
              <div style={{ position: 'absolute', bottom: 0, left: 0, width: '35%', height: 3, background: '#3BA8FF' }} />
            </div>
            <div className="playlist-mock">
              <div className="playlist-item" style={{ borderColor: '#3BA8FF', background: '#F0F9FF' }}>
                <div className="playlist-thumb" style={{ background: "url('https://images.unsplash.com/photo-1498050108023-c5249f4df085?w=100&h=100&fit=crop') center/cover" }} />
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 13, fontWeight: 600 }}>Breaking News</div>
                  <div style={{ fontSize: 11, color: '#3BA8FF' }}>Сейчас в эфире</div>
                </div>
                <i className="ri-bar-chart-fill" style={{ color: '#3BA8FF' }} />
              </div>
              <div className="playlist-item">
                <div className="playlist-thumb" style={{ background: "url('https://images.unsplash.com/photo-1551818255-e6e10975bc17?w=100&h=100&fit=crop') center/cover" }} />
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 13, fontWeight: 600, color: '#64748b' }}>Tech Review</div>
                  <div style={{ fontSize: 11, color: '#94A3B8' }}>14:30 - 15:15</div>
                </div>
                <i className="ri-more-2-fill" style={{ color: '#CBD5E1' }} />
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="features" id="features">
        <div className="section-header">
          <h2 className="section-title font-heading">{t('landing_ref_features_title', 'Комплект телекласса для Telegram')}</h2>
          <p className="section-subtitle">{t('landing_ref_features_subtitle', 'Инструменты профессионального вещания, адаптированные для мессенджера')}</p>
        </div>
        <div className="features-grid">
          {featureCards.map((card) => (
            <div className="feature-card" key={card.titleKey}>
              <div className={`feature-icon-wrapper ${card.badge}`}>
                <i className={card.icon} />
              </div>
              <h3>{t(card.titleKey, card.fallbackTitle)}</h3>
              <ul className="feature-list">
                {card.points.map((point) => (
                  <li key={point.key}>
                    <i className="ri-check-line" />
                    {t(point.key, point.fallback)}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </section>

      <section className="workflow" id="workflow">
        <div className="workflow-container">
          <div className="section-header">
            <h2 className="section-title font-heading">{t('landing_ref_workflow_title', 'Выход в эфир за четыре шага')}</h2>
            <p className="section-subtitle">{t('landing_ref_workflow_subtitle', 'Снимаем техническую неопределённость, оставляя только творчество')}</p>
          </div>
          <div className="steps-wrapper">
            <div className="steps-connector" />
            {workflowSteps.map((step, index) => (
              <div className="step-card" key={step.titleKey}>
                <div className="step-number" style={{ borderColor: step.color, color: step.color }}>{index + 1}</div>
                <span className={`step-badge ${step.badge}`}>{t(step.labelKey, step.fallbackLabel)}</span>
                <h4 className="font-heading">{t(step.titleKey, step.fallbackTitle)}</h4>
                <p>{t(step.descriptionKey, step.fallbackDescription)}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="use-cases" id="use-cases">
        <div className="section-header">
          <h2 className="section-title font-heading">{t('landing_ref_usecases_title', 'Где уже работает Telegram Streamer')}</h2>
        </div>
        <div className="cases-grid">
          {useCaseCards.map((card) => (
            <div className={`case-card ${card.className}`} key={card.titleKey}>
              <i className={`${card.icon} case-icon`} style={{ color: card.color }} />
              <h4>{t(card.titleKey, card.fallbackTitle)}</h4>
              <p>{t(card.descriptionKey, card.fallbackDescription)}</p>
            </div>
          ))}
        </div>
      </section>

      <footer>
        <div className="logo" style={{ fontSize: 20 }}>
          <i className="ri-telegram-fill" style={{ fontSize: 24, color: '#94A3B8' }} />
          <span style={{ color: '#64748B' }}>Telegram Streamer</span>
        </div>
        <div className="footer-links">
          {[
            { key: 'landing_ref_footer_docs', fallback: 'Документация' },
            { key: 'landing_ref_footer_api', fallback: 'API' },
            { key: 'landing_ref_footer_security', fallback: 'Безопасность' },
            { key: 'landing_ref_footer_contacts', fallback: 'Контакты' },
          ].map((link) => (
            <a href="#" key={link.key}>{t(link.key, link.fallback)}</a>
          ))}
        </div>
        <div className="copyright">
          {t('landing_ref_footer_copyright', '© 2025 Telegram Streamer Platform. All rights reserved.')}
        </div>
      </footer>

      <button
        type="button"
        className={`scroll-top${showScrollTop ? ' is-visible' : ''}`}
        onClick={handleScrollTop}
        aria-label={t('landing_ref_scroll_top', 'Вернуться наверх')}
      >
        <i className="ri-arrow-up-line" />
      </button>
    </div>
  );
};

export default LandingPage;
