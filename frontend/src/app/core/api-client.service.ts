import { HttpClient, HttpContext } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

/**
 * Base HTTP wrapper. Every call carries `withCredentials: true` so the
 * session cookie travels — the frontend never reads the cookie itself, it
 * only needs the browser to keep sending it (`AUTH-045`).
 */
@Injectable({ providedIn: 'root' })
export class ApiClient {
  private readonly http = inject(HttpClient);

  get<T>(path: string, params?: Record<string, string>, context?: HttpContext): Observable<T> {
    return this.http.get<T>(this.url(path), { withCredentials: true, params, context });
  }

  post<T>(path: string, body: unknown, context?: HttpContext): Observable<T> {
    return this.http.post<T>(this.url(path), body, { withCredentials: true, context });
  }

  patch<T>(path: string, body: unknown): Observable<T> {
    return this.http.patch<T>(this.url(path), body, { withCredentials: true });
  }

  delete<T>(path: string): Observable<T> {
    return this.http.delete<T>(this.url(path), { withCredentials: true });
  }

  postForm<T>(path: string, body: FormData): Observable<T> {
    return this.http.post<T>(this.url(path), body, { withCredentials: true });
  }

  private url(path: string): string {
    return `/api${path}`;
  }
}
