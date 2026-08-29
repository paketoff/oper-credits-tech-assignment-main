import { Injectable, signal } from '@angular/core';

/** Mirrors `UserResponse` field for field (`ARC-027`). No password, ever. */
export interface User {
  id: string;
  email: string;
  created_at: string;
}

/**
 * Where the auth domain's `AuthService` writes what `GET /api/auth/me`
 * returns (`AUTH-046`), and where the error interceptor clears it on a 401
 * (`AUTH-047`). Lives in `core/` rather than `domains/auth/` because the
 * interceptor is a `core` concern and cannot depend on a domain — the same
 * direction the backend's `ARC-012` draws, applied to the frontend.
 */
@Injectable({ providedIn: 'root' })
export class AuthState {
  private readonly currentUserSignal = signal<User | null>(null);
  private readonly resolvedSignal = signal(false);

  readonly currentUser = this.currentUserSignal.asReadonly();
  /** Whether the initial `/me` call has completed, either way. */
  readonly resolved = this.resolvedSignal.asReadonly();

  set(user: User): void {
    this.currentUserSignal.set(user);
    this.resolvedSignal.set(true);
  }

  clear(): void {
    this.currentUserSignal.set(null);
    this.resolvedSignal.set(true);
  }
}
