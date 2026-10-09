import { expect, it, vi } from 'vitest';

it('opens in Vietnamese when the user has not picked a language', async () => {
  localStorage.removeItem('voicestudio.locale');
  vi.resetModules();
  const { default: i18n, DEFAULT_LOCALE } = await import('./index');
  expect(DEFAULT_LOCALE).toBe('vi');
  expect(i18n.language).toBe('vi');
  expect(document.documentElement.lang).toBe('vi');
});

it('keeps a language the user picked explicitly', async () => {
  localStorage.setItem('voicestudio.locale', 'en');
  vi.resetModules();
  const { default: i18n } = await import('./index');
  expect(i18n.language).toBe('en');
});
