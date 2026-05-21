"""Unit tests for ScaffoldingInterface."""

import pytest

from pyclif import OperationResult
from pyclif.apps.project.interfaces import ScaffoldingInterface


@pytest.fixture
def iface(tmp_path):
    """ScaffoldingInterface rooted at tmp_path."""
    return ScaffoldingInterface(ctx=None, root=tmp_path)


@pytest.fixture
def project(tmp_path, monkeypatch):
    """A freshly initialised project in tmp_path."""
    monkeypatch.chdir(tmp_path)
    iface = ScaffoldingInterface(ctx=None)
    list(iface.init_project("my-app"))
    return ScaffoldingInterface(ctx=None, root=tmp_path / "my-app")


class TestNames:
    """Test suite for the _names helper."""

    def test_kebab_case(self) -> None:
        """Convert kebab-case to snake and pascal variants."""
        result = ScaffoldingInterface._names("ship-cli")
        assert result == {"name": "ship-cli", "name_snake": "ship_cli", "name_pascal": "ShipCli"}

    def test_snake_case(self) -> None:
        """Snake-case input passes through unchanged."""
        result = ScaffoldingInterface._names("my_app")
        assert result == {"name": "my_app", "name_snake": "my_app", "name_pascal": "MyApp"}

    def test_single_word(self) -> None:
        """Single word produces identical snake and lowercase pascal."""
        result = ScaffoldingInterface._names("github")
        assert result == {"name": "github", "name_snake": "github", "name_pascal": "Github"}


class TestInitProject:
    """Test suite for init_project."""

    def test_creates_expected_files(self, tmp_path, monkeypatch) -> None:
        """All project skeleton files are written."""
        monkeypatch.chdir(tmp_path)
        iface = ScaffoldingInterface(ctx=None)
        results = list(iface.init_project("my-app"))
        paths = {r.item for r in results}

        assert any("pyproject.toml" in p for p in paths)
        assert any("cli.py" in p for p in paths)
        assert any("context.py" in p for p in paths)
        assert any("conftest.py" in p for p in paths)

    def test_all_results_are_successful(self, tmp_path, monkeypatch) -> None:
        """init_project returns only successful results for a fresh project."""
        monkeypatch.chdir(tmp_path)
        iface = ScaffoldingInterface(ctx=None)
        results = list(iface.init_project("my-app"))
        assert all(r.success for r in results)
        assert all(isinstance(r, OperationResult) for r in results)

    def test_all_actions_are_created(self, tmp_path, monkeypatch) -> None:
        """init_project only creates files — no modified entries."""
        monkeypatch.chdir(tmp_path)
        iface = ScaffoldingInterface(ctx=None)
        results = list(iface.init_project("my-app"))
        assert all(r.data.get("action") == "created" for r in results)

    def test_returns_error_if_directory_exists(self, tmp_path, monkeypatch) -> None:
        """Second init with the same name returns a single error result."""
        monkeypatch.chdir(tmp_path)
        iface = ScaffoldingInterface(ctx=None)
        list(iface.init_project("my-app"))
        results = list(iface.init_project("my-app"))
        assert len(results) == 1
        assert not results[0].success
        assert "already exists" in results[0].message

    def test_uv_pyproject(self, tmp_path, monkeypatch) -> None:
        """uv template includes hatchling build backend."""
        monkeypatch.chdir(tmp_path)
        iface = ScaffoldingInterface(ctx=None)
        # noinspection PyArgumentEqualDefault
        list(iface.init_project("my-app", package_manager="uv"))
        content = (tmp_path / "my-app" / "pyproject.toml").read_text()
        assert "hatchling" in content
        assert "dependency-groups" in content

    def test_poetry_pyproject(self, tmp_path, monkeypatch) -> None:
        """poetry template includes poetry build backend."""
        monkeypatch.chdir(tmp_path)
        iface = ScaffoldingInterface(ctx=None)
        list(iface.init_project("my-app", package_manager="poetry"))
        content = (tmp_path / "my-app" / "pyproject.toml").read_text()
        assert "poetry-core" in content
        assert "tool.poetry" in content

    def test_returns_error_for_invalid_package_manager(self, tmp_path, monkeypatch) -> None:
        """Unsupported package manager returns a single error result."""
        monkeypatch.chdir(tmp_path)
        iface = ScaffoldingInterface(ctx=None)
        results = list(iface.init_project("my-app", package_manager="pipenv"))
        assert len(results) == 1
        assert not results[0].success
        assert "Unsupported package manager" in results[0].message


