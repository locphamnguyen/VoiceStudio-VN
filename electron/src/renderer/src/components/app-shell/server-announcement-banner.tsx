import { useCallback, useEffect, useState } from 'react';
import { InfoIcon, TriangleAlertIcon, XIcon } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { apiJson } from '@/lib/api/client';
import { cn } from '@/lib/utils';
import { getBridge } from '../bridge';

/**
 * Thin notice strip fed by the VoiceStudio-VN central page (phone-home, port of
 * ZaloCRM's ServerAnnouncementBanner): "a new version is out", "read this".
 * The backend caches the central answer (services/phone_home.py); the central
 * page returning null hides the strip everywhere.
 *
 * Placed at the BOTTOM of the workspace column, above the sponsor footer: the
 * top edge of every workspace is a window drag region (frameless title bar,
 * macOS traffic lights, the fixed notifications button), where a clickable
 * strip would either swallow drags or be unclickable. The bottom edge is the
 * same on macOS, Windows, Linux and the browser build.
 *
 * Text only — never HTML. Links are https-only (the backend already rejects
 * anything else) and open in the system browser.
 */

export interface ServerAnnouncement {
  id: string;
  text: string;
  level: 'info' | 'warning' | 'critical';
  link: string | null;
  linkLabel: string | null;
  dismissible: boolean;
}

export const DISMISSED_KEY = 'voicestudio.announcement-dismissed-id';
export const POLL_INTERVAL_MS = 30 * 60 * 1000;

function readDismissed(): string | null {
  try {
    return localStorage.getItem(DISMISSED_KEY);
  } catch {
    return null;
  }
}

export async function fetchServerAnnouncement(): Promise<ServerAnnouncement | null> {
  try {
    const body = await apiJson<{ announcement?: ServerAnnouncement | null }>('/announcement');
    const a = body?.announcement;
    return a && typeof a.id === 'string' && typeof a.text === 'string' ? a : null;
  } catch {
    // Best effort: an older backend (404), a busy one or no session all just hide the strip.
    return null;
  }
}

export function useServerAnnouncement() {
  const [announcement, setAnnouncement] = useState<ServerAnnouncement | null>(null);
  const [dismissedId, setDismissedId] = useState<string | null>(readDismissed);

  useEffect(() => {
    let alive = true;
    const load = () =>
      void fetchServerAnnouncement().then((a) => {
        if (alive) setAnnouncement(a);
      });
    load();
    const timer = window.setInterval(load, POLL_INTERVAL_MS);
    return () => {
      alive = false;
      window.clearInterval(timer);
    };
  }, []);

  const dismiss = useCallback(() => {
    if (!announcement?.dismissible) return;
    setDismissedId(announcement.id);
    try {
      localStorage.setItem(DISMISSED_KEY, announcement.id);
    } catch {
      // Storage blocked: still hidden for this session through state.
    }
  }, [announcement]);

  const visible =
    !!announcement && (!announcement.dismissible || dismissedId !== announcement.id);
  return { announcement, visible, dismiss };
}

const LEVEL_CLASS: Record<ServerAnnouncement['level'], string> = {
  info: 'border-primary/25 bg-primary/10 text-foreground',
  warning: 'border-amber-500/30 bg-amber-500/10 text-amber-900 dark:text-amber-200',
  critical: 'border-destructive/35 bg-destructive/10 text-destructive',
};

export function ServerAnnouncementBanner() {
  const { t } = useTranslation();
  const { announcement, visible, dismiss } = useServerAnnouncement();
  if (!visible || !announcement) return null;
  const level = LEVEL_CLASS[announcement.level] ? announcement.level : 'info';
  const Icon = level === 'info' ? InfoIcon : TriangleAlertIcon;
  return (
    <div
      role="status"
      data-testid="server-announcement"
      data-level={level}
      className={cn(
        'app-no-drag flex shrink-0 items-center gap-2 border-t px-3 py-1.5 text-xs',
        LEVEL_CLASS[level],
      )}
    >
      <Icon aria-hidden="true" className="size-3.5 shrink-0" />
      <p className="m-0 min-w-0 flex-1 break-words">{announcement.text}</p>
      {announcement.link && (
        <a
          href={announcement.link}
          target="_blank"
          rel="noopener noreferrer"
          className="shrink-0 font-semibold underline underline-offset-2"
          onClick={(event) => {
            const bridge = getBridge();
            if (!bridge || !announcement.link) return;
            event.preventDefault();
            void bridge.files.openExternal(announcement.link).catch(() => {});
          }}
        >
          {announcement.linkLabel || t('announcement.details')}
        </a>
      )}
      {announcement.dismissible && (
        <button
          type="button"
          onClick={dismiss}
          aria-label={t('announcement.dismiss')}
          title={t('announcement.dismiss')}
          className="shrink-0 rounded p-0.5 opacity-70 hover:opacity-100 focus-visible:outline-2 focus-visible:outline-ring"
        >
          <XIcon aria-hidden="true" className="size-3.5" />
        </button>
      )}
    </div>
  );
}
