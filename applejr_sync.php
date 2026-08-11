<?php
/**
 * AppleJr Sync Script
 *
 * Scrapes applejr.net for Esign, Ksign, Scarlet IPA tool plists and Cert zips,
 * re-encrypts P12 certs with new password, and pushes changes to GitHub.
 *
 * Requirements: PHP 8.x, curl, zip, openssl extensions
 * Run via cron: 0 6 * * * php /path/to/applejr_sync.php
 */

// ─── Config: env vars first, config file as fallback ─────────────────────────
$cfg = [];
$cfgFile = __DIR__ . '/applejr_sync_config.php';
if (file_exists($cfgFile)) {
    $fileCfg = require $cfgFile;
    if (is_array($fileCfg)) $cfg = $fileCfg;
}

function cfgGet(array $cfg, string $key, string $env, string $default = ''): string
{
    $v = getenv($env);
    if ($v !== false && $v !== '') return $v;
    return isset($cfg[$key]) && $cfg[$key] !== '' ? (string)$cfg[$key] : $default;
}

define('GITHUB_TOKEN',   cfgGet($cfg, 'github_token',    'GH_TOKEN'));
define('GITHUB_OWNER',   cfgGet($cfg, 'github_owner',    'GH_OWNER',   'Sorav123'));
define('GITHUB_REPO',    cfgGet($cfg, 'github_repo',     'GH_REPO',    'Certs'));
define('GITHUB_BRANCH',  cfgGet($cfg, 'github_branch',   'GH_BRANCH',  'main'));

define('SITE_URL',       cfgGet($cfg, 'site_url',        'GH_SITE',    'https://applejr.net'));
define('NEW_PASSWORD',   cfgGet($cfg, 'new_password',    'GH_NEWPASS', 'godripyt'));
define('SOURCE_LINK',    cfgGet($cfg, 'source_link',     'GH_SOURCE',  'https://hindipanchangtoday.com/hpt-tool'));

$candidates = getenv('GH_PASSWORDS');
define('PASS_CANDIDATES', $candidates !== false && $candidates !== ''
    ? array_map('trim', explode(',', $candidates))
    : (isset($cfg['password_candidates']) ? $cfg['password_candidates'] : ['1', 'AppleP12.com', 'applejr.net']));

$statePath = getenv('GH_STATE') ?: ($cfg['state_file'] ?? (__DIR__ . '/applejr_sync_state.json'));
define('STATE_FILE', $statePath);

// Section selectors on the page (cat-list div IDs)
define('SECTIONS', [
    'esign'  => 'cat-esign',
    'ksign'  => 'cat-zsign',
    'scarlet' => 'cat-scarlet',
    'certs'  => 'cat-certificate',
]);

// ─── Bootstrap ────────────────────────────────────────────────────────────────
error_reporting(E_WARNING);
ini_set('display_errors', 0);
ini_set('max_execution_time', 300);

$state = loadState();

$html = fetchUrl(SITE_URL);
if (!$html) {
    logMsg('Failed to fetch homepage');
    exit(1);
}

$dom = new DOMDocument();
@$dom->loadHTML('<?xml encoding="UTF-8">' . $html, LIBXML_NOERROR);
$xpath = new DOMXPath($dom);

$total = 0;

foreach (SECTIONS as $folder => $sectionId) {
    $node = $xpath->query("//*[@id='{$sectionId}']")->item(0);
    if (!$node) {
        logMsg("Section #{$sectionId} not found, skipping");
        continue;
    }

    $cards = $xpath->query('.//div[contains(concat(" ", normalize-space(@class), " "), " card ")]', $node);
    logMsg("[" . strtoupper($folder) . "] Found " . $cards->length . " entries");

    foreach ($cards as $card) {
        $name = trim($xpath->evaluate('string(.//h3)', $card));

        $badge = $xpath->query('.//a[contains(@class,"badge")]', $card)->item(0);
        if (!$badge) continue;
        $link = $badge->getAttribute('href');
        if (!$link) continue;

        $meta = trim($xpath->evaluate('string(.//small[@class="meta"])', $card));
        // extract provider from "DNS • Provider"
        $provider = '';
        if (preg_match('/DNS\s*•\s*(.+)/i', $meta, $m)) {
            $provider = trim($m[1]);
        }

        if ($folder === 'certs') {
            if (processCertZip($link, $name, $provider)) $total++;
        } else {
            if (processPlist($link, $name, $provider, $folder)) $total++;
        }
    }
}

