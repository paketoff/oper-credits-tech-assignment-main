import { ChangeDetectionStrategy, Component, input, output, viewChild } from '@angular/core';
import { FileUpload, FileUploadHandlerEvent } from 'primeng/fileupload';

import {
  ACCEPTED_DOCUMENT_TYPES,
  ChecklistItem,
  MAX_DOCUMENT_SIZE_BYTES,
} from '../documents.models';

export type UploadStatus = 'idle' | 'uploading' | 'error';

/**
 * One requirement row (`UX-036`): its own `p-fileupload`, never a shared
 * dropzone. Dumb (`ARC-022`) — the actual HTTP call lives in whichever page
 * hosts the checklist; this component only reports what the borrower did.
 */
@Component({
  selector: 'app-upload-field',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FileUpload],
  templateUrl: './upload-field.component.html',
})
export class UploadFieldComponent {
  readonly item = input.required<ChecklistItem>();
  readonly status = input<UploadStatus>('idle');
  readonly errorMessage = input<string | null>(null);

  readonly fileSelected = output<File>();
  readonly documentRemoved = output<string>();

  protected readonly acceptedTypes = ACCEPTED_DOCUMENT_TYPES;
  protected readonly maxSizeBytes = MAX_DOCUMENT_SIZE_BYTES;

  private readonly fileUpload = viewChild<FileUpload>('upload');

  protected onUploadHandler(event: FileUploadHandlerEvent): void {
    const [file] = event.files;
    if (file) {
      this.fileSelected.emit(file);
    }
    this.fileUpload()?.clear();
  }
}
