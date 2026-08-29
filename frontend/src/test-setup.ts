// jsdom has no matchMedia implementation at all (real browsers always do).
// ThemeService (core/theme) reads it on construction, so anything rendering
// the header needs this default in place; theme.service.spec.ts overrides
// it per test with a more specific stub where the value actually matters.
if (typeof window.matchMedia !== 'function') {
  window.matchMedia = (query: string): MediaQueryList =>
    ({
      matches: false,
      media: query,
      onchange: null,
      addListener: () => undefined,
      removeListener: () => undefined,
      addEventListener: () => undefined,
      removeEventListener: () => undefined,
      dispatchEvent: () => false,
    }) as MediaQueryList;
}
