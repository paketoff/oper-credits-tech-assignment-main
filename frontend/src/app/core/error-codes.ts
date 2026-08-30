import { HttpErrorResponse } from '@angular/common/http';

/**
 * Mirrors `core/errors.py`'s `MESSAGES` keys — the codes only, never the
 * message text (`UX-023`: the message itself always comes from the backend
 * response, never a hardcoded string here). This exists so the frontend can
 * reason about a code before a response arrives, e.g. to decide whether a
 * field-level error can be shown at all.
 */
export type ErrorCode =
  | 'VALIDATION_ERROR'
  | 'LOAN_AMOUNT_NOT_POSITIVE'
  | 'TERM_OUT_OF_RANGE'
  | 'RATE_OUT_OF_RANGE'
  | 'PROPERTY_VALUE_OUT_OF_RANGE'
  | 'JKP_COMPUTATION_FAILED'
  | 'SIMULATION_NOT_FOUND'
  | 'EMAIL_ALREADY_REGISTERED'
  | 'INVALID_CREDENTIALS'
  | 'NOT_AUTHENTICATED'
  | 'TOO_MANY_ATTEMPTS'
  | 'APPLICATION_NOT_FOUND'
  | 'INVALID_STATE_TRANSITION'
  | 'APPLICATION_ALREADY_SUBMITTED'
  | 'UNSUPPORTED_DOCUMENT_TYPE'
  | 'DOCUMENT_TOO_LARGE'
  | 'DOCUMENT_EMPTY'
  | 'DOCUMENT_TYPE_NOT_REQUIRED'
  | 'DOCUMENT_NOT_FOUND'
  | 'UPLOAD_READ_FAILED'
  | 'STORAGE_UNAVAILABLE'
  | 'STORAGE_CORRUPT';

/** The one error shape every /api failure uses (`VAL-006`, `API-013`). */
export interface ApiError {
  code: ErrorCode;
  message: string;
  field: string | null;
}

/**
 * Reads the `{code, message, field}` body out of a failed request, or returns
 * null when the failure was not one of ours (a network drop, a 502 from a
 * proxy, anything with no body).
 *
 * `UX-023`: the caller renders `message` as it arrived. Nothing here composes
 * text — a message the frontend wrote is a message that can disagree with the
 * server about what the rule is.
 */
export function apiErrorOf(failure: unknown): ApiError | null {
  if (!(failure instanceof HttpErrorResponse)) {
    return null;
  }
  const body: unknown = failure.error;
  if (typeof body !== 'object' || body === null) {
    return null;
  }
  const candidate = body as Partial<ApiError>;
  return typeof candidate.code === 'string' && typeof candidate.message === 'string'
    ? { code: candidate.code, message: candidate.message, field: candidate.field ?? null }
    : null;
}