logMsg("Done. {$total} files processed this run.");

// ─── Plist processing ─────────────────────────────────────────────────────────
function processPlist(string $installLink, string $name, string $provider, string $folder): bool
{
    global $state;

    $plistUrl = extractPlistUrl($installLink);
    if (!$plistUrl) {
        logMsg("  [SKIP] {$name}: cannot extract plist URL from: {$installLink}");
        return false;
    }

    $slug = sanitizeFilename($name . '_' . $provider);
    $filename = "{$slug}.plist";
    $destPath = "{$folder}/{$filename}";
    $stateKey = "plist:{$folder}/{$filename}";

    $plistContent = fetchUrl($plistUrl);
    if (!$plistContent) {
        logMsg("  [SKIP] {$name}: failed to download plist");
        return false;
    }

    $sha = hash('sha256', $plistContent);
    if (isset($state[$stateKey]) && $state[$stateKey]['sha'] === $sha) {
        logMsg("  [OK] {$name}: unchanged");
        return false;
    }

    $ok = pushFile($destPath, base64_encode($plistContent), "Add {$name} ({$provider}) plist from AppleJr");
    if ($ok) {
        $state[$stateKey] = ['sha' => $sha, 'updated' => date('c')];
        saveState($state);
        logMsg("  [NEW] {$name}: pushed to {$folder}/{$filename}");
    }
    return $ok;
}

