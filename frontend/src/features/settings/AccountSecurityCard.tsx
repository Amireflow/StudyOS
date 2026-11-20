import { useEffect, useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Cancel01Icon,
  CheckmarkCircle02Icon,
  Logout01Icon,
  ShieldCheckIcon,
} from '@hugeicons/core-free-icons';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { FormField, Input } from '../../components/ui/FormFields';
import { Icon } from '../../components/ui/Icon';
import { fetchAccountInfoApi, type AuthAccountInfo } from '../../lib/studyApi';
import { useAuth } from '../../state/AuthContext';

/**
 * Carte Sécurité & Compte (affichée uniquement en session API authentifiée) :
 * permet de changer le mot de passe et de révoquer toutes les sessions actives.
 */
export function AccountSecurityCard() {
  const { session, changePassword, logoutAllSessions } = useAuth();
  const navigate = useNavigate();

  const [accountInfo, setAccountInfo] = useState<AuthAccountInfo | null>(null);
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [isUpdatingPassword, setIsUpdatingPassword] = useState(false);
  const [isRevoking, setIsRevoking] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    if (session?.mode !== 'api' || !session.accessToken) {
      setAccountInfo(null);
      return;
    }
    let active = true;
    fetchAccountInfoApi(session.accessToken)
      .then((info) => {
        if (active && info && typeof info === 'object' && typeof info.id === 'string') {
          setAccountInfo(info);
        }
      })
      .catch(() => {
        // Ignore si l'endpoint n'est pas joignable (ex. tests mockés)
      });
    return () => {
      active = false;
    };
  }, [session?.mode, session?.accessToken]);

  if (session?.mode !== 'api') {
    return null;
  }

  const canChangeLocalPassword = accountInfo
    ? accountInfo.canChangePassword
    : session.authProvider !== 'supabase' && session.authProvider !== 'local_dev';

  const handlePasswordSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setFeedback(null);
    setErrorMessage(null);

    if (!currentPassword) {
      setErrorMessage('Saisissez votre mot de passe actuel.');
      return;
    }
    if (newPassword.length < 8) {
      setErrorMessage('Le nouveau mot de passe doit contenir au moins 8 caractères.');
      return;
    }
    if (newPassword !== confirmPassword) {
      setErrorMessage('Les nouveaux mots de passe ne correspondent pas.');
      return;
    }

    setIsUpdatingPassword(true);
    try {
      await changePassword(currentPassword, newPassword);
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      setFeedback('Mot de passe mis à jour. Vos autres appareils ont été déconnectés.');
    } catch (err) {
      setErrorMessage(
        err instanceof Error ? err.message : 'Impossible de modifier le mot de passe.',
      );
    } finally {
      setIsUpdatingPassword(false);
    }
  };

  const handleLogoutAll = async () => {
    setIsRevoking(true);
    try {
      navigate('/login', { replace: true, state: null });
      await logoutAllSessions();
    } finally {
      setIsRevoking(false);
    }
  };

  return (
    <section
      aria-label="Compte et sécurité"
      className="space-y-4 rounded-2xl bg-white p-5 dark:bg-zinc-900"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Icon icon={ShieldCheckIcon} size={17} className="text-teal-700 dark:text-teal-400" />
          <h2 className="text-base font-semibold text-zinc-900 dark:text-zinc-50">
            Compte & Sécurité
          </h2>
          {accountInfo && (
            <Badge variant={accountInfo.emailVerified ? 'success' : 'neutral'}>
              {accountInfo.emailVerified ? 'E-mail vérifié' : 'E-mail non vérifié'}
            </Badge>
          )}
        </div>

        <Button
          type="button"
          variant="secondary"
          size="sm"
          isLoading={isRevoking}
          onClick={() => void handleLogoutAll()}
        >
          <Icon icon={Logout01Icon} size={14} />
          Déconnecter tous mes appareils
        </Button>
      </div>

      {feedback && (
        <div
          role="status"
          className="flex items-center justify-between gap-2 rounded-xl bg-emerald-50/90 px-3.5 py-2.5 text-xs font-medium text-emerald-900 dark:bg-emerald-950/50 dark:text-emerald-200"
        >
          <span>{feedback}</span>
          <button
            type="button"
            onClick={() => setFeedback(null)}
            aria-label="Fermer le message sécurité"
            className="rounded p-0.5 hover:bg-emerald-100 dark:hover:bg-emerald-900"
          >
            <Icon icon={Cancel01Icon} size={13} />
          </button>
        </div>
      )}

      {errorMessage && (
        <div
          role="alert"
          className="flex items-center justify-between gap-2 rounded-xl bg-rose-50/90 px-3.5 py-2.5 text-xs font-medium text-rose-900 dark:bg-rose-950/50 dark:text-rose-200"
        >
          <span>{errorMessage}</span>
          <button
            type="button"
            onClick={() => setErrorMessage(null)}
            aria-label="Fermer l’erreur sécurité"
            className="rounded p-0.5 hover:bg-rose-100 dark:hover:bg-rose-900"
          >
            <Icon icon={Cancel01Icon} size={13} />
          </button>
        </div>
      )}

      {canChangeLocalPassword && (
        <form onSubmit={handlePasswordSubmit} noValidate className="space-y-3">
          <div className="grid gap-3 sm:grid-cols-3">
            <FormField id="account-current-password" label="Mot de passe actuel" required>
              <Input
                id="account-current-password"
                type="password"
                autoComplete="current-password"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
              />
            </FormField>

            <FormField id="account-new-password" label="Nouveau mot de passe" required>
              <Input
                id="account-new-password"
                type="password"
                autoComplete="new-password"
                placeholder="Minimum 8 caractères"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
              />
            </FormField>

            <FormField id="account-confirm-password" label="Confirmer le mot de passe" required>
              <Input
                id="account-confirm-password"
                type="password"
                autoComplete="new-password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
              />
            </FormField>
          </div>

          <div className="flex justify-end">
            <Button type="submit" variant="primary" size="sm" isLoading={isUpdatingPassword}>
              <Icon icon={CheckmarkCircle02Icon} size={14} />
              Mettre à jour le mot de passe
            </Button>
          </div>
        </form>
      )}
    </section>
  );
}
