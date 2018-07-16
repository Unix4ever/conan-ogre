from conans.model.conan_file import ConanFile
from conans import CMake
import os


############### CONFIGURE THESE VALUES ##################
default_user = "hilborn"
default_channel = "stable"
#########################################################

channel = os.getenv("CONAN_CHANNEL", default_channel)
username = os.getenv("CONAN_USERNAME", default_user)


class DefaultNameConan(ConanFile):
    name = "DefaultName"
    version = "0.1"
    settings = "os", "compiler", "arch", "build_type"
    generators = "cmake"
    requires = "OGRE/2.1.0@%s/%s" % (username, channel)
    options = {
        "shared": [True, False],
    }

    default_options = (
        "shared=True"
    )

    def configure(self):
        self.options["OGRE"].shared = self.options.shared

    def build(self):
        cmake = CMake(self)
        options = {
            'CMAKE_CXX_STANDARD': 11,
        }

        cmake.configure(defs=options, build_dir=self.conanfile_directory)
        cmake.build(target='build')

    def imports(self):
        self.copy(pattern="*.dll", dst="bin", src="bin")
        self.copy(pattern="*.dylib", dst="bin", src="lib")
        
    def test(self):
        self.run("cd bin && .%sexample" % (os.sep))
