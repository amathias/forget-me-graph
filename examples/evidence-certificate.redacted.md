# Forget-Me-Graph Evidence Certificate — Redacted Example

> Example only. This file is not a runtime receipt and is not presented as live evidence.

- Request: `example-request-001`
- Subject token: `<redacted-protected-token>`
- Result: **verified_with_limitations**
- Plan hash: `<redacted-plan-sha256>`
- Certificate hash: `<redacted-certificate-sha256>`

| Artifact class | Action | Before | After | Status | Limitation |
|---|---|---:|---:|---|---|
| Raw datasets | row purge | present | absent | verified | |
| Derived dataset | rebuild | present | absent | verified | |
| Vector index | delete and re-index | present | absent | verified | |
| Cache | evict | present | absent | verified | |
| Export | replace | present | absent | verified | |
| Training snapshot | rebuild | present | absent | verified | |
| Toy model | clean-snapshot retrain | active old manifest | active clean manifest | verified | This is not mathematical proof of forgetting. |
| Subject-unaddressable aggregate | exempt | not addressable | not addressable | exempt | No subject key exists in the aggregate. |

The final status includes limitations because the aggregate is explicitly exempt. Runtime
certificates use exact per-artifact counts, receipt IDs, hashes, and independently queried results.
