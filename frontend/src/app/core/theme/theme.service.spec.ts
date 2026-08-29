import { TestBed } from '@angular/core/testing';

import { ThemeService } from './theme.service';

function stubMatchMedia(matches: boolean): void {
  vi.stubGlobal(
    'matchMedia',
    vi.fn().mockImplementation((query: string) => ({
      matches,
      media: query,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    })),
  );
}

describe('ThemeService', () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.classList.remove('dark');
  });

  it('toggling flips the class and persists the choice', () => {
    stubMatchMedia(false);
    const service = TestBed.inject(ThemeService);
    expect(service.isDark()).toBe(false);
    expect(document.documentElement.classList.contains('dark')).toBe(false);

    service.toggle();

    expect(service.isDark()).toBe(true);
    expect(document.documentElement.classList.contains('dark')).toBe(true);
    expect(localStorage.getItem('theme-preference')).toBe('dark');

    service.toggle();

    expect(service.isDark()).toBe(false);
    expect(document.documentElement.classList.contains('dark')).toBe(false);
    expect(localStorage.getItem('theme-preference')).toBe('light');
  });

  it('respects prefers-color-scheme when nothing is stored yet', () => {
    stubMatchMedia(true);
    const service = TestBed.inject(ThemeService);

    expect(service.isDark()).toBe(true);
    expect(document.documentElement.classList.contains('dark')).toBe(true);
  });

  it('a stored preference overrides prefers-color-scheme', () => {
    localStorage.setItem('theme-preference', 'light');
    stubMatchMedia(true);
    const service = TestBed.inject(ThemeService);

    expect(service.isDark()).toBe(false);
  });
});
