<?php

declare(strict_types=1);

namespace bbsengine6\Form;

use bbsengine6\Form\Rule\Rule;
use bbsengine6\Form\Rule\RuleRegistry;

class Element
{
    protected string $type;
    protected string $name;
    protected array $attributes = [];
    protected ?string $label = null;
    protected mixed $value = null;
    protected array $rules = [];
    protected ?Element $parent = null;
    protected array $elements = [];
    protected bool $frozen = false;

    public function __construct(string $type, string $name, array $attributes = [])
    {
        $this->type = $type;
        $this->name = $name;
        $this->attributes = $attributes;
    }

    public function getName(): string
    {
        return $this->name;
    }

    public function getType(): string
    {
        return $this->type;
    }

    public function setLabel(string $label): self
    {
        $this->label = $label;
        return $this;
    }

    public function getLabel(): ?string
    {
        return $this->label;
    }

    public function setValue(mixed $value): self
    {
        $this->value = $value;
        return $this;
    }

    public function getValue(): mixed
    {
        return $this->value;
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

    public function addRule(string $type, string $message, mixed $options = null): self
    {
        $class = RuleRegistry::resolve($type);
        $this->rules[] = new $class($message, $options);
        return $this;
    }

    public function getRules(): array
    {
        return $this->rules;
    }

    public function validate(array $formValues = []): bool
    {
        foreach ($this->rules as $rule) {
            if (!$rule->validate($this->value, $formValues)) {
                return false;
            }
        }
        return true;
    }

    public function getError(): ?string
    {
        foreach ($this->rules as $rule) {
            if (!$rule->validate($this->value, [])) {
                return $rule->getMessage();
            }
        }
        return null;
    }

    public function toggleFrozen(bool $frozen = true): void
    {
        $this->frozen = $frozen;
    }

    public function isFrozen(): bool
    {
        return $this->frozen;
    }

    public function addElement(string $type, string $name, array $attributes = []): self
    {
        $element = new Element($type, $name, $attributes);
        $element->parent = $this;
        $this->elements[] = $element;
        return $element;
    }

    public function getElements(): array
    {
        return $this->elements;
    }

    public function createRule(string $type, string $message, mixed $options = null): self
    {
        return $this->addRule($type, $message, $options);
    }

    public function setSeparator(string $separator): self
    {
        $this->attributes['separator'] = $separator;
        return $this;
    }

    public function addGroup(string $name, array $attributes = []): self
    {
        return $this->addElement('group', $name, $attributes);
    }

    public function toArray(): array
    {
        $result = [
            'name' => $this->name,
            'type' => $this->type,
            'value' => $this->value,
            'label' => $this->label,
            'attributes' => $this->attributes,
            'frozen' => $this->frozen,
        ];

        if (count($this->elements) > 0) {
            $result['elements'] = array_map(fn($e) => $e->toArray(), $this->elements);
        }

        return $result;
    }
}
