<?php
// applejr_sync_config.php - Rename to this and set your values
// DO NOT COMMIT THIS FILE IF USING VERSION CONTROL

return [
    'github_token' => getenv('GITHUB_TOKEN') ?: 'YOUR_PAT_TOKEN_HERE',
    'github_owner' => 'Sorav123',
    'github_repo'  => 'Certs',
    'github_branch'=> 'main',

    'site_url'     => 'https://applejr.net',
    'new_password' => 'godripyt',
    'source_link'  => 'https://hindipanchangtoday.com/hpt-tool',

    'password_candidates' => ['1', 'AppleP12.com', 'applejr.net'],

    'state_file' => __DIR__ . '/applejr_sync_state.json',
];