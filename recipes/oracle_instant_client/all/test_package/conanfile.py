import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def build_requirements(self):
        self.tool_requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        self.run("sqlplus --version", env="conanbuild")
