<?php

declare(strict_types=1);

namespace bbsengine6\Form\Rule;

class Regex extends Rule
{
    public function validate(mixed $value, array $formValues = []): bool
    {
        if ($value === null || $value === '') {
            return true;
        }

        $pattern = $this->options;
        return is_string($value) && preg_match($pattern, $value) === 1;
    }
}
