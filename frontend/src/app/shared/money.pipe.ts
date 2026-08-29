import { Pipe, PipeTransform } from '@angular/core';

/**
 * Formats a wire money string for **display only** — `nl-BE` locale, the
 * Belgian `300.000,50` shape (`VAL-014`). The value entering this pipe is a
 * string and the value leaving it is a string; nothing here ever holds the
 * amount as a `number` in between, because a JSON float is how `0.1 + 0.2`
 * happens (`CQ-014`, `VAL-018`).
 */
@Pipe({ name: 'money' })
export class MoneyPipe implements PipeTransform {
  private readonly formatter = new Intl.NumberFormat('nl-BE', {
    style: 'currency',
    currency: 'EUR',
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
