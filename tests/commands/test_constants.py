"""Unit tests for todopro_cli.constants package.

Covers:
  - constants/__init__.py  (re-exports OutputType)
  - constants/output_enums.py  (OutputType StrEnum)
"""

import pytest


class TestOutputTypeEnum:
    """Tests for OutputType StrEnum defined in constants/output_enums.py."""

    def test_import_from_output_enums(self):
        from todopro_cli.constants.output_enums import OutputType

        assert OutputType is not None

    def test_import_from_constants_package(self):
        from todopro_cli.constants import OutputType

        assert OutputType is not None

    def test_json_value(self):
        from todopro_cli.constants import OutputType

        assert OutputType.JSON == "json"
        assert str(OutputType.JSON) == "json"

    def test_default_value(self):
        from todopro_cli.constants import OutputType

        assert OutputType.DEFAULT == "default"
        assert str(OutputType.DEFAULT) == "default"

    def test_is_str_enum(self):
        """OutputType values should be usable as plain strings."""
        from todopro_cli.constants import OutputType

        assert isinstance(OutputType.JSON, str)
        assert isinstance(OutputType.DEFAULT, str)

    def test_all_members(self):
        from todopro_cli.constants import OutputType

        members = list(OutputType)
        assert OutputType.JSON in members
        assert OutputType.DEFAULT in members

    def test_equality_with_string(self):
        from todopro_cli.constants import OutputType

        assert OutputType.JSON == "json"
        assert OutputType.DEFAULT == "default"

    def test_constants_package_exports_all(self):
        """Ensure __all__ is properly defined in the package."""
        import todopro_cli.constants as constants_pkg

        assert hasattr(constants_pkg, "OutputType")
        assert "OutputType" in constants_pkg.__all__

    def test_output_type_from_string(self):
        from todopro_cli.constants import OutputType

        assert OutputType("json") is OutputType.JSON
        assert OutputType("default") is OutputType.DEFAULT

    def test_invalid_output_type_raises(self):
        from todopro_cli.constants import OutputType

        with pytest.raises(ValueError):
            OutputType("invalid_value")