// ─── Cert processing ──────────────────────────────────────────────────────────
function processCertZip(string $zipUrl, string $certName, string $provider): bool
{
    global $state;

    $stateKey = "cert:" . md5($zipUrl);

    // Download zip
    $zipData = fetchUrl($zipUrl);
    if (!$zipData) {
        logMsg("  [SKIP] {$certName}: failed to download zip");
        return false;
    }

    $zipPath = sys_get_temp_dir() . '/applejr_cert_' . md5($zipUrl) . '.zip';
    file_put_contents($zipPath, $zipData);

    $zip = new ZipArchive();
    if ($zip->open($zipPath) !== true) {
        logMsg("  [SKIP] {$certName}: invalid zip");
        @unlink($zipPath);
        return false;
    }

    $workDir = sys_get_temp_dir() . '/applejr_cert_' . md5($zipUrl);
    if (is_dir($workDir)) {
        rrmdir($workDir);
    }
    mkdir($workDir, 0755, true);
    $zip->extractTo($workDir);
    $zip->close();
    @unlink($zipPath);

    // Find files
    $p12File = null;
    $mobileFile = null;
    $txtPassword = null;

    $iter = new RecursiveIteratorIterator(new RecursiveDirectoryIterator($workDir));
    foreach ($iter as $file) {
        if ($file->isDir()) continue;
        $ext = strtolower(pathinfo($file->getFilename(), PATHINFO_EXTENSION));
        if ($ext === 'p12' && !$p12File) {
            $p12File = $file->getPathname();
        } elseif ($ext === 'mobileprovision' && !$mobileFile) {
            $mobileFile = $file->getPathname();
        } elseif (in_array($ext, ['txt', 'text']) && !$txtPassword) {
            $txtPassword = $file->getPathname();
        }
    }

    if (!$p12File || !$mobileFile) {
        logMsg("  [SKIP] {$certName}: missing p12(" . ($p12File ? 'ok' : 'MISSING') . ") or mobileprovision(" . ($mobileFile ? 'ok' : 'MISSING') . ")");
        rrmdir($workDir);
        return false;
    }

    // Discover password
    $oldPassword = null;

    foreach (PASS_CANDIDATES as $candidate) {
        if (testP12Password($p12File, $candidate)) {
            $oldPassword = $candidate;
            logMsg("  [PASS] {$certName}: found password via candidate: {$candidate}");
            break;
        }
    }

    if (!$oldPassword && $txtPassword) {
        $filePass = trim(file_get_contents($txtPassword));
        // Extract just the first word (skip binary junk from resource forks)
        if (preg_match('/^([a-zA-Z0-9._-]+)/', $filePass, $m)) {
            $filePass = $m[1];
        }
        if ($filePass && testP12Password($p12File, $filePass)) {
            $oldPassword = $filePass;
            logMsg("  [PASS] {$certName}: found password via txt file: {$filePass}");
            // Save discovered password for future use
            saveDiscoveredPassword($filePass);
        }
    }

    if (!$oldPassword) {
        logMsg("  [SKIP] {$certName}: could not crack password");
        rrmdir($workDir);
        return false;
    }

    // Re-encrypt P12 with new password
    $newP12Path = $workDir . '/new_cert.p12';
    if (!reencryptP12($p12File, $oldPassword, $newP12Path, NEW_PASSWORD)) {
        logMsg("  [SKIP] {$certName}: P12 re-encryption failed");
        rrmdir($workDir);
        return false;
    }

    // Remove original P12, replace with re-encrypted version
    @unlink($p12File);
    $newP12Name = pathinfo($p12File, PATHINFO_FILENAME) . '.p12';
    $destP12 = dirname($p12File) . '/' . $newP12Name;
    rename($newP12Path, $destP12);

    // Create new password.txt (overwrite original)
    $pwdTxtPath = dirname($p12File) . '/password.txt';
    @unlink($pwdTxtPath); // remove any existing password file
    $pwdContent = "Password : " . NEW_PASSWORD . "\nSource   : " . SOURCE_LINK . "\n";
    file_put_contents($pwdTxtPath, $pwdContent);

    // Remove __MACOSX junk
    rrmdir($workDir . '/__MACOSX');

    // Remove any leftover non-p12, non-mobileprovision, non-txt files
    $cleanIter = new RecursiveIteratorIterator(
        new RecursiveDirectoryIterator($workDir, RecursiveDirectoryIterator::SKIP_DOTS),
        RecursiveIteratorIterator::CHILD_FIRST
    );
    foreach ($cleanIter as $file) {
        if ($file->isDir()) continue;
        $ext = strtolower(pathinfo($file->getFilename(), PATHINFO_EXTENSION));
        $name = $file->getFilename();
        if (!in_array($ext, ['p12', 'mobileprovision', 'txt']) && $name !== '.DS_Store') {
            @unlink($file->getPathname());
        }
    }

    // Build output zip
    $outZipPath = sys_get_temp_dir() . '/applejr_out_' . md5($zipUrl) . '.zip';
    $outZip = new ZipArchive();
    $outZip->open($outZipPath, ZipArchive::CREATE | ZipArchive::OVERWRITE);

    $outFiles = new RecursiveIteratorIterator(new RecursiveDirectoryIterator($workDir, RecursiveDirectoryIterator::SKIP_DOTS));
    foreach ($outFiles as $file) {
        if ($file->isDir()) continue;
        $name = $file->getFilename();
        if ($name === '.DS_Store') continue;
        // flatten: just use filename, no subdirectories
        $outZip->addFile($file->getPathname(), $name);
    }
    $outZip->close();

    $outContent = file_get_contents($outZipPath);
    $outSha = hash('sha256', $outContent);

    if (isset($state[$stateKey]) && $state[$stateKey]['sha'] === $outSha) {
        logMsg("  [OK] {$certName}: output zip unchanged");
        rrmdir($workDir);
        @unlink($outZipPath);
        return false;
    }

    $slug = sanitizeFilename($certName);
    $destPath = "Certs/{$slug}.zip";

    $ok = pushFile($destPath, base64_encode($outContent), "Add/update cert: {$certName} (password changed) from AppleJr");
    if ($ok) {
        $state[$stateKey] = ['sha' => $outSha, 'updated' => date('c'), 'pushed' => true];
        saveState($state);
        logMsg("  [NEW] {$certName}: pushed to {$destPath}");
    }

    rrmdir($workDir);
    @unlink($outZipPath);
    return $ok;
}

// ─── P12 helpers ──────────────────────────────────────────────────────────────
function testP12Password(string $path, string $password): bool
{
    $certs = [];
    $ok = @openssl_pkcs12_read(file_get_contents($path), $certs, $password);
    return $ok === true;
}

function reencryptP12(string $srcPath, string $oldPass, string $destPath, string $newPass): bool
{
    $p12Data = file_get_contents($srcPath);
    $certs = [];

    if (!@openssl_pkcs12_read($p12Data, $certs, $oldPass)) {
        return false;
    }

    $out = '';
    // Re-export with new password. Preserve CA certs if present.
    $args = ['friendly_name' => 'cert'];
    if (isset($certs['ca']) && $certs['ca']) {
        $args['extracerts'] = $certs['ca'];
    }

    $ok = @openssl_pkcs12_export($certs['cert'], $out, $certs['pkey'], $newPass, $args);

    if ($ok) {
        file_put_contents($destPath, $out);
    }
    return $ok;
}

