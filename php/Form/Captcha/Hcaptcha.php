<?php

declare(strict_types=1);

namespace bbsengine6\Form\Captcha;

class Hcaptcha implements CaptchaProvider
{
    public function getSiteKey(): string
    {
        if (defined('config\HCAPTCHA_SITE_KEY')) {
            return (string) constant('config\HCAPTCHA_SITE_KEY');
        }
        if (defined('HCAPTCHA_SITE_KEY')) {
            return (string) HCAPTCHA_SITE_KEY;
        }
        return getenv('HCAPTCHA_SITE_KEY') ?: '';
    }

    public function getSecretKey(): string
    {
        if (defined('config\HCAPTCHA_SECRET_KEY')) {
            return (string) constant('config\HCAPTCHA_SECRET_KEY');
        }
        if (defined('HCAPTCHA_SECRET_KEY')) {
            return (string) HCAPTCHA_SECRET_KEY;
        }
        return getenv('HCAPTCHA_SECRET_KEY') ?: '';
    }

    public function render(): string
    {
        $siteKey = $this->getSiteKey();
        if ($siteKey === '') {
            return '';
        }

        return '<div class="h-captcha" data-sitekey="' . htmlspecialchars($siteKey) . '"></div>';
    }

    public function verify(string $token): bool
    {
        $secretKey = $this->getSecretKey();
        if ($secretKey === '' || $token === '') {
            return false;
        }

        $ch = curl_init();
        curl_setopt($ch, CURLOPT_URL, 'https://hcaptcha.com/siteverify');
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
        return 'h-captcha-response';
    }
}
