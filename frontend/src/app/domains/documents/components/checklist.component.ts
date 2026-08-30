import { ChangeDetectionStrategy, Component, computed, input, output } from '@angular/core';

import { Checklist, DocumentType } from '../documents.models';
import { UploadFieldComponent, UploadStatus } from './upload-field.component';

/** Per-row transient upload state, keyed by `doc_type` (`UX-040`, `UX-041`). */
export interface RowStatus {
  status: UploadStatus;
  errorMessage: string | null;
}

export interface FileSelection {
  docType: DocumentType;
  file: File;
}

export interface DocumentRemoval {
  docType: DocumentType;
  documentId: string;
}

/**
 * The whole checklist (`UX-039`'s progress count, then one row per
 * requirement). Dumb (`ARC-022`) — the host page owns the `DocumentsService`
 * calls and feeds row state back in.
 */
@Component({
  selector: 'app-checklist',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [UploadFieldComponent],
  templateUrl: './checklist.component.html',
})
export class ChecklistComponent {
  readonly checklist = input.required<Checklist>();
  readonly rowStatus = input<Record<string, RowStatus>>({});

  readonly fileSelected = output<FileSelection>();
  readonly documentRemoved = output<DocumentRemoval>();

  /**
   * One segment per required document, filled up to the satisfied count
   * (`UX-039`). `aria-hidden` in the template: the count beside it already
   * says the same thing in words, and two readings of one fact is noise to a
   * screen reader.
   */
  protected readonly progressSegments = computed(() => {
    const { required_count: required, satisfied_count: satisfied } = this.checklist();
    return Array.from({ length: required }, (_, index) => index < satisfied);
  });

  protected statusFor(docType: DocumentType): UploadStatus {
    return this.rowStatus()[docType]?.status ?? 'idle';
  }

  protected errorFor(docType: DocumentType): string | null {
    return this.rowStatus()[docType]?.errorMessage ?? null;
  }
}
