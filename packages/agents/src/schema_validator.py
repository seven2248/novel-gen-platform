import json
from pathlib import Path
from jsonschema import validate, ValidationError


def load_schema(name: str):
    # __file__ = .../packages/agents/src/schema_validator.py
    # parent.parent = .../packages/agents/
    # contracts_dir = .../packages/contracts/
    # __file__ = .../packages/agents/src/schema_validator.py
    # parent = src/, parent.parent = agents/, parent.parent.parent = packages/
    # contracts is at packages/contracts (sibling to agents)
    contracts_dir = Path(__file__).parent.parent.parent / "contracts"
    path = contracts_dir / name
    if not path.exists():
        path = contracts_dir / "agent_io" / name
    if not path.exists():
        path = Path(name)
    if not path.exists():
        raise FileNotFoundError(f"Schema not found: {name} (tried {contracts_dir / name} and {contracts_dir / 'agent_io' / name})")
    return json.load(path.open(encoding="utf-8"))


def validate_payload(payload: dict, schema_name: str) -> tuple[bool, str]:
    try:
        schema = load_schema(schema_name)
        validate(instance=payload, schema=schema)
        return True, ""
    except ValidationError as e:
        return False, str(e.message)
    except (json.JSONDecodeError, OSError) as e:
        # OSError covers FileNotFoundError, PermissionError, etc.
        return False, str(e)
    # 不捕获其他 Exception，让编程错误（TypeError、AttributeError 等）正常上抛
