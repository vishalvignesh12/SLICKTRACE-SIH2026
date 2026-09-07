import React, { useState } from 'react';
import { useNavigation } from '../../context/NavigationContext';
import { api } from '../../services/api';
import Button from '../common/Button';

export default function LoginView() {
  const { navigateTo, setIsAuthenticated, setUser } = useNavigation();
  const [email, setEmail] = useState('officer.verma@coastguard.gov.in');
  const [password, setPassword] = useState('SIH2026@CoastGuard');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await api.login(email, password);
      if (res && res.access_token) {
        try {
          const me = await api.getMe();
          if (setUser) setUser(me);
        } catch {
          // ignore
        }
        setIsAuthenticated(true);
        navigateTo('dashboard');
      } else {
        setError('Authentication failed. Please verify credentials.');
      }
    } catch (err) {
      setError(err.message || 'Authentication failed. Please check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-surface text-on-surface min-h-screen flex flex-col antialiased">
      <main className="flex-1 flex w-full">
        {/* Left Side: Visual Hero */}
        <section className="hidden lg:block w-1/2 relative bg-primary overflow-hidden">
          <div className="absolute inset-0 map-layer opacity-40"></div>
          <div className="absolute inset-0 bg-gradient-to-tr from-primary via-primary/90 to-transparent"></div>
          
          <div className="absolute top-12 left-12 flex items-center gap-3">
            <div className="w-10 h-10 bg-secondary rounded flex items-center justify-center text-on-secondary font-bold text-xl">
              M
            </div>
            <span className="text-on-primary font-bold text-headline-md tracking-tight">
              Maritime Intel
            </span>
          </div>

          <div className="absolute bottom-16 left-12 max-w-lg text-on-primary">
            <div className="inline-flex items-center gap-2 px-3 py-1 bg-secondary/20 border border-secondary/40 rounded text-secondary-fixed text-label-sm font-semibold mb-4">
              <span className="w-2 h-2 rounded-full bg-secondary-fixed animate-pulse"></span>
              Surveillance Matrix Active
            </div>
            <h2 className="text-headline-lg font-bold text-on-primary mb-3">
              National Marine Oil Spill Monitoring
            </h2>
            <p className="text-body-md text-on-primary/80 leading-relaxed">
              Real-time geospatial observation network monitoring coastal territories for environmental anomalies, satellite radar slicks, and automated vessel compliance attribution.
            </p>
          </div>
        </section>

        {/* Right Side: Login Panel */}
        <section className="w-full lg:w-1/2 flex items-center justify-center bg-surface-container-lowest p-6 sm:p-12">
          <div className="w-full max-w-[440px] flex flex-col">
            <div className="mb-8">
              <h1 className="text-headline-lg font-bold text-primary mb-2">
                Secure Access Portal
              </h1>
              <div className="inline-flex items-center gap-2 px-3 py-1 bg-surface-container-high rounded border border-outline-variant mb-4">
                <span className="material-symbols-outlined text-primary text-[16px]">admin_panel_settings</span>
                <span className="text-label-sm uppercase font-bold tracking-wider text-on-surface">
                  Authorized Personnel Only
                </span>
              </div>
              <p className="text-body-md text-on-surface-variant">
                Sign in to access satellite-based oil spill monitoring, vessel attribution, and maritime environmental intelligence.
              </p>
            </div>

            {error && (
              <div className="mb-4 p-3.5 bg-error-container text-on-error-container rounded-lg text-label-sm font-semibold border border-error/30 flex items-center gap-2">
                <span className="material-symbols-outlined text-[18px] text-error">error</span>
                <span>{error}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="flex flex-col gap-5">
              <div className="flex flex-col gap-1.5">
                <label className="text-label-md text-on-surface font-bold" htmlFor="email">
                  Official Email / User ID
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-outline">
                    <span className="material-symbols-outlined text-[18px]">person</span>
                  </div>
                  <input
                    id="email"
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full pl-10 pr-4 py-3 bg-surface-container-lowest border border-outline rounded text-on-surface text-body-md focus:ring-2 focus:ring-primary focus:border-primary transition-colors outline-none"
                  />
                </div>
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="text-label-md text-on-surface font-bold" htmlFor="password">
                  Password
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-outline">
                    <span className="material-symbols-outlined text-[18px]">lock</span>
                  </div>
                  <input
                    id="password"
                    type={showPassword ? 'text' : 'password'}
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full pl-10 pr-12 py-3 bg-surface-container-lowest border border-outline rounded text-on-surface text-body-md focus:ring-2 focus:ring-primary focus:border-primary transition-colors outline-none"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute inset-y-0 right-0 pr-3 flex items-center text-outline hover:text-on-surface transition-colors"
                  >
                    <span className="material-symbols-outlined text-[18px]">
                      {showPassword ? 'visibility_off' : 'visibility'}
                    </span>
                  </button>
                </div>
              </div>

              <div className="flex items-center justify-between text-label-sm">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input type="checkbox" defaultChecked className="rounded border-outline text-primary focus:ring-primary" />
                  <span className="text-on-surface-variant">Remember this terminal</span>
                </label>
                <a href="#forgot" onClick={(e) => { e.preventDefault(); alert('Password reset dispatched to authorized administrator.'); }} className="text-primary font-bold hover:underline">
                  Forgot credentials?
                </a>
              </div>

              <Button type="submit" size="lg" icon="lock_person" disabled={loading} className="w-full mt-2">
                {loading ? 'Authenticating...' : 'Sign In Securely'}
              </Button>
            </form>

            <div className="mt-8 p-4 bg-error-container/30 border border-error-container rounded flex items-start gap-3">
              <span className="material-symbols-outlined text-error shrink-0 text-[20px]">gavel</span>
              <p className="text-[12px] text-on-surface-variant leading-relaxed">
                <strong className="text-on-surface block mb-0.5">Government Surveillance Network.</strong>
                All activities on this system are monitored, encrypted, and legally audited. Unauthorized access is subject to statutory penalties under maritime law.
              </p>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
