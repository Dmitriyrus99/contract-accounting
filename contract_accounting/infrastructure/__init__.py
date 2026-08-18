"""Infrastructure adapters for the Contract Accounting application."""

from contract_accounting.infrastructure.frappe_lifecycle import (
	FrappeLifecycleUnitOfWork,
)

__all__ = ["FrappeLifecycleUnitOfWork"]
