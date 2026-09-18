(() => {
  const params = new URLSearchParams(location.search);
  const explicit = params.get('api') || '';
  const onPages = location.hostname.endsWith('github.io');
  window.YING_CONFIG = {
    apiBase: explicit || (onPages ? '' : location.origin),
    preferBackend: true,
    requireBackend: !onPages || Boolean(explicit),
    pagesPreview: onPages && !explicit,
  };
})();
