#!/usr/bin/env python3
import os
import sys

def patch_opentui(opentui_root):
    print(f"=== Patching OpenTUI in {opentui_root} for Android Bionic ===")

    ndk_home = os.environ.get("ANDROID_NDK_HOME", "")
    if not ndk_home or not os.path.exists(ndk_home):
        for candidate in [
            "/usr/local/lib/android/sdk/ndk/30.0.16248370",
            "/usr/local/lib/android/sdk/ndk/27.0.12077973",
        ]:
            if os.path.exists(candidate):
                ndk_home = candidate
                break

    if not ndk_home:
        print("Error: Could not locate ANDROID_NDK_HOME")
        sys.exit(1)

    ndk_sysroot = os.path.join(ndk_home, "toolchains/llvm/prebuilt/linux-x86_64/sysroot")
    print(f"Using NDK Sysroot: {ndk_sysroot}")

    include_cxx = os.path.join(ndk_sysroot, "usr/include/c++/v1").replace("\\", "/")
    include_general = os.path.join(ndk_sysroot, "usr/include").replace("\\", "/")
    include_arch = os.path.join(ndk_sysroot, "usr/include/aarch64-linux-android").replace("\\", "/")
    lib_arch = os.path.join(ndk_sysroot, "usr/lib/aarch64-linux-android").replace("\\", "/")
    lib_api24 = os.path.join(ndk_sysroot, "usr/lib/aarch64-linux-android/24").replace("\\", "/")

    # Generate /tmp/android-libc.txt
    libc_path = "/tmp/android-libc.txt"
    if os.path.exists(libc_path):
        with open(libc_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        new_lines = []
        for line in lines:
            if line.startswith("include_dir="):
                new_lines.append(f"include_dir={include_general}\n")
            elif line.startswith("sys_include_dir="):
                new_lines.append(f"sys_include_dir={include_arch}\n")
            elif line.startswith("crt_dir="):
                new_lines.append(f"crt_dir={lib_api24}\n")
            elif line.startswith("cc_dir="):
                new_lines.append(f"cc_dir={lib_api24}\n")
            elif line.startswith("gcc_dir="):
                new_lines.append(f"gcc_dir={lib_api24}\n")
            else:
                new_lines.append(line)
        with open(libc_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
    else:
        with open(libc_path, "w", encoding="utf-8") as f:
            f.write(f"""include_dir={include_general}
sys_include_dir={include_arch}
crt_dir={lib_api24}
msvc_lib_dir=
kernel32_lib_dir=
gcc_dir={lib_api24}
darwin_sdk_dir=
cc_dir={lib_api24}
""")
    native_libc = os.path.join(opentui_root, "packages/native/android-libc.txt")
    try:
        import shutil
        shutil.copyfile(libc_path, native_libc)
        print(f"Copied {libc_path} to {native_libc}")
    except Exception as e:
        print(f"Notice: could not copy to {native_libc}: {e}")
    print(f"Configured {libc_path}")

    # Patch NDK headers to prevent host glibc leakage
    limits_path = os.path.join(ndk_sysroot, "usr/include/limits.h")
    if os.path.exists(limits_path):
        with open(limits_path, "r", encoding="utf-8") as f:
            lcontent = f.read()
        if "__has_include_next(<limits.h>)" in lcontent:
            repl = """0
#ifndef CHAR_BIT
#define CHAR_BIT 8
#define SCHAR_MIN (-128)
#define SCHAR_MAX 127
#define UCHAR_MAX 255
#define SHRT_MIN (-32768)
#define SHRT_MAX 32767
#define USHRT_MAX 65535
#define INT_MIN (-2147483647-1)
#define INT_MAX 2147483647
#define UINT_MAX 4294967295U
#define LONG_MIN (-9223372036854775807L-1L)
#define LONG_MAX 9223372036854775807L
#define ULONG_MAX 18446744073709551615UL
#define LLONG_MIN (-9223372036854775807LL-1LL)
#define LLONG_MAX 9223372036854775807LL
#define ULLONG_MAX 18446744073709551615ULL
#endif"""
            lcontent = lcontent.replace("__has_include_next(<limits.h>)", repl)
            with open(limits_path, "w", encoding="utf-8") as f:
                f.write(lcontent)
            print("Successfully patched NDK limits.h to isolate from host glibc")

    cdefs_path = os.path.join(ndk_sysroot, "usr/include/sys/cdefs.h")
    if os.path.exists(cdefs_path):
        with open(cdefs_path, "r", encoding="utf-8") as f:
            ccontent = f.read()
        if "#error Unversioned target triples are not supported!" in ccontent:
            ccontent = ccontent.replace(
                "#error Unversioned target triples are not supported!",
                "// #error Unversioned target triples are not supported!\n#ifndef __ANDROID_API__\n#define __ANDROID_API__ 24\n#endif\n#ifndef __ANDROID_MIN_SDK_VERSION__\n#define __ANDROID_MIN_SDK_VERSION__ 24\n#endif"
            )
            with open(cdefs_path, "w", encoding="utf-8") as f:
                f.write(ccontent)
            print("Successfully patched NDK sys/cdefs.h")

    # 1. Patch miniaudio_shim.c
    shim_path = os.path.join(opentui_root, "packages/native/src/miniaudio_shim.c")
    if os.path.exists(shim_path):
        with open(shim_path, "r", encoding="utf-8") as f:
            content = f.read()
        target = """#if defined(__linux__)
#define MA_ENABLE_ONLY_SPECIFIC_BACKENDS
#define MA_ENABLE_ALSA
#define MA_ENABLE_PULSEAUDIO
#endif"""
        replacement = """#if defined(__linux__) && !defined(__ANDROID__)
#define MA_ENABLE_ONLY_SPECIFIC_BACKENDS
#define MA_ENABLE_ALSA
#define MA_ENABLE_PULSEAUDIO
#elif defined(__ANDROID__)
#define MA_ENABLE_ONLY_SPECIFIC_BACKENDS
#define MA_ENABLE_AAUDIO
#define MA_ENABLE_OPENSL
#endif"""
        if target in content:
            content = content.replace(target, replacement, 1)
            with open(shim_path, "w", encoding="utf-8") as f:
                f.write(content)
            print("Successfully patched miniaudio_shim.c")
        else:
            print("Warning: target pattern not found in miniaudio_shim.c")
    else:
        print(f"Error: {shim_path} not found")

    # 2. Patch build.zig
    build_path = os.path.join(opentui_root, "packages/native/build.zig")
    if os.path.exists(build_path):
        with open(build_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Patch SUPPORTED_TARGETS
        target_supported = """const SUPPORTED_TARGETS = [_]SupportedTarget{
    .{ .zig_target = "x86_64-linux-gnu.2.17", .output_name = "x86_64-linux", .description = "Linux x86_64" },"""
        repl_supported = """const SUPPORTED_TARGETS = [_]SupportedTarget{
    .{ .zig_target = "aarch64-linux-android.24", .output_name = "android-arm64", .description = "Android ARM64" },
    .{ .zig_target = "x86_64-linux-gnu.2.17", .output_name = "x86_64-linux", .description = "Linux x86_64" },"""
        if target_supported in content:
            content = content.replace(target_supported, repl_supported, 1)
            print("Patched SUPPORTED_TARGETS for Android ARM64")

        # Patch pthread link
        target_pthread = """        .linux => {
            module.linkSystemLibrary("dl", .{});
            module.linkSystemLibrary("pthread", .{});
            module.linkSystemLibrary("m", .{});
        },"""
        repl_pthread = """        .linux => {
            module.linkSystemLibrary("dl", .{});
            if (!target.result.abi.isAndroid()) {
                module.linkSystemLibrary("pthread", .{});
            }
            module.linkSystemLibrary("m", .{});
        },"""
        if target_pthread in content:
            content = content.replace(target_pthread, repl_pthread, 1)
            print("Patched pthread linking for Android")

        # Patch addTranslatedCImports
        target_trans = """fn addTranslatedCImports(
    b: *std.Build,
    module: *std.Build.Module,
    optimize: std.lang.Optimize,
    target: std.Build.ResolvedTarget,
) void {
    const miniaudio_translate = b.addTranslateC(.{
        .root_source_file = b.path("src/vendor/miniaudio/miniaudio.h"),
        .target = target,
        .optimize = optimize,
    });
    miniaudio_translate.addIncludePath(b.path("src"));
    module.addImport("miniaudio", miniaudio_translate.createModule());

    const yoga_dep = b.dependency("yoga", .{});
    const yoga_translate = b.addTranslateC(.{
        .root_source_file = b.path("src/yoga-bridge.h"),
        .target = target,
        .optimize = optimize,
    });
    yoga_translate.addIncludePath(yoga_dep.path(""));
    module.addImport("yoga", yoga_translate.createModule());
    addContextABIHeader(b, module, optimize, target);
}"""
        repl_trans = f"""fn addTranslatedCImports(
    b: *std.Build,
    module: *std.Build.Module,
    optimize: std.lang.Optimize,
    target: std.Build.ResolvedTarget,
) void {{
    const is_android = target.result.abi.isAndroid();
    const miniaudio_translate = b.addTranslateC(.{{
        .root_source_file = b.path("src/vendor/miniaudio/miniaudio.h"),
        .target = target,
        .optimize = optimize,
        .link_libc = !is_android,
    }});
    miniaudio_translate.addIncludePath(b.path("src"));
    if (is_android) {{
        miniaudio_translate.defineCMacro("__ANDROID_API__", "24");
        miniaudio_translate.defineCMacro("__ANDROID_MIN_SDK_VERSION__", "24");
        miniaudio_translate.defineCMacro("__ANDROID__", "1");
        miniaudio_translate.addSystemIncludePath(.{{ .cwd_relative = "{include_arch}" }});
        miniaudio_translate.addSystemIncludePath(.{{ .cwd_relative = "{include_general}" }});
    }}
    module.addImport("miniaudio", miniaudio_translate.createModule());

    const yoga_dep = b.dependency("yoga", .{{}});
    const yoga_translate = b.addTranslateC(.{{
        .root_source_file = b.path("src/yoga-bridge.h"),
        .target = target,
        .optimize = optimize,
        .link_libc = !is_android,
    }});
    yoga_translate.addIncludePath(yoga_dep.path(""));
    if (is_android) {{
        yoga_translate.defineCMacro("__ANDROID_API__", "24");
        yoga_translate.defineCMacro("__ANDROID_MIN_SDK_VERSION__", "24");
        yoga_translate.defineCMacro("__ANDROID__", "1");
        yoga_translate.addSystemIncludePath(.{{ .cwd_relative = "{include_arch}" }});
        yoga_translate.addSystemIncludePath(.{{ .cwd_relative = "{include_general}" }});
    }}
    module.addImport("yoga", yoga_translate.createModule());
    addContextABIHeader(b, module, optimize, target);
}}"""
        if target_trans in content:
            content = content.replace(target_trans, repl_trans, 1)
            print("Patched addTranslatedCImports for Android")

        # Patch addContextABIHeader
        target_abi = """fn addContextABIHeader(
    b: *std.Build,
    module: *std.Build.Module,
    optimize: std.lang.Optimize,
    target: std.Build.ResolvedTarget,
) void {
    const header = b.addTranslateC(.{
        .root_source_file = b.path("include/opentui.h"),
        .target = target,
        .optimize = optimize,
    });
    module.addImport("context_abi_c", header.createModule());
}"""
        repl_abi = f"""fn addContextABIHeader(
    b: *std.Build,
    module: *std.Build.Module,
    optimize: std.lang.Optimize,
    target: std.Build.ResolvedTarget,
) void {{
    const is_android = target.result.abi.isAndroid();
    const header = b.addTranslateC(.{{
        .root_source_file = b.path("include/opentui.h"),
        .target = target,
        .optimize = optimize,
        .link_libc = !is_android,
    }});
    if (is_android) {{
        header.defineCMacro("__ANDROID_API__", "24");
        header.defineCMacro("__ANDROID_MIN_SDK_VERSION__", "24");
        header.defineCMacro("__ANDROID__", "1");
        header.addSystemIncludePath(.{{ .cwd_relative = "{include_arch}" }});
        header.addSystemIncludePath(.{{ .cwd_relative = "{include_general}" }});
    }}
    module.addImport("context_abi_c", header.createModule());
}}"""
        if target_abi in content:
            content = content.replace(target_abi, repl_abi, 1)
            print("Patched addContextABIHeader for Android")

        # Patch createLibraries
        target_createlibs = """fn createLibraries(
    b: *std.Build,
    target: std.Build.ResolvedTarget,
    optimize: std.lang.Optimize,
    build_options: *std.Build.Step.Options,
    macos_sdk_path: ?[]const u8,
) [2]*std.Build.Step.Compile {
    const module = b.createModule(.{
        .root_source_file = b.path(ROOT_SOURCE_FILE),
        .target = target,
        .optimize = optimize,
        // Release symbols must describe this exact optimized code. The package
        // build detaches them before stripping only the distribution copy.
        .strip = false,
        .pic = true,
    });
    applyDependencies(b, module, optimize, target, build_options);
    addNativeAudioDependencies(b, module, target, macos_sdk_path);
    addYogaDependencies(b, module, false);
    const shared = b.addLibrary(.{
        .name = LIB_NAME,
        .root_module = module,
        .linkage = .dynamic,
    });
    if (target.result.os.tag == .linux and optimize != .debug) shared.build_id = .sha1;
    // Zig's default DLL entry skips the MinGW CRT startup, so CRT state such as
    // the DLL atexit table would stay uninitialized. MinGW's strtod registers
    // there, and both the Zig code and FFmpeg call it, so this applies with or
    // without video.
    if (target.result.os.tag == .windows and target.result.abi == .gnu) {
        shared.entry = .{ .symbol_name = "DllMainCRTStartup" };
    }
    const static = b.addLibrary(.{
        // COFF uses .lib for both archives and DLL import libraries.
        .name = if (target.result.os.tag == .windows) "opentui-static" else LIB_NAME,
        .root_module = module,
        .linkage = .static,
    });
    shared.installHeader(b.path("include/opentui.h"), "opentui.h");
    static.installHeader(b.path("include/opentui.h"), "opentui.h");
    return .{ shared, static };
}"""
        repl_createlibs = f"""fn createLibraries(
    b: *std.Build,
    target: std.Build.ResolvedTarget,
    optimize: std.lang.Optimize,
    build_options: *std.Build.Step.Options,
    macos_sdk_path: ?[]const u8,
) [2]*std.Build.Step.Compile {{
    const is_android = target.result.abi.isAndroid();
    const module = b.createModule(.{{
        .root_source_file = b.path(ROOT_SOURCE_FILE),
        .target = target,
        .optimize = optimize,
        // Release symbols must describe this exact optimized code. The package
        // build detaches them before stripping only the distribution copy.
        .strip = false,
        .pic = true,
    }});
    if (is_android) {{
        module.addSystemIncludePath(.{{ .cwd_relative = "{include_cxx}" }});
        module.addSystemIncludePath(.{{ .cwd_relative = "{include_arch}" }});
        module.addSystemIncludePath(.{{ .cwd_relative = "{include_general}" }});
        module.addLibraryPath(.{{ .cwd_relative = "{lib_arch}" }});
        module.addLibraryPath(.{{ .cwd_relative = "{lib_api24}" }});
    }}
    applyDependencies(b, module, optimize, target, build_options);
    addNativeAudioDependencies(b, module, target, macos_sdk_path);
    addYogaDependencies(b, module, false);
    const shared = b.addLibrary(.{{
        .name = LIB_NAME,
        .root_module = module,
        .linkage = .dynamic,
    }});
    if (target.result.os.tag == .linux and optimize != .debug) shared.build_id = .sha1;
    // Zig's default DLL entry skips the MinGW CRT startup, so CRT state such as
    // the DLL atexit table would stay uninitialized. MinGW's strtod registers
    // there, and both the Zig code and FFmpeg call it, so this applies with or
    // without video.
    if (target.result.os.tag == .windows and target.result.abi == .gnu) {{
        shared.entry = .{{ .symbol_name = "DllMainCRTStartup" }};
    }}
    const static = b.addLibrary(.{{
        // COFF uses .lib for both archives and DLL import libraries.
        .name = if (target.result.os.tag == .windows) "opentui-static" else LIB_NAME,
        .root_module = module,
        .linkage = .static,
    }});
    if (is_android) {{
        shared.setLibCFile(.{{ .cwd_relative = "/tmp/android-libc.txt" }});
        static.setLibCFile(.{{ .cwd_relative = "/tmp/android-libc.txt" }});
    }}
    shared.installHeader(b.path("include/opentui.h"), "opentui.h");
    static.installHeader(b.path("include/opentui.h"), "opentui.h");
    return .{{ shared, static }};
}}"""
        if target_createlibs in content:
            content = content.replace(target_createlibs, repl_createlibs, 1)
            print("Patched createLibraries for Android")

        # Patch opentui_module in pub fn build
        target_mod = """    const module_target = b.standardTargetOptions(.{});
    const opentui_module = b.addModule("opentui", .{
        .root_source_file = b.path("src/opentui.zig"),
        .target = module_target,
        .optimize = optimize,
    });
    applyDependencies(b, opentui_module, optimize, module_target, build_options);"""
        repl_mod = f"""    const module_target = b.standardTargetOptions(.{{}});
    const opentui_module = b.addModule("opentui", .{{
        .root_source_file = b.path("src/opentui.zig"),
        .target = module_target,
        .optimize = optimize,
    }});
    if (module_target.result.abi.isAndroid()) {{
        opentui_module.addSystemIncludePath(.{{ .cwd_relative = "{include_cxx}" }});
        opentui_module.addSystemIncludePath(.{{ .cwd_relative = "{include_arch}" }});
        opentui_module.addSystemIncludePath(.{{ .cwd_relative = "{include_general}" }});
        opentui_module.addLibraryPath(.{{ .cwd_relative = "{lib_arch}" }});
        opentui_module.addLibraryPath(.{{ .cwd_relative = "{lib_api24}" }});
    }}
    applyDependencies(b, opentui_module, optimize, module_target, build_options);"""
        if target_mod in content:
            content = content.replace(target_mod, repl_mod, 1)
            print("Patched opentui_module for Android")

        with open(build_path, "w", encoding="utf-8") as f:
            f.write(content)
        print("Successfully updated build.zig")
    else:
        print(f"Error: {build_path} not found")

    # 3. Patch clipboard/host.zig for missing pthread_tryjoin_np in Bionic
    host_path = os.path.join(opentui_root, "packages/native/src/clipboard/host.zig")
    if os.path.exists(host_path):
        with open(host_path, "r", encoding="utf-8") as f:
            hcontent = f.read()
        target_h = 'extern "c" fn pthread_tryjoin_np(thread: std.Thread.Handle, result: ?*?*anyopaque) c_int;'
        repl_h = """extern "c" fn pthread_join(thread: std.Thread.Handle, retval: ?*?*anyopaque) c_int;
pub export fn pthread_tryjoin_np(thread: std.Thread.Handle, result: ?*?*anyopaque) callconv(.c) c_int {
    return pthread_join(thread, result);
}"""
        if target_h in hcontent:
            hcontent = hcontent.replace(target_h, repl_h, 1)
            with open(host_path, "w", encoding="utf-8") as f:
                f.write(hcontent)
            print("Successfully patched clipboard/host.zig for Bionic pthread_tryjoin_np")

if __name__ == "__main__":
    opentui_dir = sys.argv[1] if len(sys.argv) > 1 else "/tmp/opentui"
    patch_opentui(opentui_dir)
