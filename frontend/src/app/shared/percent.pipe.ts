import { Pipe, PipeTransform } from '@angular/core';

/**
 * Formats a wire rate or ratio string — `"0.0400"` — as a percentage for
 * display, e.g. `4,00 %`. The percent sign belongs to display only; the wire
 * value stays a four-decimal fraction in both directions (`API-005`,
 * `VAL-019`).
 */
@Pipe({ name: 'percent' })
export class PercentPipe implements PipeTransform {
  private readonly formatter = new Intl.NumberFormat('nl-BE', {
    style: 'percent',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

  transform(value: string | null | undefined): string {
    if (value === null || value === undefined || value === '') {
      return '';
    }
    return this.formatter.format(Number(value));
  }
}
