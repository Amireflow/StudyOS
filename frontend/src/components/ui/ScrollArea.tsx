import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type HTMLAttributes,
  type PointerEvent as ReactPointerEvent,
  type ReactNode,
} from 'react';
import { cn } from '../../lib/cn';

export interface ScrollAreaProps extends HTMLAttributes<HTMLElement> {
  as?: 'div' | 'nav';
  viewportClassName?: string;
  children: ReactNode;
}

/**
 * Zone de défilement personnalisée (remplace la barre native du navigateur par
 * un curseur fin flottant sans flèches, interactif au glisser-déposer et au clic).
 */
export function ScrollArea({
  as = 'div',
  className,
  viewportClassName,
  children,
  ...props
}: ScrollAreaProps) {
  const viewportRef = useRef<HTMLDivElement | null>(null);
  const trackRef = useRef<HTMLDivElement | null>(null);
  const hideTimerRef = useRef<number | null>(null);
  const dragStateRef = useRef<{ startY: number; startScrollTop: number } | null>(null);

  const [thumb, setThumb] = useState({ height: 0, top: 0, visible: false });
  const [isScrolling, setIsScrolling] = useState(false);
  const [isDragging, setIsDragging] = useState(false);

  const updateMetrics = useCallback(() => {
    const el = viewportRef.current;
    if (!el) return;
    const { scrollHeight, clientHeight, scrollTop } = el;
    if (scrollHeight <= clientHeight + 1 || clientHeight <= 0) {
      setThumb((prev) => (prev.visible ? { height: 0, top: 0, visible: false } : prev));
      return;
    }

    const trackHeight = clientHeight - 8;
    const ratio = clientHeight / scrollHeight;
    const thumbHeight = Math.max(28, Math.round(trackHeight * ratio));
    const maxScrollTop = Math.max(1, scrollHeight - clientHeight);
    const maxThumbTop = Math.max(0, trackHeight - thumbHeight);
    const thumbTop = Math.round((scrollTop / maxScrollTop) * maxThumbTop);

    setThumb({
      height: thumbHeight,
      top: thumbTop,
      visible: true,
    });
  }, []);

  useEffect(() => {
    const el = viewportRef.current;
    if (!el) return;

    updateMetrics();

    const handleScroll = () => {
      updateMetrics();
      setIsScrolling(true);
      if (hideTimerRef.current !== null) {
        window.clearTimeout(hideTimerRef.current);
      }
      hideTimerRef.current = window.setTimeout(() => {
        setIsScrolling(false);
      }, 900);
    };

    el.addEventListener('scroll', handleScroll, { passive: true });
    window.addEventListener('resize', updateMetrics);

    let resizeObserver: ResizeObserver | null = null;
    if (typeof ResizeObserver !== 'undefined') {
      resizeObserver = new ResizeObserver(updateMetrics);
      resizeObserver.observe(el);
      if (el.firstElementChild) {
        resizeObserver.observe(el.firstElementChild);
      }
    }

    let mutationObserver: MutationObserver | null = null;
    if (typeof MutationObserver !== 'undefined') {
      mutationObserver = new MutationObserver(updateMetrics);
      mutationObserver.observe(el, { childList: true, subtree: true });
    }

    return () => {
      el.removeEventListener('scroll', handleScroll);
      window.removeEventListener('resize', updateMetrics);
      resizeObserver?.disconnect();
      mutationObserver?.disconnect();
      if (hideTimerRef.current !== null) {
        window.clearTimeout(hideTimerRef.current);
      }
    };
  }, [updateMetrics]);

  const handleThumbPointerDown = (event: ReactPointerEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.stopPropagation();
    const el = viewportRef.current;
    if (!el) return;

    dragStateRef.current = {
      startY: event.clientY,
      startScrollTop: el.scrollTop,
    };
    setIsDragging(true);
    event.currentTarget.setPointerCapture?.(event.pointerId);
  };

  const handleThumbPointerMove = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (!dragStateRef.current || !viewportRef.current) return;
    const el = viewportRef.current;
    const trackHeight = Math.max(1, el.clientHeight - 8);
    const maxThumbTop = Math.max(1, trackHeight - thumb.height);
    const maxScrollTop = Math.max(1, el.scrollHeight - el.clientHeight);
    const deltaY = event.clientY - dragStateRef.current.startY;
    el.scrollTop = dragStateRef.current.startScrollTop + (deltaY / maxThumbTop) * maxScrollTop;
  };

  const handleThumbPointerUp = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (!dragStateRef.current) return;
    dragStateRef.current = null;
    setIsDragging(false);
    event.currentTarget.releasePointerCapture?.(event.pointerId);
  };

  const handleTrackClick = (event: ReactPointerEvent<HTMLDivElement>) => {
    const el = viewportRef.current;
    const track = trackRef.current;
    if (!el || !track || event.target !== track) return;

    const rect = track.getBoundingClientRect();
    const clickY = event.clientY - rect.top;
    const ratio = Math.min(1, Math.max(0, (clickY - thumb.height / 2) / Math.max(1, rect.height - thumb.height)));
    el.scrollTo({
      top: ratio * (el.scrollHeight - el.clientHeight),
      behavior: 'smooth',
    });
  };

  const Container = as;

  return (
    <Container
      className={cn('group/scroll relative min-h-0 overflow-hidden', className)}
      {...props}
    >
      <div
        ref={viewportRef}
        className={cn('no-scrollbar h-full w-full overflow-y-auto', viewportClassName)}
      >
        {children}
      </div>

      {thumb.visible && (
        <div
          ref={trackRef}
          aria-hidden="true"
          onPointerDown={handleTrackClick}
          className={cn(
            'absolute inset-y-1 right-1 z-10 w-2 rounded-full transition-opacity duration-200',
            isScrolling || isDragging
              ? 'opacity-100'
              : 'opacity-0 group-hover/scroll:opacity-100',
          )}
        >
          <div
            onPointerDown={handleThumbPointerDown}
            onPointerMove={handleThumbPointerMove}
            onPointerUp={handleThumbPointerUp}
            onPointerCancel={handleThumbPointerUp}
            style={{
              height: `${thumb.height}px`,
              transform: `translateY(${thumb.top}px)`,
            }}
            className={cn(
              'mx-auto w-1.5 rounded-full transition-colors cursor-pointer',
              isDragging
                ? 'bg-teal-600 dark:bg-teal-400'
                : 'bg-zinc-400/60 hover:bg-zinc-500/80 dark:bg-zinc-500/50 dark:hover:bg-zinc-400/75',
            )}
          />
        </div>
      )}
    </Container>
  );
}
