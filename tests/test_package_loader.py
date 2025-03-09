from unittest import mock

import pytest

from pykour.package_loader import load_package


@pytest.mark.parametrize(
    "package_name, expected_modules",
    [
        ("routes", ["routes.user_router", "routes.order_router"]),
    ],
)
def test_load_package(package_name, expected_modules):

    with (
        mock.patch("importlib.import_module") as mock_import_module,
        mock.patch("pkgutil.walk_packages") as mock_walk_packages,
    ):

        mock_module = mock.Mock()
        mock_module.__file__ = f"/fake/path/{package_name}/__init__.py"
        mock_import_module.return_value = mock_module

        mock_walk_packages.return_value = [
            (None, module_name.split(".")[-1], False) for module_name in expected_modules
        ]

        load_package(package_name)

        calls = [mock.call(module_name) for module_name in expected_modules]
        mock_import_module.assert_has_calls(calls, any_order=True)
