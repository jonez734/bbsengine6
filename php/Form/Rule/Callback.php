<?php

declare(strict_types=1);

namespace bbsengine6\Form\Rule;

class Callback extends Rule
{
    public function validate(mixed $value, array $formValues = []): bool
    {
        $callback = $this->options;

        if (is_string($callback) && function_exists($callback)) {
            if (is_array($formValues) && count($formValues) > 0) {
                return $callback($formValues);
            }
            return $callback($value);
        }

        if (is_callable($callback)) {
            if (is_array($formValues) && count($formValues) > 0) {
                return $callback($formValues);
            }
            return $callback($value);
        }

        return false;
    }
}
