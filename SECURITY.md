# Security policy

## Supported version

Security fixes target the latest tagged release and `main`.

## Report a vulnerability

Please use GitHub's private vulnerability reporting for this repository. Do not open a public
issue with exploit details or credentials.

RepoMind does not need provider keys. Never include secrets, private repository source, or
sensitive filesystem paths in a report. The public API accepts only server-configured catalog
ids; treating a request value as a filesystem path is a security bug.
