/* 全部まとめて走らせる。

     node tests/run.mjs

   配信サーバーは自分で立てて、終わったら落とす（2026-09-24）。
   それまでは手で立てる前提だったので、立てっぱなしのサーバーが毎回残っていた。
   すでに BASE のポートが応答していれば、そちらを使って立てない
   （手で立てて開発している最中に、横から落とさないため）。

   BASE で配信先を変えられる（本番に当てるときは BASE=https://... ）。
   外のホストを指しているときは、当然こちらでは立てない。 */
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, '..');
const SUITES = ['pricing.mjs', 'header.mjs', 'content.mjs', 'funnel.mjs', 'a11y.mjs'];
const BASE = process.env.BASE || 'http://127.0.0.1:8899';

const alive = async () => {
    try {
        const c = AbortSignal.timeout(1500);
        await fetch(`${BASE}/index.html`, { signal: c });
        return true;
    } catch { return false; }
};

/* 立てたときだけ落とす。手で立っていたものには触らない */
let server = null;
async function serve() {
    if (await alive()) return '（すでに動いているものを使う）';
    const u = new URL(BASE);
    if (!['127.0.0.1', 'localhost'].includes(u.hostname)) {
        return '（外のホストなので立てない）';
    }
    server = spawn('python3', ['-m', 'http.server', u.port || '80', '--directory', ROOT],
        { stdio: 'ignore', detached: false });
    for (let i = 0; i < 40; i += 1) {          // 最大4秒待つ
        await new Promise((r) => setTimeout(r, 100));
        if (await alive()) return '（このプロセスで立てた）';
    }
    throw new Error(`${BASE} が立ち上がらない`);
}

function stop() {
    if (!server) return;
    try { server.kill('SIGTERM'); } catch { /* noop */ }
    server = null;
}
/* 途中で落ちても残さない */
for (const sig of ['SIGINT', 'SIGTERM']) process.on(sig, () => { stop(); process.exit(130); });
process.on('exit', stop);

console.log(`配信先 ${BASE} ${await serve()}`);

let failed = 0;
try {
    for (const s of SUITES) {
        const out = await new Promise((res) => {
            const c = spawn('node', [join(HERE, s)], { env: process.env });
            let buf = '';
            c.stdout.on('data', (d) => { buf += d; });
            c.stderr.on('data', (d) => { buf += d; });
            c.on('close', (code) => res({ code, buf }));
        });
        const line = out.buf.split('\n').filter(l => l.startsWith('RESULT')).pop() || '(結果行なし)';
        console.log(`${s.padEnd(14)} ${line}`);
        if (out.code !== 0) { failed += 1; console.log(out.buf.split('\n').filter(l => l.startsWith('FAIL')).join('\n')); }
    }
} finally {
    stop();
}
console.log(failed ? `\n${failed} スイートが FAILED` : '\nすべてのスイートが PASS');
process.exit(failed ? 1 : 0);
