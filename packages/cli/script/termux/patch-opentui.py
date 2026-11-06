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
        target_createlibs = """    const module = b.createModule(.{
        .root_source_file = b.path(ROOT_SOURCE_FILE),
        .target = target,
        .optimize = optimize,
        // Release symbols must describe this exact optimized code. The package
        // build detaches them before stripping only the distribution copy.
        .strip = false,
        .pic = true,
    });
    applyDependencies(b, module, optimize, target, build_options);"""
        repl_createlibs = f"""    const module = b.createModule(.{{
        .root_source_file = b.path(ROOT_SOURCE_FILE),
        .target = target,
        .optimize = optimize,
        // Release symbols must describe this exact optimized code. The package
        // build detaches them before stripping only the distribution copy.
        .strip = false,
        .pic = true,
    }});
    if (target.result.abi.isAndroid()) {{
        module.addCMacro("__ANDROID_API__", "24");
        module.addCMacro("__ANDROID_MIN_SDK_VERSION__", "24");
        module.addCMacro("__ANDROID__", "1");
        module.addSystemIncludePath(.{{ .cwd_relative = "{include_cxx}" }});
        module.addSystemIncludePath(.{{ .cwd_relative = "{include_arch}" }});
        module.addSystemIncludePath(.{{ .cwd_relative = "{include_general}" }});
        module.addLibraryPath(.{{ .cwd_relative = "{lib_arch}" }});
        module.addLibraryPath(.{{ .cwd_relative = "{lib_api24}" }});
    }}
    applyDependencies(b, module, optimize, target, build_options);"""
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
        opentui_module.addCMacro("__ANDROID_API__", "24");
        opentui_module.addCMacro("__ANDROID_MIN_SDK_VERSION__", "24");
        opentui_module.addCMacro("__ANDROID__", "1");
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

if __name__ == "__main__":
    opentui_dir = sys.argv[1] if len(sys.argv) > 1 else "/tmp/opentui"
    patch_opentui(opentui_dir)
