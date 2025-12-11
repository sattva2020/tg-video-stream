import React, { useEffect, useState } from 'react';

interface LoadingBarProps {
  isLoading: boolean;
}

export const LoadingBar: React.FC<LoadingBarProps> = ({ isLoading }) => {
  const [progress, setProgress] = useState(0);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    let interval: NodeJS.Timeout;
    let timeout: NodeJS.Timeout;

    if (isLoading) {
      setVisible(true);
      setProgress(0);
      
      // Быстрый старт до 30%
      interval = setInterval(() => {
        setProgress(prev => {
          if (prev < 30) return prev + 10;
          if (prev < 60) return prev + 5;
          if (prev < 85) return prev + 2;
          if (prev < 95) return prev + 0.5;
          return prev;
        });
      }, 100);
    } else {
      // Завершение загрузки
      setProgress(100);
      timeout = setTimeout(() => {
        setVisible(false);
        setProgress(0);
      }, 300);
    }

    return () => {
      clearInterval(interval);
      clearTimeout(timeout);
    };
  }, [isLoading]);

  if (!visible) return null;

  return (
    <div className="fixed top-0 left-0 right-0 z-[9999] h-1 bg-transparent">
      <div
        className="h-full bg-gradient-to-r from-cyan-400 via-blue-500 to-purple-500 transition-all duration-200 ease-out shadow-lg shadow-blue-500/50"
        style={{ 
          width: `${progress}%`,
          boxShadow: '0 0 10px rgba(59, 130, 246, 0.8), 0 0 20px rgba(59, 130, 246, 0.4)'
        }}
      />
    </div>
  );
};

export default LoadingBar;
