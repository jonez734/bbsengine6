<?php

declare(strict_types=1);

namespace bbsengine6\Form\Captcha;

class None implements CaptchaProvider
{
    public function getSiteKey(): string
    {
        return '';
    }

    public function getSecretKey(): string
    {
        return '';
    }

    public function render(): string
    {
        return '';
    }

    public function verify(string $token): bool
    {
        return true;
    }
}
