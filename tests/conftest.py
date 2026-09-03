"""Pytest configuration: install a minimal pyspark.sql.types stub when the
real pyspark package is unavailable (e.g. on CI).

Several unit tests assert on pyspark ``StructType`` / ``StructField`` shape
via ``isinstance`` checks against objects returned by
``src.jobs.lakehouse_spark_lakehouse_job._rows_with_schema``. That function
itself only constructs these type objects; it does not require a live
SparkSession. The full PySpark runtime is exercised separately by the
integration DAGs in the Airflow Docker cluster.

When ``pyspark`` cannot be imported (CI quality-gate job installs only the
test surface from ``requirements.txt``), we install lightweight stand-ins
into ``sys.modules`` so the type-construction code path and the
``isinstance`` checks in tests still work.
"""

from __future__ import annotations

import sys
import types


def _install_pyspark_stub() -> None:
    pyspark = types.ModuleType("pyspark")
    pyspark_sql = types.ModuleType("pyspark.sql")
    pyspark_types = types.ModuleType("pyspark.sql.types")

    class _StubType:
        """Stand-in for pyspark.sql.types.AtomicType subclasses."""

        def __init__(self) -> None:
            pass

        def __repr__(self) -> str:  # pragma: no cover - debug aid only
            return f"<stub {type(self).__name__}>"

    class _StructField:
        def __init__(self, name: str, dataType: object, nullable: bool = True) -> None:
            self.name = name
            self.dataType = dataType
            self.nullable = nullable

        def __repr__(self) -> str:  # pragma: no cover - debug aid only
            return f"StructField({self.name!r}, {self.dataType!r}, nullable={self.nullable})"

    class _StructType:
        def __init__(self, fields: list[_StructField] | None = None) -> None:
            self.fields: list[_StructField] = list(fields or [])

        def __repr__(self) -> str:  # pragma: no cover - debug aid only
            return f"StructType({self.fields!r})"

    # All AtomicType markers share the same class identity for isinstance checks
    BooleanType = type("BooleanType", (_StubType,), {})
    LongType = type("LongType", (_StubType,), {})
    DoubleType = type("DoubleType", (_StubType,), {})
    StringType = type("StringType", (_StubType,), {})

    pyspark_types.StructType = _StructType  # type: ignore[attr-defined]
    pyspark_types.StructField = _StructField  # type: ignore[attr-defined]
    pyspark_types.BooleanType = BooleanType  # type: ignore[attr-defined]
    pyspark_types.LongType = LongType  # type: ignore[attr-defined]
    pyspark_types.DoubleType = DoubleType  # type: ignore[attr-defined]
    pyspark_types.StringType = StringType  # type: ignore[attr-defined]

    sys.modules["pyspark"] = pyspark
    sys.modules["pyspark.sql"] = pyspark_sql
    sys.modules["pyspark.sql.types"] = pyspark_types


try:
    import pyspark.sql.types  # noqa: F401
except ImportError:
    _install_pyspark_stub()
