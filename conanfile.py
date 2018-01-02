from conans import ConanFile
import os
import fnmatch
import glob
from conans.tools import get, patch, SystemPackageTool
from conans import CMake


def apply_patches(source, dest):
    for root, _dirnames, filenames in os.walk(source):
        for filename in fnmatch.filter(filenames, '*.patch'):
            patch_file = os.path.join(root, filename)
            dest_path = os.path.join(dest, os.path.relpath(root, source))
            patch(base_path=dest_path, patch_file=patch_file)


def rename(pattern, name):
    for extracted in glob.glob(pattern):
        os.rename(extracted, name)


class OgreConan(ConanFile):
    name = "OGRE"
    version = "2.1.0"
    description = "Open Source 3D Graphics Engine"
    folder = 'ogre-v2.1'
    install_path = os.path.join('_build', folder, 'sdk')
    generators = "cmake"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "with_cg": [True, False],
        "with_metal": [True, False]
    }
    default_options = (
        "shared=True",
        "with_cg=True",
        "with_metal=False",
        "freetype:shared=False"
    )
    exports = ["CMakeLists.txt", 'patches*']
    requires = (
        "freeimage/3.17.0@gsage/master",
        "freetype/2.6.3@hilborn/stable",
        "zlib/1.2.8@lasote/stable",
        "zziplib/0.13.59@gsage/master"
    )
    url = "http://github.com/sixten-hilborn/conan-ogre"
    license = "https://opensource.org/licenses/mit-license.php"

    def configure(self):
        if 'x86' not in str(self.settings.arch):
            self.options.with_cg = False

    def requirements(self):
        # Cg won't build on Mac OSX, it's not compatible with the latest SDK
        # disabling it as Nvidia no longer supports it
        if self.options.with_cg and not self.settings.os == "Macos":
            self.requires("Cg/3.1@hilborn/stable")

        repo = "hilborn/stable"

        # hilborn/stable does not work for osx
        if self.settings.os == "Macos":
            repo = "gsage/master"

        self.requires.add("OIS/1.3@{}".format(repo), private=False)

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
        get("https://bitbucket.org/sinbad/ogre/get/v2-1.zip")
        rename('sinbad-ogre*', self.folder)
        apply_patches('patches', self.folder)
        #replace_in_file(
        #    '{0}/Components/Overlay/CMakeLists.txt'.format(self.folder),
        #    'target_link_libraries(OgreOverlay OgreMain ${FREETYPE_LIBRARIES})',
        #    'target_link_libraries(OgreOverlay OgreMain ${FREETYPE_LIBRARIES} ${CONAN_LIBS_BZIP2} ${CONAN_LIBS_LIBPNG} ${CONAN_LIBS_ZLIB})')

    def build(self):
        cmake = CMake(self)
        options = {
            'OGRE_BUILD_TESTS': False,
            'OGRE_BUILD_TOOLS': False,
            'OGRE_INSTALL_PDB': False,
            'CMAKE_INSTALL_PREFIX:': os.path.join(os.getcwd(), self.install_path),
            'OGRE_BUILD_SAMPLES': 0,
            'OGRE_BUILD_RENDERSYSTEM_METAL': 1 if self.options.with_metal else 0
        }
        if not self.options.shared:
            options['OGRE_STATIC'] = 1
            if self.settings.os == "Linux":
                options['CMAKE_SHARED_LINKER_FLAGS'] = '-Wl, --export-all-symbols'

        cmake.configure(defs=options, build_dir='_build')
        cmake.build(target='install')

    def package(self):
        sdk_dir = self.install_path
        include_dir = os.path.join(sdk_dir, 'include', 'OGRE')
        lib_dir = os.path.join(sdk_dir, 'lib')
        bin_dir = os.path.join(sdk_dir, 'bin')
        frameworks_dir = os.path.join(lib_dir, 'macosx', 'Release')

        self.copy(pattern="*.h", dst="include", src=include_dir)
        self.copy(pattern="*.inl", dst="include", src=include_dir)
        self.copy("*.lib", dst="lib", src=lib_dir, keep_path=False)
        self.copy("*.a", dst="lib", src=lib_dir, keep_path=False)
        self.copy("*.so*", dst="lib", src=lib_dir, keep_path=False, links=True)
        self.copy("*.dylib", dst="lib", src=lib_dir, keep_path=False)
        self.copy("*.dll", dst="bin", src=bin_dir, keep_path=False)
        if self.settings.os == "Macos":
            self.copy("*.*", dst="Frameworks", src=frameworks_dir, keep_path=True)

    def package_info(self):
        self.cpp_info.libs = [
            'OgreMain',
            'OgreOverlay',
            'OgreMeshLoadGenerator',
            'OgreHlmsPbsMobile',
            'OgreHlmsPbs',
            'OgreHlmsUnlitMobile',
            'OgreHlmsUnlit',
        ]

        is_apple = (self.settings.os == 'Macos' or self.settings.os == 'iOS')
        if is_apple:
            self.cpp_info.exelinkflags.append("-framework Cocoa")
            self.cpp_info.sharedlinkflags = self.cpp_info.exelinkflags

        if not self.options.shared:
            self.cpp_info.libs = ["{}Static".format(l) for l in self.cpp_info.libs]
            self.cpp_info.libs.extend([
                'RenderSystem_GL3PlusStatic',
                'RenderSystem_NULLStatic',
                'Plugin_ParticleFXStatic',
            ])
            self.user_info.STATIC = 1

        if self.settings.build_type == "Debug" and not is_apple:
            self.cpp_info.libs = [lib+'_d' for lib in self.cpp_info.libs]

        if self.settings.os == 'Linux':
            self.cpp_info.libs.append('rt')
