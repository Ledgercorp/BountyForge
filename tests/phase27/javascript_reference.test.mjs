import test from 'node:test';
import assert from 'node:assert/strict';
import { retryDelayMs } from '../../fixtures/phase27/javascript/retry_delay_reference.mjs';

test('owned JavaScript reference preserves a valid zero-second delay', () => {
  assert.equal(retryDelayMs('0', 1000, 0), 0);
});

test('owned JavaScript reference handles positive seconds, dates, and invalid input', () => {
  assert.equal(retryDelayMs('5', 1000, 0), 5000);
  assert.equal(retryDelayMs('1970-01-01T00:00:05.000Z', 1000, 0), 5000);
  assert.equal(retryDelayMs('not a date', 1000, 0), 1000);
  assert.equal(retryDelayMs('-1', 1000, 0), 1000);
});
