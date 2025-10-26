const currencyFormatter = new Intl.NumberFormat(undefined, {
  style: 'currency',
  currency: 'USD',
  minimumFractionDigits: 4,
  maximumFractionDigits: 4,
});

const shortCurrencyFormatter = new Intl.NumberFormat(undefined, {
  style: 'currency',
  currency: 'USD',
  minimumFractionDigits: 3,
  maximumFractionDigits: 3,
});

const numberFormatter = new Intl.NumberFormat(undefined, {
  minimumFractionDigits: 0,
  maximumFractionDigits: 0,
});

export function formatCurrency(value: number | null | undefined, { compact = false } = {}): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return '—';
  }
  return compact ? shortCurrencyFormatter.format(value) : currencyFormatter.format(value);
}

export function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return '—';
  }
  return numberFormatter.format(value);
}

export function formatTimestamp(value: string | null | undefined): string {
  if (!value) {
    return '—';
  }
  try {
    const date = new Date(value);
    return `${date.toLocaleString()} (${date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })})`;
  } catch {
    return value;
  }
}

export function formatRelativeTime(value: string | null | undefined): string {
  if (!value) {
    return '—';
  }

  try {
    const date = new Date(value).getTime();
    const now = Date.now();
    const diff = now - date;

    const minute = 60 * 1000;
    const hour = 60 * minute;
    const day = 24 * hour;

    if (diff < minute) {
      return 'just now';
    }
    if (diff < hour) {
      const minutes = Math.floor(diff / minute);
      return `${minutes} min ago`;
    }
    if (diff < day) {
      const hours = Math.floor(diff / hour);
      return `${hours}h ago`;
    }
    const days = Math.floor(diff / day);
    return `${days}d ago`;
  } catch {
    return value;
  }
}
