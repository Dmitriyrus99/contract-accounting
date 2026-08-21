"""Fail-closed, local-site-only demo/UAT dataset tooling.

The public Bench entrypoints live in :mod:`installer`, :mod:`verifier`, and
:mod:`reset`.  Importing this package is deliberately Frappe-free so the
manifest contract can be tested without a Bench runtime.
"""

from contract_accounting.demo_uat.manifest import load_manifest

__all__ = ["load_manifest"]
