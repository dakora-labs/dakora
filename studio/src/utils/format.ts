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

function normaliseUtcString(value: string): string {
  const trimmed = value.trim();
  if (trimmed === '') {
    return trimmed;
  }

  // If the string already contains a timezone offset or Z, return as-is
  if (/[Zz]$/.test(trimmed) || /[+-]\d{2}:\d{2}$/.test(trimmed)) {
    return trimmed;
  }

  // Append Z to treat the timestamp as UTC
  return `${trimmed}Z`;
}

export function parseApiDate(value: string | null | undefined): Date | null {
  if (!value) {
    return null;
  }

  const normalised = normaliseUtcString(value);
  const date = new Date(normalised);
  if (Number.isNaN(date.getTime())) {
    return null;
  }
  return date;
}

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
  const date = parseApiDate(value);
  if (!date) {
    return '—';
  }

  return `${date.toLocaleString()} (${date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })})`;
}

export function formatRelativeTime(value: string | null | undefined): string {
  const date = parseApiDate(value);
  if (!date) {
    return '—';
  }

  const timestamp = date.getTime();
  const now = Date.now();
  const diff = now - timestamp;

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
}
