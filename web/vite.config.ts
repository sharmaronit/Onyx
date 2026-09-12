// @lovable.dev/vite-tanstack-config already includes the following — do NOT add them manually
// or the app will break with duplicate plugins:
//   - TanStack devtools (dev-only, first), tanstackStart, viteReact, tailwindcss, tsConfigPaths,
//     nitro (build-only using cloudflare as a default target), VITE_* env injection, @ path alias,
//     React/TanStack dedupe, error logger plugins, and sandbox detection (port/host/strictPort).
// You can pass additional config via defineConfig({ vite: { ... }, etc... }) if needed.
import { defineConfig } from "@lovable.dev/vite-tanstack-config";

const backendUrl = process.env.ONYX_BACKEND_URL ?? "http://127.0.0.1:8020";

export default defineConfig({
  vite: {
    server: {
      // Endpoint heartbeats update SQLite continuously. Ignoring runtime database
      // files prevents Vite from treating telemetry writes as source changes and
      // reloading the entire browser page.
      watch: {
        ignored: [
          "**/backend/*.db",
          "**/backend/*.db-journal",
          "**/backend/*.db-wal",
          "**/backend/*.db-shm",
        ],
      },
      proxy: {
        "/api": {
          target: backendUrl,
          changeOrigin: true,
        },
      },
    },
  },
  tanstackStart: {
    // Redirect TanStack Start's bundled server entry to src/server.ts (our SSR error wrapper).
    // nitro/vite builds from this
    server: { entry: "server" },
  },
});
