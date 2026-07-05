#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');

const pkg = require('../package.json');

const HELP_TEXT = [
  'wbui - WorkflowEXE Builder CLI',
  '',
  'Usage:',
  '  wbui start',
  '  wbui --help',
  '  wbui --version',
  '',
  'Commands:',
  '  start     Start wbui server on port 5007',
].join('\n');

function printHelp() {
  process.stdout.write(`${HELP_TEXT}\n`);
}

function printVersion() {
  process.stdout.write(`${pkg.version}\n`);
}

function fail(message) {
  process.stderr.write(`wbui: ${message}\n`);
  process.exit(1);
}

function runStart() {
  const binaryByPlatform = (pkg.config && pkg.config.runtimeBinaryByPlatform) || {};
  const binaryName = binaryByPlatform[process.platform];

  if (!binaryName) {
    fail(`unsupported platform '${process.platform}'. Supported: win32, linux.`);
  }

  const binaryPath = path.resolve(__dirname, '..', 'runtime', binaryName);

  if (!fs.existsSync(binaryPath)) {
    fail(
      `runtime binary not found at ${binaryPath}. Reinstall with npm install -g wbui.`
    );
  }

  const child = spawn(binaryPath, {
    stdio: 'inherit',
    env: {
      ...process.env,
      WBUI_PORT: process.env.WBUI_PORT || '5007',
    },
  });

  child.on('error', (err) => {
    fail(`failed to launch runtime: ${err.message}`);
  });

  child.on('exit', (code, signal) => {
    if (signal) {
      process.kill(process.pid, signal);
      return;
    }
    process.exit(code === null ? 1 : code);
  });
}

function main() {
  const command = process.argv[2];

  if (!command || command === '--help' || command === '-h' || command === 'help') {
    printHelp();
    return;
  }

  if (command === '--version' || command === '-v' || command === 'version') {
    printVersion();
    return;
  }

  if (command === 'start') {
    runStart();
    return;
  }

  fail(`unknown command '${command}'. Use wbui --help.`);
}

main();
