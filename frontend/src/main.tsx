import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import { ThemePreferenceProvider } from './hooks/useThemePreference';
import './styles/tokens.css';
import './index.css';
import './i18n';

try {
  ReactDOM.createRoot(document.getElementById('root')!).render(
    <React.StrictMode>
      <ThemePreferenceProvider>
        <App />
      </ThemePreferenceProvider>
    </React.StrictMode>
  );
} catch (error) {
  console.error("Caught error:", error);
}
