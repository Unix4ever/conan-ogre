from conans import ConanFile
import os
import fnmatch
import glob
from conans.tools import cpu_count, get, patch, replace_in_file, SystemPackageTool
from conans import CMake


def apply_patches(source, dest):
    for root, dirnames, filenames in os.walk(source):
        for filename in fnmatch.filter(filenames, '*.patch'):
            patch_file = os.path.join(root, filename)
            dest_path = os.path.join(dest, os.path.relpath(root, source))
            patch(base_path=dest_path, patch_file=patch_file)


def rename(pattern, name):
    for extracted in glob.glob(pattern):
        os.rename(extracted, name)


class OgreConan(ConanFile):
    name = "OGRE"
    version = "1.9.0"
    description = "Open Source 3D Graphics Engine"
    folder = 'ogre-v1.9'
    install_path = os.path.join('_build', folder, 'sdk')
    generators = "cmake"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "use_boost": [True, False],
    }
    default_options = "shared=True", "use_boost=True", "freetype:shared=False"
    exports = ["CMakeLists.txt", 'patches*']
    requires = (
        "freeimage/3.17.0@hilborn/stable",
        "freetype/2.6.3@hilborn/stable",
        "SDL2/2.0.5@lasote/stable",
        "OIS/1.3@hilborn/stable",
        "RapidJSON/1.0.2@inexorgame/stable",
        "zlib/1.2.8@lasote/stable",
        "Cg/3.1@hilborn/stable",

        "libpng/1.6.23@lasote/stable", "bzip2/1.0.6@lasote/stable"  # From freetype
    )
    url = "http://github.com/sixten-hilborn/conan-ogre"
    license = "https://opensource.org/licenses/mit-license.php"

    def requirements(self):
        if self.options.use_boost:
            if self.settings.compiler != "Visual Studio":
                self.options["Boost"].fPIC = True
            self.requires("Boost/1.60.0@lasote/stable")

    def system_requirements(self):
        if self.settings.os == 'Linux':
            installer = SystemPackageTool()
            if self.settings.arch == 'x86':
                installer.install("libxmu-dev:i386")
                installer.install("libxaw7-dev:i386")
                installer.install("libxt-dev:i386")
                installer.install("libxrandr-dev:i386")
            elif self.settings.arch == 'x86_64':
                installer.install("libxmu-dev:amd64")
                installer.install("libxaw7-dev:amd64")
                installer.install("libxt-dev:amd64")
                installer.install("libxrandr-dev:amd64")

    def source(self):
        get("https://bitbucket.org/sinbad/ogre/get/v1-9.zip")
        rename('sinbad-ogre*', self.folder)
        apply_patches('patches', self.folder)
        replace_in_file(
            '{0}/Components/Overlay/CMakeLists.txt'.format(self.folder),
            'target_link_libraries(OgreOverlay OgreMain ${FREETYPE_LIBRARIES})',
            'target_link_libraries(OgreOverlay OgreMain ${FREETYPE_LIBRARIES} ${CONAN_LIBS_BZIP2} ${CONAN_LIBS_LIBPNG} ${CONAN_LIBS_ZLIB})')

    def build(self):
        cmake = CMake(self.settings)
        options = {
            'OGRE_BUILD_SAMPLES': False,
            'OGRE_BUILD_TESTS': False,
            'OGRE_BUILD_TOOLS': False,
            'OGRE_INSTALL_PDB': False,
            'OGRE_USE_BOOST': self.options.use_boost,
            'CMAKE_INSTALL_PREFIX:': os.path.join(os.getcwd(), self.install_path)
        }
        cmake.configure(self, defs=options, build_dir='_build')

        build_args = ['--']
        if self.settings.compiler == 'gcc':
            build_args.append('-- -j{0}'.format(cpu_count()))
        cmake.build(self, target='install', args=build_args)

    def package(self):
        sdk_dir = self.install_path
        include_dir = os.path.join(sdk_dir, 'include', 'OGRE')
        lib_dir = os.path.join(sdk_dir, 'lib')
        bin_dir = os.path.join(sdk_dir, 'bin')
        self.copy(pattern="*.h", dst="include/OGRE", src=include_dir)
        self.copy("*.lib", dst="lib", src=lib_dir, keep_path=False)
        self.copy("*.a", dst="lib", src=lib_dir, keep_path=False)
        self.copy("*.so*", dst="lib", src=lib_dir, keep_path=False, links=True)
        self.copy("*.dll", dst="bin", src=bin_dir, keep_path=False)

    def package_info(self):
        self.cpp_info.libs = [
            'OgreMain',
            'OgreOverlay',
            'OgrePaging',
            'OgreProperty',
            'OgreRTShaderSystem',
            'OgreTerrain'
        ]

        if self.settings.os == "Windows":
            if self.settings.build_type == "Debug" and self.settings.compiler == "Visual Studio":
                self.cpp_info.libs = [lib+'_d' for lib in self.cpp_info.libs]

    def run_and_print(self, command):
        self.output.warn(command)
        self.run(command)
