/* 縦型SNS版のコマを撮る。使い方: node sns_render.mjs <作業場所> [--check]
   作業場所に sns_scene.html・logo-word.svg・fr/{oil,yin,kin,ezu}/NNNN.jpg が要る（sns_build.sh が用意する）。
   --check は代表の15コマだけ撮って check/sheet.jpg に並べる（本番の480コマは約70秒）。
   アニメは Web Animations の currentTime を手で進めるので、撮るのが遅くてもコマ落ちしない。 */
import { existsSync, mkdirSync, rmSync, readdirSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { join, resolve } from 'node:path';

const WORK = resolve(process.argv[2] || '/tmp/aichi_map/sns');
const CHECK = process.argv.includes('--check');
const FPS = 24, DUR = 20.0;

// Playwright の場所は tests/lib.mjs と同じ候補から探す
const PW = [process.env.PW, '/opt/node22/lib/node_modules/playwright/index.js',
  '/opt/homebrew/lib/node_modules/playwright/index.js', '/usr/local/lib/node_modules/playwright/index.js']
  .find((p) => p && existsSync(p));
if (!PW) throw new Error('Playwright が無い：npm i -g playwright && npx playwright install chromium（別の場所なら PW=.../playwright/index.js）');
const { chromium } = (await import(PW)).default;

// ブラウザ：CHROME の指定 > /opt/pw-browsers の新しいもの（クラウドの環境）> Playwright の既定（Mac）
function chromePath() {
  if (process.env.CHROME) return process.env.CHROME;
  const root = '/opt/pw-browsers'; if (!existsSync(root)) return undefined;
  const ds = readdirSync(root).filter((d) => /^chromium-\d+$/.test(d)).sort((a, b) => b.split('-')[1] - a.split('-')[1]);
  for (const d of ds) for (const s of ['chrome-linux64/chrome', 'chrome-linux/chrome']) {
    const p = join(root, d, s); if (existsSync(p)) return p; }
}

const OUT = join(WORK, CHECK ? 'check' : 'frames');
rmSync(OUT, { recursive: true, force: true }); mkdirSync(OUT, { recursive: true });
const times = CHECK
  ? [0, 1500, 3000, 3600, 4700, 6000, 7250, 8700, 9250, 11000, 12600, 14900, 16300, 17600, 19950]
  : Array.from({ length: Math.round(DUR * FPS) }, (_, i) => (i * 1000) / FPS);

const browser = await chromium.launch({ executablePath: chromePath(),
  args: ['--force-color-profile=srgb', '--font-render-hinting=none', '--hide-scrollbars', '--allow-file-access-from-files'] });
try {
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  page.on('pageerror', (e) => console.log('PAGE ERROR:', e.message));
  await page.goto('file://' + join(WORK, 'sns_scene.html'));
  await page.waitForFunction(() => window.__ready === true, null, { timeout: 60000 });
  const t0 = Date.now();
  for (let i = 0; i < times.length; i++) {
    await page.evaluate((ms) => window.__seek(ms), times[i]);
    await page.screenshot({ path: join(OUT, `f${String(i).padStart(5, '0')}.jpg`), type: 'jpeg', quality: CHECK ? 88 : 95 });
  }
  console.log(`撮影 ${times.length}枚 / ${((Date.now() - t0) / 1000).toFixed(1)}秒`);
} finally { await browser.close(); }   // 残すと次まで居座る

if (CHECK) {   // 5列に並べる
  const n = times.length, cols = 5, ins = [];
  for (let i = 0; i < n; i++) ins.push('-i', join(OUT, `f${String(i).padStart(5, '0')}.jpg`));
  const lay = times.map((_, i) => { const c = i % cols, r = (i / cols) | 0;
    const x = c ? Array.from({ length: c }, (_, k) => `w${k}`).join('+') : '0';
    const y = r ? Array.from({ length: r }, (_, k) => `h${k * cols}`).join('+') : '0'; return `${x}_${y}`; }).join('|');
  const lbl = times.map((t, i) => `[${i}]scale=400:-2,drawtext=text='${(t / 1000).toFixed(1)}s':x=12:y=12:fontsize=26:fontcolor=red:box=1:boxcolor=white@0.7[v${i}]`).join(';');
  execFileSync('ffmpeg', ['-y', '-loglevel', 'error', ...ins, '-filter_complex',
    `${lbl};${times.map((_, i) => `[v${i}]`).join('')}xstack=inputs=${n}:layout=${lay}`, join(OUT, 'sheet.jpg')], { stdio: 'inherit' });
  console.log('→', join(OUT, 'sheet.jpg'));
}
