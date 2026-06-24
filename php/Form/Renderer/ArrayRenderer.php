<?php

declare(strict_types=1);

namespace bbsengine6\Form\Renderer;

use bbsengine6\Form\Form;
use bbsengine6\Form\Element;

class ArrayRenderer
{
    protected array $options = [];
    protected array $output = [];

    public function __construct(array $options = [])
    {
        $this->options = array_merge([
            'group_errors' => true,
            'group_hiddens' => true,
            'required_note' => "<span class='requiredstar'>*</span> denotes required fields.",
        ], $options);
    }

    public function setOption(string $key, mixed $value): self
    {
        $this->options[$key] = $value;
        return $this;
    }

    public function getOption(string $key, mixed $default = null): mixed
    {
        return $this->options[$key] ?? $default;
    }

    public function render(Form $form): void
    {
        $this->output = [
            'id' => $form->getId(),
            'method' => $form->getMethod(),
            'attributes' => $form->getAttributes(),
            'elements' => [],
            'required_note' => $this->options['required_note'],
            'errors' => [],
        ];

        $hiddens = [];
        $regulars = [];

        foreach ($form->getElements() as $element) {
            $elementData = $this->renderElement($element);
            
            if ($element->getType() === 'hidden') {
                $hiddens[] = $elementData;
            } else {
                $regulars[] = $elementData;
            }
        }

        if ($this->options['group_hiddens'] && count($hiddens) > 0) {
            $this->output['hidden'] = $hiddens;
        } else {
            $this->output['elements'] = array_merge($this->output['elements'], $hiddens);
        }

        $this->output['elements'] = array_merge($this->output['elements'], $regulars);

        $errors = $form->getErrors();
        if ($this->options['group_errors'] && count($errors) > 0) {
            $this->output['errors'] = $errors;
        }
    }

    protected function renderElement(Element $element): array
    {
        $data = [
            'name' => $element->getName(),
            'type' => $element->getType(),
            'label' => $element->getLabel(),
            'value' => $element->getValue(),
            'attributes' => $element->getAttributes(),
            'frozen' => $element->isFrozen(),
        ];

        $error = $element->getError();
        if ($error !== null) {
            $data['error'] = $error;
        }

        if ($element->getType() === 'fieldset') {
            $data['elements'] = [];
            foreach ($element->getElements() as $child) {
                $data['elements'][] = $this->renderElement($child);
            }
        }

        return $data;
    }

    public function toArray(): array
    {
        return $this->output;
    }

    public static function create(array $options = []): self
    {
        return new self($options);
    }
}
