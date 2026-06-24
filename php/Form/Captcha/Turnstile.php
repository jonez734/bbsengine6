<?php

declare(strict_types=1);

namespace bbsengine6\Form\Captcha;

class Turnstile implements CaptchaProvider
{
    public function getSiteKey(): string
    {
        if (defined('config\TURNSTILE_SITE_KEY')) {
            return (string) constant('config\TURNSTILE_SITE_KEY');
        }
        if (defined('TURNSTILE_SITE_KEY')) {
            return (string) TURNSTILE_SITE_KEY;
        }
        return getenv('TURNSTILE_SITE_KEY') ?: '';
    }

    public function getSecretKey(): string
    {
        if (defined('config\TURNSTILE_SECRET_KEY')) {
            return (string) constant('config\TURNSTILE_SECRET_KEY');
        }
        if (defined('TURNSTILE_SECRET_KEY')) {
            return (string) TURNSTILE_SECRET_KEY;
        }
        return getenv('TURNSTILE_SECRET_KEY') ?: '';
    }

    public function render(): string
    {
        $siteKey = $this->getSiteKey();
        if ($siteKey === '') {
            return '';
        }

        return '<div class="cf-turnstile" data-sitekey="' . htmlspecialchars($siteKey) . '"></div>';
    }

    public function verify(string $token): bool
    {
        $secretKey = $this->getSecretKey();
        if ($secretKey === '' || $token === '') {
            return false;
        }

        $ch = curl_init();
        curl_setopt($ch, CURLOPT_URL, 'https://challenges.cloudflare.com/turnstile/v0/siteverify');
        curl_setopt($ch, CURLOPT_POST, true);
        curl_setopt($ch, CURLOPT_POSTFIELDS, http_build_query([
            'secret' => $secretKey,
            'response' => $token,
            'remoteip' => $_SERVER['REMOTE_ADDR'] ?? '',
        ]));
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        
        $response = curl_exec($ch);
        curl_close($ch);

        if ($response === false) {
            return false;
        }

        $result = json_decode($response, true);
        return isset($result['success']) && $result['success'] === true;
    }

    public function getTokenName(): string
    {
        return 'cf-turnstile-response';
    }
}
