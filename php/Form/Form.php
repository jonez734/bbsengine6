<?php

declare(strict_types=1);

namespace bbsengine6\Form;

use bbsengine6\Form\DataSource\ArrayDataSource;

class Form
{
    protected string $id;
    protected string $method;
    protected array $attributes = [];
    protected array $elements = [];
    protected array $dataSources = [];
    protected bool $frozen = false;
    protected array $values = [];

    public function __construct(string $id, string $method = 'post', mixed $attributes = [], bool $tracksubmit = true)
    {
        $this->id = $id;
        $this->method = strtolower($method);
        
        $defaults = [
            'id' => $id,
            'method' => $method,
            'enctype' => 'multipart/form-data',
        ];
        
        if (is_array($attributes)) {
            $this->attributes = array_merge($defaults, $attributes);
        } else {
            $this->attributes = $defaults;
        }
    }

    public function getId(): string
    {
        return $this->id;
    }

    public function getMethod(): string
    {
        return $this->method;
    }

    public function setAttribute(string $key, mixed $value): self
    {
        $this->attributes[$key] = $value;
        return $this;
    }

    public function getAttribute(string $key, mixed $default = null): mixed
    {
        return $this->attributes[$key] ?? $default;
    }

    public function getAttributes(): array
    {
        return $this->attributes;
    }

    public function addElement(string $type, string $name = null, array $attributes = []): Element
    {
        if ($name === null) {
            $name = $type . '_' . count($this->elements);
        }

        $element = new Element($type, $name, $attributes);
        $this->elements[] = $element;
        return $element;
    }

    public function addFieldset(string $name = null): Element
    {
        return $this->addElement('fieldset', $name ?? 'fieldset_' . count($this->elements));
    }

    public function addHidden(string $name, mixed $value = null): Element
    {
        $element = $this->addElement('hidden', $name);
        if ($value !== null) {
            $element->setValue($value);
        }
        return $element;
    }

    public function addDataSource(ArrayDataSource $dataSource): self
    {
        $this->dataSources[] = $dataSource;
        return $this;
    }

    public function getDataSourceValues(): array
    {
        $values = [];
        foreach ($this->dataSources as $ds) {
            foreach ($ds->getArray() as $key => $value) {
                $values[$key] = $value;
            }
        }
        return $values;
    }

    public function populateFromDataSources(): self
    {
        $values = $this->getDataSourceValues();
        foreach ($this->elements as $element) {
            $this->populateElement($element, $values);
        }
        return $this;
    }

    protected function populateElement(Element $element, array $values): void
    {
        if ($element->getType() === 'fieldset') {
            foreach ($element->getElements() as $child) {
                $this->populateElement($child, $values);
            }
        } else {
            $name = $element->getName();
            if (isset($values[$name])) {
                $element->setValue($values[$name]);
            }
        }
    }

    public function getElements(): array
    {
        return $this->elements;
    }

    public function isSubmitted(): bool
    {
        if ($this->method === 'post') {
            return $_SERVER['REQUEST_METHOD'] === 'POST' && 
                   isset($_POST[$this->id]) || count($_POST) > 0;
        }
        return false;
    }

    public function getValue(): array
    {
        if ($this->method === 'post') {
            return $_POST;
        }
        return $_GET;
    }

    public function validate(): bool
    {
        $values = $this->getValue();
        
        foreach ($this->elements as $element) {
            if (!$this->validateElement($element, $values)) {
                return false;
            }
        }

        return true;
    }

    protected function validateElement(Element $element, array $values): bool
    {
        $elementName = $element->getName();
        $value = $values[$elementName] ?? null;

        if ($element->getType() === 'fieldset') {
            foreach ($element->getElements() as $child) {
                if (!$this->validateElement($child, $values)) {
                    return false;
                }
            }
        } else {
            $element->setValue($value);
            if (!$element->validate($values)) {
                return false;
            }
        }

        return true;
    }

    public function getErrors(): array
    {
        $errors = [];
        
        foreach ($this->elements as $element) {
            $this->collectErrors($element, $errors);
        }

        return $errors;
    }

    protected function collectErrors(Element $element, array &$errors): void
    {
        $elementName = $element->getName();
        
        if ($element->getType() === 'fieldset') {
            foreach ($element->getElements() as $child) {
                $this->collectErrors($child, $errors);
            }
        } else {
            $error = $element->getError();
            if ($error !== null) {
                $errors[$elementName] = $error;
            }
        }
    }

    public function toggleFrozen(bool $frozen = true): void
    {
        $this->frozen = $frozen;
        foreach ($this->elements as $element) {
            $element->toggleFrozen($frozen);
        }
    }

    public function isFrozen(): bool
    {
        return $this->frozen;
    }

    public function addRecursiveFilter(string $filter): void
    {
        if ($filter === 'trim') {
            $values = $this->getValue();
            $this->values = $this->arrayMapRecursive(fn($v) => is_string($v) ? trim($v) : $v, $values);
        }
    }

    protected function arrayMapRecursive(callable $callback, array $array): array
    {
        foreach ($array as $key => $value) {
            if (is_array($value)) {
                $array[$key] = $this->arrayMapRecursive($callback, $value);
            } else {
                $array[$key] = $callback($value);
            }
        }
        return $array;
    }

    public function render($renderer): void
    {
        $renderer->render($this);
    }
}
