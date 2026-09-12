import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const isWindows = process.platform === "win32";
const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const webRoot = path.resolve(scriptDir, "..");
const repoRoot = path.resolve(webRoot, "..");
const localVenvPython = path.join(repoRoot, ".venv", "Scripts", "python.exe");
const pythonCmd =
  process.env.BACKEND_PYTHON ||
  (fs.existsSync(localVenvPython) ? localVenvPython : isWindows ? "python" : "python3");

console.log("Starting Onyx backend API...");
console.log(`Backend interpreter: ${pythonCmd}`);

const child = spawn(
  `"${pythonCmd}" -m uvicorn backend.server:app --host 0.0.0.0 --port 8020 --reload`,
  {
    cwd: webRoot,
    stdio: "inherit",
    shell: true,
  },
);

child.on("error", (err) => {
  console.error(`[backend] failed to start: ${err.message}`);
  process.exit(1);
});

child.on("exit", (code) => {
  process.exit(code || 0);
});

process.on("SIGINT", () => child.kill("SIGTERM"));
process.on("SIGTERM", () => child.kill("SIGTERM"));
