<?php

declare(strict_types=1);

namespace bbsengine6\Form\Captcha;

class Factory
{
    private static ?CaptchaProvider $provider = null;
    private static ?string $currentProviderName = null;

    public static function create(string $providerName = null): CaptchaProvider
    {
        if ($providerName === null) {
            $providerName = self::getConfigProvider();
        }

        if (self::$currentProviderName === $providerName && self::$provider !== null) {
            return self::$provider;
        }

        self::$currentProviderName = $providerName;

        self::$provider = match (strtolower($providerName)) {
            'turnstile' => new Turnstile(),
            'hcaptcha' => new Hcaptcha(),
            'recaptcha' => new Recaptcha(),
            'none' => new None(),
            default => new None(),
        };

        return self::$provider;
    }

    public static function setProvider(CaptchaProvider $provider): void
    {
        self::$provider = $provider;
    }

    private static function getConfigProvider(): string
    {
        if (defined('config\CAPTCHA_PROVIDER')) {
            return constant('config\CAPTCHA_PROVIDER');
        }

        if (defined('CAPTCHA_PROVIDER')) {
            return CAPTCHA_PROVIDER;
        }

        return 'none';
    }

    public static function getProviderName(): string
    {
        return self::$currentProviderName ?? self::getConfigProvider();
    }

    public static function isEnabled(): bool
    {
        $provider = self::create();
        return $provider->getSiteKey() !== '' && $provider->getSecretKey() !== '';
    }
}
