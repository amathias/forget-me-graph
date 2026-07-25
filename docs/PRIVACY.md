# Privacy Boundary

Forget-Me-Graph is a synthetic-data demonstration. It must not process real personal information.

## Data flow

| Boundary | Raw synthetic selector | Protected token | Subject records |
|---|---:|---:|---:|
| Browser request form | In memory until planning/execution | Displayed after planning | Never loaded |
| Plan endpoint | Accepted in request body | Returned and plan-bound | Never loaded |
| Deterministic planner | Protected immediately | Used in every decision | Never loaded |
| Artifact adapters | Decrypted only to perform exact fixture queries | Used for token-keyed stores | Read only from the disposable fixture |
| Certificate and receipts | Omitted | Persisted | Omitted |
| DataHub MCP/SDK | Omitted | Omitted from MCP; only hashes/status written | Omitted |
| External LLM | Omitted | Omitted | Omitted |

No LLM is used in the executable workflow. Planning, action selection, execution ordering,
verification, and certificate aggregation are deterministic application code.

## Implemented controls

- Intake selector fields are `repr=False`; Pydantic validation failures return a generic message
  rather than echoing rejected request content.
- The browser clears the visible selector field after planning and retains the value only in the
  current page's memory until approved execution. It never uses local storage, session storage,
  analytics, or console logging.
- `SelectorProtector` creates an HMAC display token and encrypted adapter value. The ciphertext is
  excluded from model serialization and is not written to plans or certificates.
- Plans, decisions, certificates, DataHub custom properties, catalog receipts, and public examples
  contain no raw selector.
- Evidence downloads allow only the certificate and DataHub receipt filenames for a validated
  opaque request ID.
- Runtime evidence stays under the configured fixture/state roots and is excluded from the public
  evidence package.
- UI screenshots and recordings must keep the selector input masked and must not open local fixture
  tables containing the synthetic subject.

## Logging and transport

Application code does not log request bodies or selector values. Standard access logs contain the
method and URL path, not the JSON body. A deployed environment must use HTTPS and must not add
reverse-proxy body logging, browser analytics, request tracing, or error capture that records bodies.

The bundled default selector secret exists only for disposable local/test demonstrations. Any
other environment must provide `FMG_SELECTOR_SECRET` through its secret mechanism, and the value
must contain at least 16 characters. Readiness validates that same minimum contract without
deriving, hashing, persisting, logging, or returning the value; missing or invalid protection fails
closed. An explicitly invalid local/test value also fails rather than silently falling back.
DataHub credentials are supplied out of band and never included in requests, examples, screenshots,
or Git.

## Accurate boundary of the claim

The local fixture necessarily contains synthetic rows so deletion can be demonstrated. The system
minimizes their movement; it does not claim that the fixture contains no subject data. The current
UI has process-local execution coordination and no durable resumable request store. These controls
are a demo privacy architecture, not a certification of legal compliance or production security.
