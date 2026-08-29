import { Injectable, signal } from '@angular/core';

const STORAGE_KEY = 'theme-preference';

function prefersDark(): boolean {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored === 'light' || stored === 'dark') {
    return stored === 'dark';
  }
  return matchMedia('(prefers-color-scheme: dark)').matches;
}

/**
 * Dark mode (`UX-064`), superseding `UX-053`'s "not doing" — default stays
 * light (`UI-001`'s legibility concern), the borrower opts in and the
 * choice is remembered. A signal, not a `BehaviorSubject`: nothing here is
 * asynchronous, and `AppHeaderComponent`'s toggle just reads it directly.
 */
@Injectable({ providedIn: 'root' })
export class ThemeService {
  readonly isDark = signal(prefersDark());

  constructor() {
    this.apply(this.isDark());
  }

  toggle(): void {
    const next = !this.isDark();
    this.isDark.set(next);
    localStorage.setItem(STORAGE_KEY, next ? 'dark' : 'light');
    this.apply(next);
  }

  private apply(dark: boolean): void {
    document.documentElement.classList.toggle('dark', dark);
  }
}
