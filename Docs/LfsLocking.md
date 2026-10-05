<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Git LFS File Locking — Team Setup Guide</title>
<style>
body{background:#f6f7f9;color:#1a1a2e;font-family:"Segoe UI",Arial,sans-serif;max-width:900px;margin:0 auto;padding:32px;line-height:1.6;}
h1{font-size:26px;border-bottom:3px solid #2d6cdf;padding-bottom:8px;}
h2{font-size:20px;color:#2d6cdf;margin-top:32px;}
h3{font-size:16px;margin-top:20px;}
code{background:#e8eaf0;padding:2px 6px;border-radius:4px;font-family:Consolas,monospace;font-size:13px;}
pre{background:#1e1e2e;color:#cdd6f4;padding:14px 18px;border-radius:8px;overflow-x:auto;font-family:Consolas,monospace;font-size:13px;}
pre code{background:none;padding:0;color:inherit;}
table{border-collapse:collapse;width:100%;margin:12px 0;}
th,td{border:1px solid #cfd4e0;padding:8px 12px;text-align:left;font-size:14px;}
th{background:#eef1f8;}
.warn{background:#fff3cd;border-left:4px solid #dc9a2c;padding:12px 16px;border-radius:4px;}
.ok{background:#e6f4ea;border-left:4px solid #2f9f5f;padding:12px 16px;border-radius:4px;}
.bad{background:#fdecea;border-left:4px solid #d93025;padding:12px 16px;border-radius:4px;}
.zh{background:#f0f4ff;border-left:4px solid #2d6cdf;padding:12px 16px;border-radius:4px;font-size:14px;}
.step{background:#fff;border:1px solid #dfe3ec;border-radius:8px;padding:16px 20px;margin:14px 0;}
.step h3{margin-top:0;color:#2d6cdf;}
</style>
</head>
<body>
<h1>Git LFS File Locking — Team Setup Guide</h1>
<p><strong>Don't Trust The Levels</strong> · COMP 4900SEF group project · 6 members, single <code>main</code> branch</p>

<p>UE4 blueprints (<code>.uasset</code>) and maps (<code>.umap</code>) are binary — Git <strong>cannot merge them</strong>. If two people edit the same file, one person's work is silently destroyed. This guide sets up <strong>Git LFS File Locking</strong>: files are read-only by default; the editor locks a file the moment you edit it; teammates see a red warning and are refused.</p>

<div class="zh">
<p><strong>機制摘要（原文說明）：</strong>藍圖與地圖為二進制檔案，Git 無法合併。專案統一採用「單一主分支 + Git LFS 自動唯讀鎖定」模式：Pull 後檔案自動唯讀 → 編輯器修改瞬間自動向雲端請求鎖定 → 成功後解除唯讀；已被他人鎖定的檔案會紅字警告並拒絕編輯。完成修改後盡快 Commit &amp; Push 以釋放鎖定。</p>
</div>

<h2>1. One-time setup (each machine)</h2>

<div class="step">
<h3>1.1 Verify Git LFS is installed</h3>
<pre><code>git lfs version</code></pre>
<p>Expected: <code>git-lfs/3.x.x</code>. If missing: install from <a href="https://git-lfs.com">git-lfs.com</a>, then <code>git lfs install</code>.</p>
</div>

<div class="step">
<h3>1.2 Pull the updated .gitattributes (after this commit is pushed)</h3>
<pre><code>git pull</code></pre>
<p>The <code>.gitattributes</code> now marks all game binaries as <strong>lockable</strong>. Then force LFS to re-scan and make all existing files read-only:</p>
<pre><code>git lfs update</code></pre>
<p>Output should list every <code>.uasset</code> / <code>.umap</code> / <code>.png</code> switching to read-only. Verify:</p>
<pre><code>git lfs lock --list</code>
attrib +R Content\DontTrustTheLevels\Player\Blueprints\BP_Player.uasset &amp; rem check read-only flag
</pre>
<p>Or in Explorer: right-click any <code>.uasset</code> → Properties → <strong>Read-only</strong> should be ticked.</p>
</div>

<div class="step">
<h3>1.3 Connect UE4 to Source Control (each editor session, persists in project)</h3>
<ol>
<li>Unreal Editor → top-right <strong>Source Control</strong> icon → <strong>Connect to Source Control</strong></li>
<li>Provider: <strong>Git</strong></li>
<li>Repository: auto-detected (<code>C:\dtl</code>) · User Name: <strong>your GitHub username</strong></li>
<li>✓ <strong>Use Git LFS Locking (required for collaborative workflow)</strong> ← <em>this is the critical checkbox</em></li>
<li>Accept Settings → status icon turns green</li>
</ol>
<p>After connecting, Content Browser icons: <span style="color:#2f9f5f">●</span> green padlock = locked by <strong>you</strong> (editable) · <span style="color:#d93025">●</span> red padlock = locked by <strong>someone else</strong> (read-only, editor refuses changes) · no padlock = not locked.</p>
</div>

<h2>2. How it works day-to-day</h2>

<table>
<tr><th>Step</th><th>What happens</th><th>Who does what</th></tr>
<tr><td>1. Pull</td><td>All LFS files flip to <strong>read-only</strong></td><td>automatic</td></tr>
<tr><td>2. Edit a blueprint</td><td>Editor sends a <strong>lock request</strong> to GitHub the moment you change something; on success the file unlocks locally</td><td>automatic (with Source Control connected)</td></tr>
<tr><td>3. Teammate edits the same file</td><td>Their editor shows <strong>red warning and refuses</strong> — the file stays read-only</td><td>automatic</td></tr>
<tr><td>4. Commit &amp; push</td><td>Your lock is <strong>released</strong> when the commit that includes the file is pushed</td><td>you, ASAP after testing</td></tr>
</table>

<div class="warn">
<strong>⚠️ Locks are per-file and per-person.</strong> Lock what you edit, release what you finish. Do not hold locks overnight after you've pushed — push releases them automatically, but if you edited without pushing, run <code>git lfs locks</code> to check what you're holding.
</div>

<h2>3. Manual lock commands (fallback / power users)</h2>

<pre><code>git lfs locks                          :: see all locks (who holds what)
git lfs lock Content/DontTrustTheLevels/Player/Blueprints/BP_Player.uasset
git lfs unlock Content/DontTrustTheLevels/Player/Blueprints/BP_Player.uasset
git lfs unlock --id=123                :: unlock by lock ID (admin/unlock)
</code></pre>

<h2>4. Rules for the team</h2>

<div class="ok">
<ul>
<li><strong>One pillar = one folder = one owner.</strong> The lock system is the safety net, not an excuse to co-edit assets.</li>
<li><strong>Connect Source Control BEFORE editing.</strong> If the lock icon doesn't appear when you edit a blueprint, your changes are unprotected — stop, connect, retry.</li>
<li><strong>Commit &amp; push promptly after testing.</strong> Locks release on push; holding a lock for days blocks the team.</li>
<li><strong>Never edit .umap files you don't own.</strong> Level maps are the most-contested files; use per-person levels.</li>
<li><strong>Split logic into Actor Components.</strong> Avoid one giant player blueprint — separate components lock separately, so two people can work on the same character in parallel files.</li>
<li><strong>Editor closed before <code>git pull</code>.</strong> Read-only flags can't flip while UE4 holds file handles.</li>
</ul>
</div>

<h2>5. Troubleshooting</h2>

<table>
<tr><th>Symptom</th><th>Cause</th><th>Fix</th></tr>
<tr><td>Editor edits a file with no lock prompt</td><td>Source Control not connected, or "Use Git LFS Locking" unchecked</td><td>Reconnect with the Locking checkbox ✓</td></tr>
<tr><td>"File is read-only" when YOU try to save</td><td>Someone else holds the lock (red padlock)</td><td>Wait, or ask them to unlock; never attrib -R manually</td></tr>
<tr><td><code>git lfs lock</code> fails "not found"</td><td>File path typo or file not LFS-tracked</td><td>Check <code>git lfs ls-files | findstr filename</code></td></tr>
<tr><td>Push rejected "LFS lock verification failed"</td><td>You're pushing a file locked by someone else</td><td>Pull, coordinate, or <code>git lfs unlock --id=...</code> with their consent</td></tr>
<tr><td>Locks list shows stale locks</td><td>Push didn't include the file changes</td><td><code>git lfs unlock</code> the stale ones</td></tr>
</table>

<h2>6. What this repo now has (the actual config)</h2>

<pre><code>.gitattributes
  *.uasset  ... lockable
  *.umap    ... lockable
  *.png     ... lockable       (source art)
  *.psd     ... lockable
.lfsconfig [lfs]  locks.verify = true   (push refuses unlocked modified files)</code></pre>

<p>Source: <a href="https://github.com/git-lfs/git-lfs/blob/main/docs/locking.md">Git LFS locking docs</a> · UE4 Git LFS 2 setup: <a href="https://github.com/SRombauts/UE4GitPlugin">SRombauts/UE4GitPlugin</a></p>

</body>
</html>