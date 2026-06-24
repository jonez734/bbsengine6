<?php

declare(strict_types=1);

namespace bbsengine6\Form\Captcha;

interface CaptchaProvider
{
    public function getSiteKey(): string;
    
    public function getSecretKey(): string;
    
    public function render(): string;
    
    public function verify(string $token): bool;
}
