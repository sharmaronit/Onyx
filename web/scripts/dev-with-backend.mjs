import { spawn } from 'node:child_process';
import net from 'node:net';
import process from 'node:process';

const isWindows = process.platform === 'win32';
const npmCmd = isWindows ? 'npm.cmd' : 'npm';
const pythonCmd = process.env.BACKEND_PYTHON || (isWindows ? 'python' : 'python3');

const processes = [];

function startProcess(command, name, cwd = process.cwd()) {
  const child = spawn(command, {
    cwd,
    stdio: 'inherit',
    shell: true,
  });

  child.on('error', (err) => {
    console.error(`[${name}] failed to start: ${err.message}`);
  });

  child.on('exit', (code) => {
    if (code !== 0) {
      console.error(`[${name}] exited with code ${code}`);
    }
    shutdown(code || 0);
  });

  processes.push(child);
  return child;
}

function shutdown(exitCode = 0) {
  while (processes.length > 0) {
    const p = processes.pop();
    if (p && !p.killed) {
      p.kill('SIGTERM');
    }
  }
  process.exit(exitCode);
}

process.on('SIGINT', () => shutdown(0));
process.on('SIGTERM', () => shutdown(0));

function isPortAvailable(port, host = '127.0.0.1') {
  return new Promise((resolve) => {
    const tester = net.createServer();
    tester.once('error', () => resolve(false));
    tester.once('listening', () => {
      tester.close(() => resolve(true));
    });
    tester.listen(port, host);
  });
}

console.log('Starting Onyx web stack (backend + frontend)...');
console.log(`Backend interpreter: ${pythonCmd}`);

const backendCmd = `${npmCmd} run dev:backend`;
const backendPortFree = await isPortAvailable(8020, '127.0.0.1');
if (backendPortFree) {
  startProcess(backendCmd, 'backend', process.cwd());
} else {
  console.log('Backend port 8020 is already in use. Assuming backend is already running.');
}

startProcess(`${npmCmd} run dev:frontend`, 'frontend', process.cwd());
