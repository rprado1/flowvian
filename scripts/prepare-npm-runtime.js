#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const https = require('https');

const pkg = require('../package.json');

function fail(message) {
  process.stderr.write(`[prepare-npm-runtime] ${message}\n`);
  process.exit(1);
}

function ensureDir(dirPath) {
  fs.mkdirSync(dirPath, { recursive: true });
}

function fetchJson(url) {
  return new Promise((resolve, reject) => {
    const req = https.get(
      url,
      {
        headers: {
          'User-Agent': 'wbui-npm-runtime',
          Accept: 'application/vnd.github+json',
        },
      },
      (res) => {
        let data = '';
        res.setEncoding('utf8');
        res.on('data', (chunk) => {
          data += chunk;
        });
        res.on('end', () => {
          if (res.statusCode && res.statusCode >= 200 && res.statusCode < 300) {
            try {
              resolve(JSON.parse(data));
            } catch (err) {
              reject(new Error(`invalid JSON response: ${err.message}`));
            }
            return;
          }

          reject(new Error(`request failed (${res.statusCode}): ${data}`));
        });
      }
    );

    req.on('error', reject);
    req.end();
  });
}

function downloadFile(url, outputPath) {
  return new Promise((resolve, reject) => {
    const file = fs.createWriteStream(outputPath);

    const request = https.get(
      url,
      {
        headers: {
          'User-Agent': 'wbui-npm-runtime',
          Accept: 'application/octet-stream',
        },
      },
      (res) => {
        if (res.statusCode && res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
          file.close();
          if (fs.existsSync(outputPath)) {
            fs.unlinkSync(outputPath);
          }
          downloadFile(res.headers.location, outputPath).then(resolve).catch(reject);
          return;
        }

        if (!res.statusCode || res.statusCode < 200 || res.statusCode >= 300) {
          file.close();
          if (fs.existsSync(outputPath)) {
            fs.unlinkSync(outputPath);
          }
          reject(new Error(`download failed with status ${res.statusCode}`));
          return;
        }

        res.pipe(file);
        file.on('finish', () => {
          file.close(resolve);
        });
      }
    );

    request.on('error', (err) => {
      file.close();
      if (fs.existsSync(outputPath)) {
        fs.unlinkSync(outputPath);
      }
      reject(err);
    });

    request.end();
  });
}

function chmodExecutableIfNeeded(filePath) {
  if (process.platform === 'linux') {
    fs.chmodSync(filePath, 0o755);
  }
}

async function main() {
  const config = pkg.config || {};
  const repo = config.releaseRepo;
  const tag = config.releaseTag;
  const runtimeAssetsByTarget = config.runtimeAssetsByTarget || {};
  const runtimeBinaryByPlatform = config.runtimeBinaryByPlatform || {};
  const supportedTargets = String(config.supportedTargets || '')
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean);

  if (!repo || !tag) {
    fail('missing releaseRepo/releaseTag in package.json config.');
  }

  const target = `${process.platform}-${process.arch}`;
  if (!supportedTargets.includes(target)) {
    fail(
      `unsupported target '${target}'. Supported targets: ${supportedTargets.join(', ') || '(none configured)'}`
    );
  }

  const assetName = runtimeAssetsByTarget[target];
  if (!assetName) {
    fail(`no runtime asset configured for target '${target}'.`);
  }

  const runtimeBinaryName = runtimeBinaryByPlatform[process.platform];
  if (!runtimeBinaryName) {
    fail(`no runtime binary name configured for platform '${process.platform}'.`);
  }

  const runtimeDir = path.resolve(__dirname, '..', 'runtime');
  const runtimePath = path.join(runtimeDir, runtimeBinaryName);

  if (fs.existsSync(runtimePath)) {
    process.stdout.write(`[prepare-npm-runtime] runtime already present: ${runtimePath}\n`);
    return;
  }

  ensureDir(runtimeDir);

  const releaseApiUrl = `https://api.github.com/repos/${repo}/releases/tags/${tag}`;
  process.stdout.write(`[prepare-npm-runtime] querying release ${tag} from ${repo}\n`);
  const release = await fetchJson(releaseApiUrl);
  const assets = Array.isArray(release.assets) ? release.assets : [];

  if (!assets.length) {
    fail(`release ${tag} has no assets. Upload runtime assets for ${supportedTargets.join(', ')}.`);
  }

  const asset = assets.find((item) => item.name === assetName);
  if (!asset) {
    const listed = assets.map((item) => item.name).join(', ');
    fail(
      `runtime asset '${assetName}' not found for target '${target}'. Available assets: ${listed || '(none)'}`
    );
  }

  process.stdout.write(`[prepare-npm-runtime] downloading ${asset.name}\n`);
  await downloadFile(asset.browser_download_url, runtimePath);
  chmodExecutableIfNeeded(runtimePath);
  process.stdout.write(`[prepare-npm-runtime] runtime ready at ${runtimePath}\n`);
}

main().catch((err) => {
  fail(err.message);
});
