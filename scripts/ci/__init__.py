"""Pure helpers used by the platform .uild and deployment gates.

Catalog symbols are loaded lazily so lightweight tools such as
``verify_supply_chain.py --help`` do not import the YAML parser unnecessarily.
"""

__all__ = ["CatalogError", "Deployable", "load_catalog", "validate_catalog"]


def __getattr__(name: str):
    if name in __all__:
        from .catalog import CatalogError, Deployable, load_catalog, validate_catalog

        return {
            "CatalogError": CatalogError,
            "Deployable": Deployable,
            "load_catalog": load_catalog,
            "validate_catalog": validate_catalog,
        }[name]
    raise AttributeError(name)