class TestAddApp:
    """Test suite for add_app."""

    def test_creates_app_files(self, project) -> None:
        """App skeleton files are written under apps/."""
        results = list(project.add_app("repos"))
        paths = {r.item for r in results}

        assert any("repos/__init__.py" in p for p in paths)
        assert any("repos/interfaces.py" in p for p in paths)
        assert any("repos/models.py" in p for p in paths)
        assert any("repos/tables.py" in p for p in paths)
        assert any("repos/commands/__init__.py" in p for p in paths)

    def test_wires_app_in_apps_init(self, project, tmp_path) -> None:
        """apps/__init__.py is updated with the new group import and list entry."""
        list(project.add_app("repos"))
        content = (tmp_path / "my-app" / "src" / "my_app" / "apps" / "__init__.py").read_text()
        assert "from .repos import repos" in content
        assert "groups = [repos]" in content

    def test_modified_action_for_apps_init(self, project) -> None:
        """The apps/__init__.py entry is marked as modified."""
        results = list(project.add_app("repos"))
        modified = [r for r in results if r.success and r.data.get("action") == "modified"]
        assert len(modified) == 1
        assert "__init__.py" in modified[0].item

    def test_returns_error_if_app_exists(self, project) -> None:
        """Second add_app with same name returns a single error result."""
        list(project.add_app("repos"))
        results = list(project.add_app("repos"))
        assert len(results) == 1
        assert not results[0].success
        assert "already exists" in results[0].message


class TestAddFlatApp:
    """Test suite for add_app with flat=True."""

    def test_creates_app_files(self, project) -> None:
        """Same app files are created for a flat app."""
        results = list(project.add_app("status", flat=True))
        paths = {r.item for r in results}

        assert any("status/__init__.py" in p for p in paths)
        assert any("status/interfaces.py" in p for p in paths)
        assert any("status/models.py" in p for p in paths)
        assert any("status/tables.py" in p for p in paths)
        assert any("status/commands/__init__.py" in p for p in paths)

    def test_init_has_no_group_decorator(self, project, tmp_path) -> None:
        """Flat app __init__.py imports commands but defines no @group."""
        list(project.add_app("status", flat=True))
        content = (
            tmp_path / "my-app" / "src" / "my_app" / "apps" / "status" / "__init__.py"
        ).read_text()
        assert "@group()" not in content
        assert "from .commands import commands" in content

    def test_wires_flat_app_with_extend(self, project, tmp_path) -> None:
        """apps/__init__.py uses extend (not append) for a flat app."""
        list(project.add_app("status", flat=True))
        content = (tmp_path / "my-app" / "src" / "my_app" / "apps" / "__init__.py").read_text()
        assert "from .status import commands as status_commands" in content
        assert "groups.extend(status_commands)" in content

    def test_flat_does_not_use_append(self, project, tmp_path) -> None:
        """Flat app wiring never uses groups.append."""
        list(project.add_app("status", flat=True))
        content = (tmp_path / "my-app" / "src" / "my_app" / "apps" / "__init__.py").read_text()
        assert "groups.append" not in content

    def test_returns_error_if_app_exists(self, project) -> None:
        """Second add_app with same name returns a single error result."""
        list(project.add_app("status", flat=True))
        results = list(project.add_app("status", flat=True))
        assert len(results) == 1
        assert not results[0].success
        assert "already exists" in results[0].message

    def test_add_command_works_on_flat_app(self, project, tmp_path) -> None:
        """add_command works normally on a flat app."""
        list(project.add_app("status", flat=True))
        results = list(project.add_command("check", "status"))
        assert any("commands/check.py" in r.item for r in results)
        path = (
            tmp_path / "my-app" / "src" / "my_app" / "apps" / "status" / "commands" / "__init__.py"
        )
        content = path.read_text()
        assert "from .check import check" in content
        assert "commands.append(check)" in content

    def test_mixed_grouped_and_flat(self, project, tmp_path) -> None:
        """Grouped and flat apps can coexist in apps/__init__.py."""
        list(project.add_app("repos"))
        list(project.add_app("status", flat=True))
        content = (tmp_path / "my-app" / "src" / "my_app" / "apps" / "__init__.py").read_text()
        assert "groups = [repos]" in content
        assert "groups.extend(status_commands)" in content


