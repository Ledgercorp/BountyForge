import test from 'node:test';
import assert from 'node:assert/strict';
import { releaseReservation } from '../../fixtures/phase27/typescript/reservation_reference.ts';

test('owned TypeScript reference does not release expired reservation units', () => {
  const inventory = { available: 10 };
  const reservation = { state: 'expired' as const, units: 3 };
  assert.equal(releaseReservation(reservation, inventory), 10);
  assert.equal(reservation.state, 'expired');
});

test('owned TypeScript reference releases held units once', () => {
  const inventory = { available: 10 };
  const reservation = { state: 'held' as const, units: 3 };
  assert.equal(releaseReservation(reservation, inventory), 13);
  assert.equal(reservation.state, 'released');
  assert.equal(releaseReservation(reservation, inventory), 13);
});
