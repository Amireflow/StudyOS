import { HelpCircleIcon } from '@hugeicons/core-free-icons';
import { Link } from 'react-router-dom';
import { buttonClasses } from '../components/ui/Button';
import { Card, CardContent } from '../components/ui/Card';
import { Icon } from '../components/ui/Icon';
import { EmptyState } from '../components/ui/StateFeedback';

/**
 * Écran 404 affiché lorsqu'une route n'existe pas.
 */
export function NotFoundPage() {
  return (
    <div className="space-y-5">
      <header>
        <h1 className="text-xl font-semibold tracking-tight text-zinc-900 sm:text-2xl">
          Page introuvable
        </h1>
      </header>

      <Card>
        <CardContent className="py-6">
          <EmptyState
            icon={<Icon icon={HelpCircleIcon} size={18} />}
            title="Contenu introuvable (404)"
            action={
              <Link to="/" className={buttonClasses('primary', 'sm')}>
                Retour au tableau de bord
              </Link>
            }
          />
        </CardContent>
      </Card>
    </div>
  );
}