class TestAddCommand:
    """Test suite for add_command."""

    def test_creates_command_file(self, project) -> None:
        """Command file is written inside the app's commands/ directory."""
        list(project.add_app("repos"))
        results = list(project.add_command("list", "repos"))
        assert any("commands/list.py" in r.item for r in results)

    def test_wires_command_in_commands_init(self, project, tmp_path) -> None:
        """commands/__init__.py is updated with the new command import."""
        list(project.add_app("repos"))
        list(project.add_command("list", "repos"))
        path = (
            tmp_path / "my-app" / "src" / "my_app" / "apps" / "repos" / "commands" / "__init__.py"
        )
        content = path.read_text()
        assert "from .list import list" in content
        assert "commands.append(list)" in content

    def test_returns_error_if_app_not_found(self, project) -> None:
        """add_command returns an error result when the app does not exist."""
        results = list(project.add_command("list", "unknown"))
        assert len(results) == 1
        assert not results[0].success
        assert "App 'unknown' not found" in results[0].message

    def test_returns_error_if_command_exists(self, project) -> None:
        """Second add_command with the same name returns an error result."""
        list(project.add_app("repos"))
        list(project.add_command("list", "repos"))
        results = list(project.add_command("list", "repos"))
        assert len(results) == 1
        assert not results[0].success
        assert "already exists" in results[0].message


class TestAddCommands:
    """Test suite for add_commands (multi-name variant)."""

    def test_creates_multiple_commands(self, project) -> None:
        """add_commands creates one command file per name."""
        list(project.add_app("repos"))
        results = list(project.add_commands(("list", "show"), "repos"))
        assert any("commands/list.py" in r.item for r in results)
        assert any("commands/show.py" in r.item for r in results)

    def test_continues_after_partial_error(self, project) -> None:
        """add_commands proceeds past a duplicate error and yields remaining results."""
        list(project.add_app("repos"))
        list(project.add_commands(("list",), "repos"))
        results = list(project.add_commands(("list", "show"), "repos"))
        failed = [r for r in results if not r.success]
        succeeded = [r for r in results if r.success]
        assert failed
        assert succeeded

    def test_single_name_equivalent_to_add_command(self, project) -> None:
        """add_commands with one name produces the same results as add_command."""
        list(project.add_app("repos"))
        results = list(project.add_commands(("list",), "repos"))
        assert any("commands/list.py" in r.item for r in results)
        assert all(r.success for r in results)


class TestAddCommandNested:
    """Test suite for add_command with dotted app paths."""

    def test_creates_command_in_nested_group(self, project, tmp_path) -> None:
        """add_command with dotted path creates the file in the subgroup's commands/ dir."""
        list(project.add_app("demo"))
        list(project.add_group("tasks", "demo"))
        results = list(project.add_command("list", "demo.tasks"))
        assert any("demo/apps/tasks/commands/list.py" in r.item for r in results)

    def test_wires_command_in_nested_group(self, project, tmp_path) -> None:
        """commands/__init__.py of the subgroup receives the new import."""
        list(project.add_app("demo"))
        list(project.add_group("tasks", "demo"))
        list(project.add_command("list", "demo.tasks"))
        path = (
            tmp_path
            / "my-app"
            / "src"
            / "my_app"
            / "apps"
            / "demo"
            / "apps"
            / "tasks"
            / "commands"
            / "__init__.py"
        )
        content = path.read_text()
        assert "from .list import list" in content
        assert "commands.append(list)" in content

    def test_three_levels_deep(self, project, tmp_path) -> None:
        """Three-level dotted path a.b.c resolves to apps/a/apps/b/apps/c/."""
        list(project.add_app("a"))
        list(project.add_group("b", "a"))
        list(project.add_group("c", "a.b"))
        results = list(project.add_command("run", "a.b.c"))
        assert any("a/apps/b/apps/c/commands/run.py" in r.item for r in results)

    def test_simple_app_unchanged(self, project) -> None:
        """Single-segment --app still resolves to a top-level app (no regression)."""
        list(project.add_app("repos"))
        results = list(project.add_command("list", "repos"))
        assert any("repos/commands/list.py" in r.item for r in results)

    def test_error_intermediate_not_found(self, project) -> None:
        """Dotted path where an intermediate segment does not exist returns an error."""
        list(project.add_app("demo"))
        results = list(project.add_command("list", "demo.unknown"))
        assert len(results) == 1
        assert not results[0].success
        assert "App 'demo.unknown' not found" in results[0].message


class TestAddIntegration:
    """Test suite for add_integration."""

    def test_creates_simple_integration(self, project) -> None:
        """Simple integration writes a single .py file."""
        results = list(project.add_integration("github"))
        assert any("integrations/github.py" in r.item for r in results)

    def test_creates_package_integration(self, project) -> None:
        """Package integration writes client, helpers, models and __init__."""
        results = list(project.add_integration("ssh", package=True))
        paths = {r.item for r in results}
        assert any("ssh/__init__.py" in p for p in paths)
        assert any("ssh/client.py" in p for p in paths)
        assert any("ssh/helpers.py" in p for p in paths)
        assert any("ssh/models.py" in p for p in paths)

    def test_wires_integration_in_context(self, project, tmp_path) -> None:
        """core/context.py receives import and property stub."""
        list(project.add_integration("github"))
        content = (tmp_path / "my-app" / "src" / "my_app" / "core" / "context.py").read_text()
        assert "from .integrations.github import GithubIntegration" in content
        assert "self.github = GithubIntegration()" in content

    def test_returns_error_if_integration_exists(self, project) -> None:
        """Second add_integration with the same name returns an error result."""
        list(project.add_integration("github"))
        results = list(project.add_integration("github"))
        assert len(results) == 1
        assert not results[0].success
        assert "already exists" in results[0].message


