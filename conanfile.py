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
        "with_metal": [True, False],
        "hlms_type": ["desktop", "mobile"],
    }
    default_options = (
        "shared=True",
        "with_cg=True",
        "with_metal=False",
        "freetype:shared=False",
        "hlms_type=desktop",
    )
    exports = ["CMakeLists.txt", 'patches*']
    requires = (
        "freeimage/3.17.0@gsage/master",
        "freetype/2.6.3@gsage/master",
        "zlib/1.2.11@lasote/stable",
        "zziplib/0.13.59@gsage/master",
    )
    url = "http://github.com/sixten-hilborn/conan-ogre"
    license = "https://opensource.org/licenses/mit-license.php"

    def configure(self):
        if 'x86' not in str(self.settings.arch):
            self.options.with_cg = False

        if self.settings.os == "Macos":
            self.options["SDL2"].x11_video = False

    def requirements(self):
        # Cg won't build on Mac OSX, it's not compatible with the latest SDK
        # disabling it as Nvidia no longer supports it
        if self.options.with_cg and not self.settings.os == "Macos":
            self.requires("Cg/3.1@hilborn/stable")

        repo = "hilborn/stable"

        # hilborn/stable does not work for osx
        if self.settings.os == "Macos":
            repo = "gsage/master"

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
        get("https://github.com/OGRECave/ogre/archive/v2-1.zip")
        rename('ogre*', self.folder)

    def build(self):
        cmake = CMake(self)
        options = {
            'OGRE_BUILD_TESTS': False,
            'OGRE_BUILD_TOOLS': False,
            'OGRE_INSTALL_PDB': True,
            'CMAKE_INSTALL_PREFIX:': os.path.join(os.getcwd(), self.install_path),
            'OGRE_BUILD_RENDERSYSTEM_METAL': 1 if self.options.with_metal else 0,
            'CMAKE_CXX_STANDARD': 11,
            'OGRE_BUILD_SAMPLES2': False,
            'OGRE_DEBUG_LEVEL_DEBUG': 0,
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
            'OgreMeshLodGenerator',
        ]

        if self.options.hlms_type == "desktop":
            self.cpp_info.libs.extend([
                'OgreHlmsPbs',
                'OgreHlmsUnlit',
            ])
        else:
            self.cpp_info.libs.extend([
                'OgreHlmsPbsMobile',
                'OgreHlmsUnlitMobile',
            ])

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
            if self.options.with_metal:
                self.cpp_info.libs.append("RenderSystem_MetalStatic")

            self.user_info.STATIC = 1

        if self.settings.build_type == "Debug" and not is_apple:
            self.cpp_info.libs = [lib+'_d' for lib in self.cpp_info.libs]

        if self.settings.os == 'Linux':
            self.cpp_info.libs.append('rt')
