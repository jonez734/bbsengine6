<?php

declare(strict_types=1);

namespace bbsengine6\Form\Rule;

abstract class Rule
{
    protected string $message;
    protected mixed $options = null;

    public function __construct(string $message, mixed $options = null)
    {
        $this->message = $message;
        $this->options = $options;
    }

    public function getMessage(): string
    {
        return $this->message;
    }

    public function getOptions(): mixed
    {
        return $this->options;
    }

    abstract public function validate(mixed $value, array $formValues = []): bool;
}
