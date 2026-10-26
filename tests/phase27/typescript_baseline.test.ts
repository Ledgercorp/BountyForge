import test from 'node:test';
import assert from 'node:assert/strict';
import { releaseReservation } from '../../fixtures/phase27/typescript/reservation_buggy.ts';

test('owned TypeScript baseline reproduces release of an expired reservation', () => {
  const inventory = { available: 10 };
  const reservation = { state: 'expired' as const, units: 3 };
  assert.equal(releaseReservation(reservation, inventory), 13);
  assert.equal(reservation.state, 'released');
});

test('owned TypeScript baseline releases held units once', () => {
  const inventory = { available: 10 };
  const reservation = { state: 'held' as const, units: 3 };
  assert.equal(releaseReservation(reservation, inventory), 13);
  assert.equal(releaseReservation(reservation, inventory), 13);
});
