"""
RED phase tests for task 2.3 — written before migration/fixture files existed.
test_initial_migration_exists and test_fixture_* are pure Python (no Django runtime).
test_migration_imports_cleanly requires Django installed (skipped in greenfield env).
"""
import json
from pathlib import Path


def test_initial_migration_exists():
    migration_path = Path(__file__).parent.parent / 'migrations' / '0001_initial.py'
    assert migration_path.exists(), "0001_initial.py must exist in migrations/"


def test_fixture_initial_plans_exists():
    fixture_path = Path(__file__).parent.parent / 'fixtures' / 'initial_plans.json'
    assert fixture_path.exists(), "initial_plans.json must exist in fixtures/"


def test_fixture_has_trial_and_enterprise():
    fixture_path = Path(__file__).parent.parent / 'fixtures' / 'initial_plans.json'
    data = json.loads(fixture_path.read_text())
    nombres = [item['fields']['nombre'] for item in data]
    assert 'trial' in nombres
    assert 'enterprise' in nombres
    assert len(data) == 2, f"Expected 2 plan records, got {len(data)}"


def test_fixture_model_label_is_tenants_plan():
    fixture_path = Path(__file__).parent.parent / 'fixtures' / 'initial_plans.json'
    data = json.loads(fixture_path.read_text())
    for item in data:
        assert item['model'] == 'tenants.plan', f"Expected 'tenants.plan', got {item['model']}"


def test_migration_imports_cleanly():
    """Requires Django installed — skipped in greenfield environment."""
    try:
        import django  # noqa: F401
    except ImportError:
        import pytest
        pytest.skip("Django not installed in this environment")
    import importlib
    mod = importlib.import_module('apps.tenants.migrations.0001_initial')
    assert hasattr(mod, 'Migration')
