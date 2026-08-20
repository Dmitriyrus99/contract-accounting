# Security policy

## Supported versions

The project is in pre-release development. Only the current default branch and
explicit release-candidate branches receive security fixes. No version is
approved for production PII until the separate privacy, human-UAT, deployment,
backup/restore, and production-data gates are closed.

## Reporting a vulnerability

Use the repository's private GitHub Security Advisory flow. Do not open a
public issue containing credentials, personal data, exploit details, database
dumps, or site configuration.

Include the affected commit SHA, surface (DocType/API/report/export/File/job),
role and own/foreign project context, minimal synthetic reproduction, and the
expected fail-closed result. Never attach real customer or personnel data.

Security reports are evidence, not automatic release approval. A fix requires
negative regression tests and qualification at the appropriate static, Bench,
browser, and operational gates.
