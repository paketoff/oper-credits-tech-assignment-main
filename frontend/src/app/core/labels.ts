import { EmploymentType, PropertyType, Region } from './models';

/**
 * How the value types in `models.ts` are written for a person to read.
 *
 * One definition each, in `core/` beside the types they label. There were
 * three copies of the region names — the simulator's form, the wizard's
 * property step, and nothing at all on the review screen, which rendered the
 * raw `FLANDERS` and `EMPLOYEE` on the last page before submission. The same
 * failure `STATUS_CHIPS` was extracted to prevent (T63).
 *
 * `core/` and not `shared/`: `shared/` carries no domain vocabulary
 * (`ARC-025`), and these are the wire's enums.
 */

/** One choice in a `p-select`. */
export interface LabelledOption<T> {
  label: string;
  value: T;
}

export const REGION_LABELS: Record<Region, string> = {
  FLANDERS: 'Flanders',
  WALLONIA: 'Wallonia',
  BRUSSELS: 'Brussels',
};

export const EMPLOYMENT_LABELS: Record<EmploymentType, string> = {
  EMPLOYEE: 'Employee',
  SELF_EMPLOYED: 'Self-employed',
  OTHER: 'Other',
};

export const PROPERTY_TYPE_LABELS: Record<PropertyType, string> = {
  EXISTING: 'Existing',
  NEW_BUILD: 'New build',
};

/** Turn a label map into the option list a `p-select` takes. */
export function optionsOf<T extends string>(labels: Record<T, string>): LabelledOption<T>[] {
  return (Object.keys(labels) as T[]).map((value) => ({ label: labels[value], value }));
}
