/**
 * Utility to hide Clerk branding badge
 * 
 * NOTE: This is for development purposes only.
 * 
 * This utility targets footer elements and clerk.com links to hide the badge
 * during development for a cleaner UI experience.
 */
export function hideClerkBadge() {
  const hideElements = () => {
    // Hide footer elements
    const footerSelectors = ['.cl-footer', '.cl-modalFooter', '.cl-userButtonPopoverFooter'];
    footerSelectors.forEach(selector => {
      document.querySelectorAll(selector).forEach((el: Element) => {
        if (el instanceof HTMLElement) {
          el.style.display = 'none';
        }
      });
    });

    // Hide clerk.com badge links
    document.querySelectorAll('a[href*="clerk.com"]').forEach((link: Element) => {
      if (link instanceof HTMLElement && link.parentElement) {
        const parent = link.parentElement;
        if (parent.offsetHeight < 50) {
          parent.style.display = 'none';
        }
      }
    });
  };

  // Run on load and periodically
  hideElements();
  setTimeout(hideElements, 500);
  setTimeout(hideElements, 1000);

  // Watch for DOM changes (when modals open)
  const observer = new MutationObserver(hideElements);
  observer.observe(document.body, { childList: true, subtree: true });

  return () => observer.disconnect();
}
