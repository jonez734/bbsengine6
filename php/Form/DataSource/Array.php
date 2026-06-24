<?php

declare(strict_types=1);

namespace bbsengine6\Form\DataSource;

class ArrayDataSource
{
    protected array $data;

    public function __construct(array $data = [])
    {
        $this->data = $data;
    }

    public function getArray(): array
    {
        return $this->data;
    }

    public function hasValue(string $name): bool
    {
        return isset($this->data[$name]);
    }

    public function getValue(string $name): mixed
    {
        return $this->data[$name] ?? null;
    }
}
