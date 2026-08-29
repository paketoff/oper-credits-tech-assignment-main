import { ApplicationStatus } from '../../core/models';

/** Mirrors `core/enums.py`'s `DocumentType`, eleven members (`ARC-044`). */
export type DocumentType =
  | 'IDENTITY'
  | 'BANK_STATEMENTS'
  | 'PURCHASE_AGREEMENT'
  | 'PAYSLIPS'
  | 'EMPLOYER_STATEMENT'
  | 'TAX_ASSESSMENT'
  | 'ACCOUNTANT_STATEMENT'
  | 'EXISTING_LOAN_STATEMENTS'
  | 'EPC'
  | 'BUILDING_PERMIT'
  | 'CONSTRUCTION_QUOTE';

/** Accepted content types and size limit, stated before the picker opens (`UX-042`, `DOC-001`, `DOC-002`). */
export const ACCEPTED_DOCUMENT_TYPES = 'application/pdf,image/jpeg,image/png';
export const MAX_DOCUMENT_SIZE_BYTES = 10 * 1024 * 1024;

/** Mirrors `DocumentSummary` field for field (`API-045`). */
export interface DocumentSummary {
  id: string;
  filename: string;
  size_bytes: number;
  uploaded_at: string;
}

/** Mirrors `ChecklistItem` field for field (`API-045`, `API-046`). */
export interface ChecklistItem {
  doc_type: DocumentType;
  label_en: string;
  label_nl: string;
  required: boolean;
  satisfied: boolean;
  reason: string | null;
  documents: DocumentSummary[];
}

/** Mirrors `ChecklistResponse` field for field (`API-045`, `API-047`). */
export interface Checklist {
  required_count: number;
  satisfied_count: number;
  items: ChecklistItem[];
}

/** Mirrors `DocumentResponse` field for field (`API-048`, `API-049`). */
export interface UploadedDocument {
  id: string;
  doc_type: DocumentType;
  filename: string;
  content_type: string;
  size_bytes: number;
  uploaded_at: string;
  application_status: ApplicationStatus;
}

/** Mirrors `DocumentDeleteResponse` field for field (`API-055`). */
export interface DeleteResult {
  application_status: ApplicationStatus;
}
