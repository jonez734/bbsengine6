

def mainproto(something, **kwargs):
    pass


import inspect


def func_example(a, b: int, *, c: str, **kwargs) -> None:
    pass


sig = inspect.signature(func_example)

for name, param in sig.parameters.items():
    print(f"Parameter: {name}")
    print(f"  Kind: {param.kind}")
    print(
        f"  Annotation: {param.annotation if param.annotation != inspect.Parameter.empty else 'No annotation'}"
    )
    print(
        f"  Default: {param.default if param.default != inspect.Parameter.empty else 'No default'}\n"
    )

# module.validate_function("func_example", "main", mainsig)
