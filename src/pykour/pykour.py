from pykour.app import ASGIApp
from pykour.callable import AppCallable
from pykour.config import Config
from pykour.package_loader import load_package


class Pykour(AppCallable):

    def __init__(self) -> None:
        super().__init__()

        self.app = ASGIApp()
        self._config = Config()

    @property
    def config(self):
        return self._config

    def use(self, package_name: str):
        load_package(package_name)
