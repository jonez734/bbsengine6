<?php

declare(strict_types=1);

namespace bbsengine6\Form\Rule;

class Equals extends Rule
{
    public function validate(mixed $value, array $formValues = []): bool
    {
        $compareTo = $this->options;

        if ($compareTo instanceof \bbsengine6\Form\Element) {
            $compareValue = $compareTo->getValue();
        } elseif (is_string($compareTo) && isset($formValues[$compareTo])) {
            $compareValue = $formValues[$compareTo];
        } else {
            $compareValue = $compareTo;
        }

        return $value === $compareValue;
    }
}
