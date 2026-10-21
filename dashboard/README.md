# Owner dashboard adapter

These newly authored files update the existing **private BountyForge** Hatchable
project only. They contain no authentication credentials and make only fixed,
read-only public GitHub requests. Existing private dashboard code is not copied
into this public repository.

Deployment mapping:

- `operations-state.mjs` -> `lib/operations-state.js`
- `operator-status.js` -> `api/operator-status.js` (admin-only GET)
- Insert `bounded-status.fragment.html` before the historical Phase 3 snapshot.
- The existing `loadOperations` function fills the panel using the API's
  `operations` object, sets the verified Actions URL with a fixed repository
  regex, and shows `UNAVAILABLE` if the ledger cannot be read. It uses textContent.

The panel distinguishes completed synthetic cycles, active/expired leases,
unverified discoveries, the historical 0/5 score, inactive repair scheduling and
zero commercial approvals/revenue. It does not infer current model health.

Validation: `node --test tests/dashboard_state.mjs`; admin, anonymous and member
route checks; platform deployment validation and deployed status inspection.
Never change project visibility or use dashboard credentials to publish code.
