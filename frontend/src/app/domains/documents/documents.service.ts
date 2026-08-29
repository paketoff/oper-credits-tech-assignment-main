import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiClient } from '../../core/api-client.service';
import { Checklist, DeleteResult, DocumentType, UploadedDocument } from './documents.models';

/**
 * HTTP for the documents domain (`ARC-020`). The checklist is computed on
 * read (`API-047`); upload and delete each return the application's current
 * status in the same response so the caller never needs a second request
 * (`API-049`, `API-055`).
 */
@Injectable({ providedIn: 'root' })
export class DocumentsService {
  private readonly api = inject(ApiClient);

  checklist(applicationId: string): Observable<Checklist> {
    return this.api.get<Checklist>(`/applications/${applicationId}/checklist`);
  }

  upload(applicationId: string, docType: DocumentType, file: File): Observable<UploadedDocument> {
    const body = new FormData();
    body.append('doc_type', docType);
    body.append('file', file);
    return this.api.postForm<UploadedDocument>(`/applications/${applicationId}/documents`, body);
  }

  delete(applicationId: string, documentId: string): Observable<DeleteResult> {
    return this.api.delete<DeleteResult>(`/applications/${applicationId}/documents/${documentId}`);
  }
}
