import { HugeiconsIcon } from '@hugeicons/react';
import type { IconSvgElement } from '@hugeicons/react';
import type { SVGAttributes } from 'react';

export type { IconSvgElement };

export interface IconProps extends Omit<SVGAttributes<SVGSVGElement>, 'color'> {
  icon: IconSvgElement;
  size?: number | string;
  strokeWidth?: number;
  className?: string;
}

/**
 * Composant icône unifié basé sur Hugeicons (@hugeicons/react).
 * Trait fin et constant (strokeWidth 1.75 par défaut) pour un rendu éditorial et sobre.
 */
export function Icon({
  icon,
  size = 18,
  strokeWidth = 1.75,
  className,
  ...props
}: IconProps) {
  return (
    <HugeiconsIcon
      icon={icon}
      size={size}
      strokeWidth={strokeWidth}
      className={className}
      aria-hidden="true"
      {...props}
    />
  );
}
