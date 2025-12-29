import { useTranslation } from 'react-i18next';

/**
 * Компонент для тестирования и диагностики i18n
 * 
 * Показывает:
 * - Текущий язык
 * - Примеры переводов
 * - Кнопки переключения языка
 * 
 * Использование:
 * Добавьте <I18nDebugPanel /> в любой компонент для проверки
 */
export const I18nDebugPanel = () => {
  const { t, i18n } = useTranslation();
  
  const testKeys = [
    'admin.dashboard',
    'admin.users',
    'admin.stream',
    'admin.start',
    'admin.stop',
    'admin.restart',
    'common.loading',
  ];
  
  return (
    <div 
      style={{ 
        position: 'fixed', 
        bottom: 10, 
        right: 10, 
        background: '#fff', 
        border: '2px solid #000',
        padding: 16,
        maxWidth: 400,
        maxHeight: 500,
        overflow: 'auto',
        zIndex: 9999,
        borderRadius: 8,
        boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
        fontSize: 12,
        fontFamily: 'monospace'
      }}
    >
      <h3 style={{ marginTop: 0, marginBottom: 10, fontSize: 14, fontWeight: 'bold' }}>
        🔍 i18n Debug Panel
      </h3>
      
      <div style={{ marginBottom: 10 }}>
        <strong>Текущий язык:</strong> {i18n.language}
      </div>
      
      <div style={{ marginBottom: 10 }}>
        <strong>Загруженные языки:</strong> {i18n.languages.join(', ')}
      </div>
      
      <div style={{ marginBottom: 10 }}>
        <strong>Тестовые переводы:</strong>
        <ul style={{ margin: 0, paddingLeft: 20 }}>
          {testKeys.map(key => (
            <li key={key} style={{ marginBottom: 4 }}>
              <code>{key}</code>: <strong>{t(key)}</strong>
            </li>
          ))}
        </ul>
      </div>
      
      <div style={{ marginBottom: 10 }}>
        <strong>Переключить язык:</strong>
        <div style={{ display: 'flex', gap: 4, marginTop: 4 }}>
          {['ru', 'en', 'uk', 'de'].map(lng => (
            <button 
              key={lng}
              onClick={() => i18n.changeLanguage(lng)}
              style={{
                padding: '4px 8px',
                border: '1px solid #ccc',
                borderRadius: 4,
                background: i18n.language === lng ? '#0066cc' : '#fff',
                color: i18n.language === lng ? '#fff' : '#000',
                cursor: 'pointer',
                fontSize: 11,
                textTransform: 'uppercase',
                fontWeight: i18n.language === lng ? 'bold' : 'normal'
              }}
            >
              {lng}
            </button>
          ))}
        </div>
      </div>
      
      <div style={{ fontSize: 10, color: '#666', marginTop: 10, paddingTop: 10, borderTop: '1px solid #eee' }}>
        localStorage: {localStorage.getItem('i18nextLng') || 'не установлен'}
      </div>
    </div>
  );
};