// ─── URL extraction ───────────────────────────────────────────────────────────
function extractPlistUrl(string $link): ?string
{
    if (preg_match('/url=([^&]+)/i', $link, $m)) {
        $url = urldecode($m[1]);
        return filter_var($url, FILTER_VALIDATE_URL) ? $url : null;
    }
    return null;
}

// ─── GitHub API ───────────────────────────────────────────────────────────────
function pushFile(string $path, string $b64Content, string $message): bool
{
    $url = "https://api.github.com/repos/" . GITHUB_OWNER . "/" . GITHUB_REPO . "/contents/" . $path;
    $headers = [
        "Authorization: Bearer " . GITHUB_TOKEN,
        "Accept: application/vnd.github.v3+json",
        "User-Agent: AppleJr-Sync/1.0",
    ];

    // Check if file exists
    $existingSha = null;
    $ch = curl_init($url);
    curl_setopt_array($ch, [
        CURLOPT_HTTPHEADER => $headers,
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_CUSTOMREQUEST => 'GET',
    ]);
    $resp = curl_exec($ch);
    $code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);

    if ($code === 200) {
        $json = json_decode($resp, true);
        if (isset($json['sha'])) {
            $existingSha = $json['sha'];
        }
    }

    // Create/update
    $body = [
        'message' => $message,
        'content' => $b64Content,
        'branch' => GITHUB_BRANCH,
    ];
    if ($existingSha) {
        $body['sha'] = $existingSha;
    }

    $ch = curl_init($url);
    curl_setopt_array($ch, [
        CURLOPT_HTTPHEADER => array_merge($headers, ['Content-Type: application/json']),
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_CUSTOMREQUEST => 'PUT',
        CURLOPT_POSTFIELDS => json_encode($body),
    ]);
    $resp = curl_exec($ch);
    $code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);

    if ($code >= 200 && $code < 300) {
        return true;
    }

    logMsg("  [ERR] GitHub push failed ({$code}): " . substr($resp, 0, 200));
    return false;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────
function normalizeGitHubUrl(string $url): string
{
    // Convert github.com/owner/repo/blob/main/path -> raw.githubusercontent.com/owner/repo/main/path
    if (preg_match('#^https://github\.com/([^/]+)/([^/]+)/blob/(.+)$#', $url, $m)) {
        return "https://raw.githubusercontent.com/{$m[1]}/{$m[2]}/{$m[3]}";
    }
    return $url;
}

function fetchUrl(string $url): ?string
{
    $url = normalizeGitHubUrl($url);
    $ch = curl_init($url);
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_FOLLOWLOCATION => true,
        CURLOPT_TIMEOUT => 60,
        CURLOPT_USERAGENT => 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    ]);
    $data = curl_exec($ch);
    $code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    if ($code !== 200 || !$data) {
        return null;
    }
    return $data;
}

function sanitizeFilename(string $name): string
{
    $name = preg_replace('/[^\w\s.-]/', '', $name);
    $name = preg_replace('/\s+/', '_', trim($name));
    return $name;
}

function loadState(): array
{
    if (file_exists(STATE_FILE)) {
        return json_decode(file_get_contents(STATE_FILE), true) ?: [];
    }
    return [];
}

function saveState(array $state): void
{
    file_put_contents(STATE_FILE, json_encode($state, JSON_PRETTY_PRINT));
}

function logMsg(string $msg): void
{
    echo date('[Y-m-d H:i:s] ') . $msg . "\n";
    error_log(date('[Y-m-d H:i:s] ') . $msg . "\n");
}

function rrmdir(string $dir): void
{
    if (!is_dir($dir)) return;
    $it = new RecursiveIteratorIterator(
        new RecursiveDirectoryIterator($dir, RecursiveDirectoryIterator::SKIP_DOTS),
        RecursiveIteratorIterator::CHILD_FIRST
    );
    foreach ($it as $file) {
        $file->isDir() ? @rmdir($file->getPathname()) : @unlink($file->getPathname());
    }
    @rmdir($dir);
}

function saveDiscoveredPassword(string $password): void
{
    $passFile = __DIR__ . '/discovered_passwords.txt';
    $existing = file_exists($passFile) ? file_get_contents($passFile) : '';
    $lines = array_filter(array_map('trim', explode("\n", $existing)));
    if (!in_array($password, $lines)) {
        $lines[] = $password;
        file_put_contents($passFile, implode("\n", $lines) . "\n");
    }
}