class TestAddGroup:
    """Test suite for add_group."""

    def test_creates_subgroup_files(self, project, tmp_path) -> None:
        """All five subgroup skeleton files are created under apps/<app>/apps/<name>/."""
        list(project.add_app("demo"))
        results = list(project.add_group("tasks", "demo"))
        paths = {r.item for r in results}

        assert any("demo/apps/tasks/__init__.py" in p for p in paths)
        assert any("demo/apps/tasks/interfaces.py" in p for p in paths)
        assert any("demo/apps/tasks/models.py" in p for p in paths)
        assert any("demo/apps/tasks/tables.py" in p for p in paths)
        assert any("demo/apps/tasks/commands/__init__.py" in p for p in paths)

    def test_creates_apps_package_if_absent(self, project, tmp_path) -> None:
        """apps/<app>/apps/__init__.py is created when the apps/ directory does not exist yet."""
        list(project.add_app("demo"))
        list(project.add_group("tasks", "demo"))
        pkg_init = tmp_path / "my-app" / "src" / "my_app" / "apps" / "demo" / "apps" / "__init__.py"
        assert pkg_init.exists()

    def test_does_not_recreate_apps_package(self, project) -> None:
        """Adding a second group does not error on the already-existing apps/__init__.py."""
        list(project.add_app("demo"))
        list(project.add_group("tasks", "demo"))
        results = list(project.add_group("users", "demo"))
        assert all(r.success for r in results)

    def test_wires_import_in_parent_init(self, project, tmp_path) -> None:
        """Parent app __init__.py receives the from .apps.<name> import statement."""
        list(project.add_app("demo"))
        list(project.add_group("tasks", "demo"))
        content = (
            tmp_path / "my-app" / "src" / "my_app" / "apps" / "demo" / "__init__.py"
        ).read_text()
        assert "from .apps.tasks import tasks" in content

    def test_expands_subgroups_list(self, project, tmp_path) -> None:
        """subgroups = [] in parent __init__.py is expanded to include the new name."""
        list(project.add_app("demo"))
        list(project.add_group("tasks", "demo"))
        content = (
            tmp_path / "my-app" / "src" / "my_app" / "apps" / "demo" / "__init__.py"
        ).read_text()
        assert "subgroups = [tasks]" in content

    def test_second_group_expands_list_correctly(self, project, tmp_path) -> None:
        """Adding a second group appends to the existing subgroups list."""
        list(project.add_app("demo"))
        list(project.add_group("tasks", "demo"))
        list(project.add_group("users", "demo"))
        content = (
            tmp_path / "my-app" / "src" / "my_app" / "apps" / "demo" / "__init__.py"
        ).read_text()
        assert "subgroups = [tasks, users]" in content

    def test_error_app_not_found(self, project) -> None:
        """add_group returns an error when the parent app does not exist."""
        results = list(project.add_group("tasks", "unknown"))
        assert len(results) == 1
        assert not results[0].success
        assert "App 'unknown' not found" in results[0].message

    def test_error_group_already_exists(self, project) -> None:
        """Second add_group with same name returns an error with error_code=2."""
        list(project.add_app("demo"))
        list(project.add_group("tasks", "demo"))
        results = list(project.add_group("tasks", "demo"))
        assert len(results) == 1
        assert not results[0].success
        assert results[0].error_code == 2
        assert "already exists" in results[0].message

    def test_error_parent_init_missing(self, project, tmp_path) -> None:
        """add_group returns an error when the parent app __init__.py is absent."""
        list(project.add_app("demo"))
        parent_init = tmp_path / "my-app" / "src" / "my_app" / "apps" / "demo" / "__init__.py"
        parent_init.unlink()
        results = list(project.add_group("tasks", "demo"))
        assert not results[0].success
        assert "__init__.py" in results[0].message

    def test_error_no_subgroups_sentinel(self, project, tmp_path) -> None:
        """add_group returns an error when subgroups = [ is absent from parent __init__.py."""
        list(project.add_app("demo"))
        parent_init = tmp_path / "my-app" / "src" / "my_app" / "apps" / "demo" / "__init__.py"
        parent_init.write_text("# no subgroups sentinel here\n")
        results = list(project.add_group("tasks", "demo"))
        assert not results[0].success
        assert "subgroups = [" in results[0].message
