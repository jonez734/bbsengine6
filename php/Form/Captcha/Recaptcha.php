<?php

declare(strict_types=1);

namespace bbsengine6\Form\Captcha;

class Recaptcha implements CaptchaProvider
{
    public function getSiteKey(): string
    {
        if (defined('config\RECAPTCHA_SITE_KEY')) {
            return (string) constant('config\RECAPTCHA_SITE_KEY');
        }
        if (defined('RECAPTCHA_SITE_KEY')) {
            return (string) RECAPTCHA_SITE_KEY;
        }
        if (defined('RECAPTCHASITEKEY')) {
            return (string) RECAPTCHASITEKEY;
        }
        return getenv('RECAPTCHA_SITE_KEY') ?: '';
    }

    public function getSecretKey(): string
    {
        if (defined('config\RECAPTCHA_SECRET_KEY')) {
            return (string) constant('config\RECAPTCHA_SECRET_KEY');
        }
        if (defined('RECAPTCHA_SECRET_KEY')) {
            return (string) RECAPTCHA_SECRET_KEY;
        }
        if (defined('RECAPTCHASECRETKEY')) {
            return (string) RECAPTCHASECRETKEY;
        }
        return getenv('RECAPTCHA_SECRET_KEY') ?: '';
    }

    public function render(): string
    {
        $siteKey = $this->getSiteKey();
        if ($siteKey === '') {
            return '';
        }

        return '<div class="g-recaptcha" data-sitekey="' . htmlspecialchars($siteKey) . '"></div>';
    }

    public function verify(string $token): bool
    {
        $secretKey = $this->getSecretKey();
        if ($secretKey === '' || $token === '') {
            return false;
        }

        $ch = curl_init();
        curl_setopt($ch, CURLOPT_URL, 'https://www.google.com/recaptcha/api/siteverify');
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
        return 'g-recaptcha-response';
    }
}
