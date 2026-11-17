# Security and privacy reports

Familiar handles private family data, including data about living people.
A defect that lets such data leave where the host put it is treated as a
security defect, whether or not it looks like a classic vulnerability.

## What to report privately

- Reader export, desk build or print book showing something the family's
  privacy settings, consent records or the living-person rules should have
  withheld.
- A way around the sign-in of a published desk, or a way for a `reader` login
  to reach what only an `owner` may see.
- A command that writes outside the chosen family root, or reads another
  family.
- Secrets printed to output or written outside `.secrets/`.

## How

Use GitHub's private vulnerability reporting on this repository
(**Security → Report a vulnerability**). Do not open a public issue and do
not attach real family data: reproduce on `demo/` or describe the shape of the
data. State the engine version (`familiar --version`).

There is no bounty and no fixed response time; this is a small project in
active development. Reports are read, answered and credited if you wish.
Only the latest tagged release is fixed.
