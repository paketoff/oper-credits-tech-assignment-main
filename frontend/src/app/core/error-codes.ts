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
