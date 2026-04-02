import inspect

tools_schema = []

tools = set()

TYPE_MAP = {
    str: "string",
    float: "number",
    int: "number",
    bool: "boolean",
    list: "array",
    dict: "object"
}

def tool(func):
    sig = inspect.signature(func)
    properties = {}
    required = []
    description, param_descriptions = parse_docstring(func)

    for name, param in sig.parameters.items():
        if name == "self":  # skip
            continue
        hint = func.__annotations__.get(name, str)
        properties[name] = {
            "type": TYPE_MAP.get(hint, "string"),
            "description": param_descriptions.get(name, "")
        }
        if param.default is inspect.Parameter.empty:
            required.append(name)

    # outside the loop
    tools_schema.append({
        "name": func.__name__,
        "description": description,
        "input_schema": {
            "type": "object",
            "properties": properties,
            "required": required
        }
    })

    tools.add(func.__name__)

    return func


def parse_docstring(func):
    doc = func.__doc__ or ""
    lines = doc.strip().splitlines()

    description = []
    param_descriptions = {}
    in_args = False

    for line in lines:
        line = line.strip()
        if line == "Args:":
            in_args = True
        elif line in ("Returns:", "Raises:"):
            in_args = False
        elif in_args and ":" in line:
            name, desc = line.split(":", 1)
            param_descriptions[name.strip()] = desc.strip()
        elif not in_args and line:
            description.append(line)

    return " ".join(description), param_descriptions
