import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { SimulationService } from './simulation.service';

const _REQUEST = {
  property_value: '300000.00',
  own_contribution: '30000.00',
  term_months: 300,
  annual_nominal_rate: '0.0400',
  region: 'FLANDERS' as const,
  is_first_home: true,
};

describe('SimulationService', () => {
  let httpMock: HttpTestingController;

  beforeEach(() => {
    sessionStorage.clear();
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    httpMock = TestBed.inject(HttpTestingController);
  });

  it('remembers the simulation id across a reload (DOM-026)', () => {
    const service = TestBed.inject(SimulationService);
    service.simulate(_REQUEST).subscribe();
    httpMock.expectOne('/api/simulations').flush({ id: 'sim-42' });

    expect(service.lastId()).toBe('sim-42');

    // A reload builds a brand new service against the same tab. Held only in a
    // signal, the id was lost here — signup still worked (UX-028) but the draft
    // was unseeded and affordability had nothing to measure (API-075).
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });

    expect(TestBed.inject(SimulationService).lastId()).toBe('sim-42');
  });

  it('forgets the id once it has been claimed (DOM-027)', () => {
    const service = TestBed.inject(SimulationService);
    service.simulate(_REQUEST).subscribe();
    httpMock.expectOne('/api/simulations').flush({ id: 'sim-42' });

    service.forget();

    expect(service.lastId()).toBeNull();
    expect(sessionStorage.getItem('last-simulation-id')).toBeNull();
  });

  it('starts empty in a fresh tab', () => {
    expect(TestBed.inject(SimulationService).lastId()).toBeNull();
  });
});
