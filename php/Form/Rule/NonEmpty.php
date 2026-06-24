<?php

declare(strict_types=1);

namespace bbsengine6\Form\Rule;

class NonEmpty extends Rule
{
    public function validate(mixed $value, array $formValues = []): bool
    {
        if ($value === null || $value === '') {
            return false;
        }

        if (is_string($value)) {
            return trim($value) !== '';
        }

        if (is_array($value)) {
            return count($value) > 0;
        }

        return true;
    }
}
