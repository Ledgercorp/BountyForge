import test from 'node:test';
import assert from 'node:assert/strict';
import { retryDelayMs } from '../../fixtures/phase27/javascript/retry_delay_buggy.mjs';

test('owned JavaScript baseline reproduces zero-second fallback defect', () => {
  assert.equal(retryDelayMs('0', 1000, 0), 1000);
});

test('owned JavaScript baseline handles positive seconds and HTTP dates', () => {
  assert.equal(retryDelayMs('5', 1000, 0), 5000);
  assert.equal(retryDelayMs('1970-01-01T00:00:05.000Z', 1000, 0), 5000);
});
