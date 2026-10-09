import { useEffect, useState } from 'react';
import { LogOutIcon, UserRoundIcon, UsersIcon } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { accountPageUrl, apiPath } from '@/lib/api/client';

export interface AccountUser {
  email: string;
  full_name: string;
  is_admin: boolean;
}

/** Signed-in user from the account gate; null when accounts are off or signed out. */
export async function fetchAccountUser(): Promise<AccountUser | null> {
  try {
    const res = await fetch(apiPath('/account/me'), {
      credentials: 'include',
      headers: { Accept: 'application/json' },
    });
    if (!res.ok) return null;
    const body = (await res.json()) as { enabled?: boolean; user?: AccountUser | null };
    return body.enabled && body.user ? body.user : null;
  } catch {
    return null;
  }
}

const linkClass =
  'app-no-drag flex h-8 items-center gap-1.5 rounded-md px-2 text-xs text-muted-foreground hover:bg-accent hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring';

/**
 * Web deployment only: who is signed in, plus links to the server-rendered
 * account pages (profile / password, member approval for admins, sign out).
 * The desktop app runs with accounts off, so this renders nothing there.
 */
export function AccountMenu() {
  const { t } = useTranslation();
  const [user, setUser] = useState<AccountUser | null>(null);

  useEffect(() => {
    if (!__WEB_DEPLOYMENT__) return;
    let alive = true;
    void fetchAccountUser().then((u) => {
      if (alive) setUser(u);
    });
    return () => {
      alive = false;
    };
  }, []);

  if (!user) return null;
  const name = user.full_name || user.email;
  return (
    <div className="flex shrink-0 items-center gap-0.5" data-testid="account-menu">
      <Tooltip>
        <TooltipTrigger
          render={
            <a href={accountPageUrl('profile')} className={linkClass} aria-label={t('account.profile')} />
          }
        >
          <UserRoundIcon aria-hidden="true" className="size-3.5" />
          <span className="hidden max-w-32 truncate sm:inline">{name}</span>
        </TooltipTrigger>
        <TooltipContent surface="theme" side="bottom">
          {t('account.signed_in_as', { email: user.email })}
        </TooltipContent>
      </Tooltip>
      {user.is_admin && (
        <Tooltip>
          <TooltipTrigger
            render={
              <a href={accountPageUrl('members')} className={linkClass} aria-label={t('account.members')} />
            }
          >
            <UsersIcon aria-hidden="true" className="size-3.5" />
          </TooltipTrigger>
          <TooltipContent surface="theme" side="bottom">
            {t('account.members')}
          </TooltipContent>
        </Tooltip>
      )}
      <Tooltip>
        <TooltipTrigger
          render={
            <a href={accountPageUrl('logout')} className={linkClass} aria-label={t('account.logout')} />
          }
        >
          <LogOutIcon aria-hidden="true" className="size-3.5" />
        </TooltipTrigger>
        <TooltipContent surface="theme" side="bottom">
          {t('account.logout')}
        </TooltipContent>
      </Tooltip>
    </div>
  );
}
