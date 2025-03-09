from conan import ConanFile
from conan.tools.system import package_manager
from conan.tools.files import get, copy, download, chdir
from conan.errors import ConanInvalidConfiguration
import os

required_conan_version = ">=2.6.0"


class OracleInstantClientConan(ConanFile):
    name = "oracle_instant_client"
    description = "Oracle Instant Client libraries, headers, and utilities"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = (
        "https://www.oracle.com/database/technologies/instant-client/downloads.html"
    )
    topics = ("oracle", "oci", "pre-built")
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def _extract_dmg(self, dmg_path, output_folder):
        mount_point = "/Volumes/mount_dmg"
        self.run(f"hdiutil attach {dmg_path} -mountpoint {mount_point}")
        try:
            os.makedirs(output_folder, exist_ok=True)
            self.run(f"cp -R {mount_point}/* {output_folder}")
            self.output.info(f"cp -R {mount_point}/* {output_folder}")
        except Exception as error:
            self.output.info(f"Error {error}")
        self.run(f"hdiutil detach {mount_point}")

    def _create_symlink(self, lib_folder, lib_file):
        source = None
        lib_file_path = os.path.join(lib_folder, lib_file)

        with open(lib_file_path, "r") as f:
            source = f.read().strip()

        if source:
            source = os.path.join("./", source)
            lib_file = os.path.join("./", lib_file)
            with chdir(self, lib_folder):
                os.unlink(lib_file)
                os.symlink(source, lib_file)

    def system_requirements(self):
        if self.settings.os == "Linux":
            yum = package_manager.Yum(self)
            yum.install(["libaio"], update=True, check=True)

            apt = package_manager.Apt(self)
            apt.install(["libaio1t64"], update=True, check=True)
            if os.path.exists(
                "/usr/lib/x86_64-linux-gnu/libaio.so.1t64"
            ) and not os.path.exists("/usr/lib/x86_64-linux-gnu/libaio.so.1"):
                os.symlink(
                    "/usr/lib/x86_64-linux-gnu/libaio.so.1t64",
                    "/usr/lib/x86_64-linux-gnu/libaio.so.1",
                )

    def layout(self):
        pass

    def package_id(self):
        del self.info.settings.compiler
        del self.info.settings.build_type

    def validate(self):
        pass

    def source(self):
        pass

    def build(self):
        # Extract major version from the full version string (e.g., "23" from "23.7.0.25.01")
        versions = self.version.split(".")
        pattern = f"instantclient_{versions[0]}_{versions[1]}/*"
        os_name = str(self.settings.os).lower()
        # Access the URLs defined in conandata.yml for the current version
        if self.settings.os != "Macos":
            # Basic
            sources = get(
                self,
                **self.conan_data["sources"][self.version][os_name]["basic"],
                strip_root=True,
                keep_permissions=True,
                pattern=pattern,
            )
            # SQLPlus
            sources = get(
                self,
                **self.conan_data["sources"][self.version][os_name]["sqlplus"],
                strip_root=True,
                keep_permissions=True,
                pattern=pattern,
            )
            # SDK
            sources = get(
                self,
                **self.conan_data["sources"][self.version][os_name]["sdk"],
                strip_root=True,
                keep_permissions=True,
                pattern=pattern,
            )
        else:
            # Basic
            sources = download(
                self,
                **self.conan_data["sources"][self.version][os_name]["basic"],
                filename="basic.dmg",
            )
            # SQLPlus
            sources = download(
                self,
                **self.conan_data["sources"][self.version][os_name]["sqlplus"],
                filename="sqlplus.dmg",
            )
            # SDK
            sources = download(
                self,
                **self.conan_data["sources"][self.version][os_name]["sdk"],
                filename="sdk.dmg",
            )
            self._extract_dmg("basic.dmg", self.build_folder)
            self._extract_dmg("sqlplus.dmg", self.build_folder)
            self._extract_dmg("sdk.dmg", self.build_folder)

    def package(self):
        # Folders
        oracle_home = self.build_folder
        sdk_folder_include = os.path.join(oracle_home, "sdk", "include")
        sdk_folder_lib = os.path.join(oracle_home, "sdk", "lib")
        if self.settings.os == "Windows":
            sdk_folder_lib = os.path.join(sdk_folder_lib, "msvc")
        lib_folder = os.path.join(self.package_folder, "lib")
        bin_folder = os.path.join(self.package_folder, "bin")
        include_folder = os.path.join(self.package_folder, "include")

        options = {
            "Unix": {
                oracle_home: {
                    lib_folder: [
                        "*.so*",
                        "*.dylib*",
                        "*.la",
                    ],
                    bin_folder: [
                        "adrci",
                        "genezi",
                        "sqlplus",
                    ],
                },
                sdk_folder_include: {
                    include_folder: ["*.h"],
                },
            },
            "Windows": {
                oracle_home: {
                    bin_folder: [
                        "*.exe",
                        "*.dll",
                    ]
                },
                sdk_folder_include: {include_folder: ["*.h"]},
                sdk_folder_lib: {lib_folder: ["*.lib"]},
            },
        }

        platform_key = "Windows" if self.settings.os == "Windows" else "Unix"
        for base_folder, destinations in options[platform_key].items():
            for dst_folder, patterns in destinations.items():
                for pattern in patterns:
                    copy(
                        self,
                        pattern,
                        src=base_folder,
                        dst=dst_folder,
                        keep_path=True,
                    )

        if platform_key == "Unix":
            self._create_symlink(lib_folder, "libclntsh.so")
            self._create_symlink(lib_folder, "libclntshcore.so")
            self._create_symlink(lib_folder, "libocci.so")

    def package_info(self):
        # Define ORACLE_HOME as the 'oracle_home' folder in the package
        oracle_home = self.package_folder
        self.runenv_info.define("ORACLE_HOME", oracle_home)
        # Set OCI_LIB_DIR to ORACLE_HOME/lib
        self.runenv_info.define("OCI_LIB_DIR", os.path.join(oracle_home, "lib"))
        # Set OCI_INC_DIR to ORACLE_HOME/include
        self.runenv_info.define("OCI_INC_DIR", os.path.join(oracle_home, "include"))
        # Optionally, add the bin directory to PATH
        self.runenv_info.append_path("PATH", os.path.join(oracle_home, "bin"))

        if self.settings.os == "Linux":
            # Append ORACLE_HOME/lib to LD_LIBRARY_PATH
            self.runenv_info.append_path(
                "LD_LIBRARY_PATH", os.path.join(oracle_home, "lib")
            )
