import { createRequire } from "node:module"

declare const OPENCODE_LIBC: string | undefined

// Lazy: on workerd import.meta.url is undefined and the watcher is never
// loaded, so createRequire must not run at module scope.
export default function load() {
  const require = createRequire(import.meta.url)
  const libc = typeof OPENCODE_LIBC === "undefined" ? undefined : OPENCODE_LIBC
  const platform = process.platform === "android" ? "linux" : process.platform
  return require(
    process.env.OPENCODE_PARCEL_WATCHER_PATH ??
      `@parcel/watcher-${platform}-${process.arch}${platform === "linux" ? `-${libc || "glibc"}` : ""}`,
  )
}
