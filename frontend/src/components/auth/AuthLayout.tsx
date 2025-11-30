import React from 'react';

interface AuthLayoutProps {
  hero: React.ReactNode;
  primary: React.ReactNode;
  secondary?: React.ReactNode;
}

const AuthLayout: React.FC<AuthLayoutProps> = ({ hero, primary, secondary }) => (
  <section
    data-testid="auth-layout"
    className="relative z-10 flex min-h-screen w-full flex-col items-center justify-center px-4 py-10 md:px-6 xl:px-10"
  >
    <div className="absolute top-0 left-0 right-0 w-full px-6 py-6 md:px-10 md:py-8">
      <div className="mx-auto max-w-screen-xl">
        {hero}
      </div>
    </div>

    {secondary ? (
      <div className="mx-auto w-full max-w-screen-xl grid auto-rows-max gap-8 md:grid-cols-[minmax(0,1fr)_minmax(320px,420px)] md:items-start xl:grid-cols-[minmax(0,0.85fr)_minmax(360px,480px)] xl:gap-12">
        <div className="order-2 space-y-6 md:order-1">{secondary}</div>
        <div className="order-1 md:order-2">{primary}</div>
      </div>
    ) : (
      <div className="w-full max-w-[420px]">{primary}</div>
    )}
  </section>
);

export default AuthLayout;
