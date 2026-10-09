import { cleanup, render, screen, waitFor } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import { TooltipProvider } from '@/components/ui/tooltip';
import { AccountMenu, fetchAccountUser } from './account-menu';

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

function respond(body: unknown, status = 200) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => new Response(JSON.stringify(body), { status })),
  );
}

it('reads the signed-in user from /account/me', async () => {
  respond({ enabled: true, user: { email: 'a@vi.vn', full_name: 'A', is_admin: false } });
  await expect(fetchAccountUser()).resolves.toMatchObject({ email: 'a@vi.vn' });
});

it('treats accounts-off and signed-out as no user', async () => {
  respond({ enabled: false, user: null });
  await expect(fetchAccountUser()).resolves.toBeNull();
  respond({ error: { message: 'x' } }, 401);
  await expect(fetchAccountUser()).resolves.toBeNull();
});

it('renders nothing outside the web deployment', async () => {
  respond({ enabled: true, user: { email: 'a@vi.vn', full_name: 'A', is_admin: true } });
  render(
    <TooltipProvider>
      <AccountMenu />
    </TooltipProvider>,
  );
  await waitFor(() => expect(screen.queryByTestId('account-menu')).toBeNull());
});

it('recognises the account gate answer and builds account page URLs', async () => {
  const { ApiError, accountPageUrl, isAccountLoginRequired } = await import('@/lib/api/client');
  expect(isAccountLoginRequired(new ApiError(401, 'account login required'))).toBe(true);
  expect(isAccountLoginRequired(new ApiError(403, 'account login required'))).toBe(true);
  expect(isAccountLoginRequired(new ApiError(401, 'API key required'))).toBe(false);
  expect(accountPageUrl('login')).toMatch(/\/account\/login$/);
});
