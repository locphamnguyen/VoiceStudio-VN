import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { DISMISSED_KEY, ServerAnnouncementBanner } from './server-announcement-banner';

const notice = {
  id: 'rel-0.6',
  text: 'Đã có bản 0.6',
  level: 'warning',
  link: 'https://example.com/release',
  linkLabel: null,
  dismissible: true,
};

function serve(announcement: unknown, status = 200) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => new Response(JSON.stringify({ announcement }), { status })),
  );
}

beforeEach(() => localStorage.removeItem(DISMISSED_KEY));
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

async function mount() {
  await act(async () => {
    render(<ServerAnnouncementBanner />);
  });
}

it('shows the cached announcement as plain text with an https link', async () => {
  serve({ ...notice, text: '<b>bold</b>' });
  await mount();
  const strip = screen.getByTestId('server-announcement');
  expect(strip).toHaveAttribute('data-level', 'warning');
  expect(strip).toHaveTextContent('<b>bold</b>');
  expect(strip.querySelector('b')).toBeNull();
  expect(screen.getByRole('link')).toHaveAttribute('href', notice.link);
});

it('hides when the central page has nothing, or the backend is unreachable', async () => {
  serve(null);
  await mount();
  expect(screen.queryByTestId('server-announcement')).toBeNull();
  cleanup();
  serve(null, 404);
  await mount();
  expect(screen.queryByTestId('server-announcement')).toBeNull();
});

it('remembers a dismissed id, and a new id shows again', async () => {
  serve(notice);
  await mount();
  fireEvent.click(screen.getByRole('button'));
  expect(screen.queryByTestId('server-announcement')).toBeNull();
  expect(localStorage.getItem(DISMISSED_KEY)).toBe('rel-0.6');
  cleanup();
  await mount();
  expect(screen.queryByTestId('server-announcement')).toBeNull();
  cleanup();
  serve({ ...notice, id: 'rel-0.7' });
  await mount();
  expect(screen.getByTestId('server-announcement')).toBeInTheDocument();
});

it('non-dismissible notices have no close button and ignore a stored dismissal', async () => {
  localStorage.setItem(DISMISSED_KEY, 'sec-1');
  serve({ ...notice, id: 'sec-1', level: 'critical', dismissible: false, link: null });
  await mount();
  expect(screen.getByTestId('server-announcement')).toHaveAttribute('data-level', 'critical');
  expect(screen.queryByRole('button')).toBeNull();
});
