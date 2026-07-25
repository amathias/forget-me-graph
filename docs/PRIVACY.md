# Privacy Boundary

Forget-Me-Graph uses synthetic data only.

- Raw selector values are accepted at the request boundary.
- A deterministic HMAC token is used in logs, plans, events, screenshots, and evidence.
- The raw selector is encrypted when persisted for resumable execution.
- Only execution and verification adapters may decrypt the selector.
- LLM or narration adapters may receive URNs, schemas, counts, policies, gaps, and
  selector tokens, but never raw subject records or selector values.
- Tests treat raw values appearing beyond the intake/adapter boundary as failures.

This is a demo privacy architecture, not a claim of production legal compliance.

