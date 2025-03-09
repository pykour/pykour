import importlib
import os
import pkgutil


def load_package(package_name: str):

    package = importlib.import_module(package_name)
    package_path = os.path.dirname(package.__file__)

    for finder, module_name, is_pkg in pkgutil.walk_packages([package_path]):
        full_module_name = f"{package_name}.{module_name}"

        importlib.import_module(full_module_name)

        if is_pkg:
            load_package(full_module_name)
