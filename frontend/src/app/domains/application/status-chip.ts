import { ApplicationStatus } from '../../core/models';

/** One status, as the borrower reads it (`UI-053`). */
export interface StatusChip {
  label: string;
  classes: string;
}

/**
 * The `UI-053` palette, defined once (T63).
 *
 * Both the applications list and the application page render this, and a
 * second copy would drift the first time a status was added or a colour
 * changed — the list would say one thing and the detail page another about
 * the same application.
 */
export const STATUS_CHIPS: Record<ApplicationStatus, StatusChip> = {
  DRAFT: { label: 'Draft', classes: 'bg-surface-3 text-muted' },
  SUBMITTED: { label: 'Submitted', classes: 'bg-signal-soft text-ink-fixed' },
  DOCUMENTS_PENDING: { label: 'Documents pending', classes: 'bg-signal-soft text-ink-fixed' },
  DOCUMENTS_COMPLETE: { label: 'Documents complete', classes: 'bg-success-soft text-success' },
  UNDER_REVIEW: { label: 'Under review', classes: 'bg-signal-soft text-ink-fixed' },
  OFFER_ISSUED: { label: 'Offer issued', classes: 'bg-success-soft text-success' },
  WITHDRAWN: { label: 'Withdrawn', classes: 'bg-danger-soft text-danger-fixed' },
};
