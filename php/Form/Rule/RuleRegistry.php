<?php

declare(strict_types=1);

namespace bbsengine6\Form\Rule;

class RuleRegistry
{
    private static array $rules = [];

    public static function register(string $name, string $class): void
    {
        self::$rules[$name] = $class;
    }

    public static function resolve(string $name): string
    {
        if (isset(self::$rules[$name])) {
            return self::$rules[$name];
        }

        return self::getBuiltIn($name);
    }

    public static function getBuiltIn(string $name): string
    {
        return match ($name) {
            'required' => Required::class,
            'callback' => Callback::class,
            'regex' => Regex::class,
            'eq' => Equals::class,
            'nonempty' => NonEmpty::class,
            default => throw new \InvalidArgumentException("Unknown rule: $name"),
        };
    }

    public static function isRegistered(string $name): bool
    {
        return isset(self::$rules[$name]);
    }

    public static function getRegistered(): array
    {
        return array_keys(self::$rules);
    }
}
