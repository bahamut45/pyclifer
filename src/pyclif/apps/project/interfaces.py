"""File system operations and template rendering for project scaffolding."""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from pyclif import OperationResult
from pyclif.apps.project.renderers import ScaffoldingRenderer
from pyclif.core.interfaces import BaseInterface


class ScaffoldingInterface(BaseInterface):
    """Renders templates and manages generated project files.

    Args:
        ctx: The CLI context.
        root: Project root directory. Defaults to the current working directory.
    """

    _TEMPLATES_DIR = Path(__file__).parent / "templates"

    renderers = {
        "init_project": ScaffoldingRenderer,
        "add_app": ScaffoldingRenderer,
        "add_command": ScaffoldingRenderer,
        "add_integration": ScaffoldingRenderer,
    }

    def __init__(self, ctx, root: Path = Path(".")) -> None:
        super().__init__(ctx)
        self._root = root
        self._env = Environment(
            loader=FileSystemLoader(str(self._TEMPLATES_DIR)),
            keep_trailing_newline=True,
        )

    def init_project(self, name: str, package_manager: str = "uv") -> Iterator[OperationResult]:
        """Create a full project skeleton in a new directory.

        Args:
            name: Project name (kebab-case or snake_case).
            package_manager: Toolchain to target — "uv" (default) or "poetry".

        Yields:
            OperationResult for each file created.
        """
        if package_manager not in ("uv", "poetry"):
            yield OperationResult.error(
                name,
                f"Unsupported package manager '{package_manager}'. Use 'uv' or 'poetry'.",
            )
            return

        ns = self._names(name)
        root = Path(name)
        if root.exists():
            yield OperationResult.error(name, f"Directory '{name}' already exists.", error_code=2)
            return

        pkg = f"src/{ns['name_snake']}"
        pm_tmpl = f"pyproject_{package_manager}.toml.jinja2"
        files = [
            (root / "pyproject.toml", pm_tmpl),
            (root / "README.md", "readme.md.jinja2"),
            (root / ".gitignore", "gitignore.jinja2"),
            (root / f"{pkg}/__init__.py", "project_package_init.py.jinja2"),
            (root / f"{pkg}/cli.py", "project_cli.py.jinja2"),
            (root / f"{pkg}/core/context.py", "project_context.py.jinja2"),
            (root / f"{pkg}/core/constants.py", "project_constants.py.jinja2"),
            (root / f"{pkg}/core/options.py", "project_options.py.jinja2"),
            (root / f"{pkg}/core/integrations/__init__.py", "project_integrations_init.py.jinja2"),
            (root / f"{pkg}/apps/__init__.py", "project_apps_init.py.jinja2"),
            (root / "tests/__init__.py", "tests_init.py.jinja2"),
            (root / "tests/conftest.py", "tests_conftest.py.jinja2"),
        ]
        for dest, tmpl in files:
            yield self._write_rendered(dest, tmpl, ns)

    def add_app(self, name: str, flat: bool = False) -> Iterator[OperationResult]:
        """Create an app skeleton inside the current project's apps/ directory.

        Args:
            name: App name (snake_case).
            flat: When True, skip the @group wrapper and expose commands directly
                on the app_group. Defaults to False.

        Yields:
            OperationResult for each file created or modified.
        """
        ns = self._names(name)
        app_dir = self._root / "src" / self._detect_package() / "apps" / ns["name_snake"]
        if app_dir.exists():
            yield OperationResult.error(
                str(app_dir), f"App '{name}' already exists at {app_dir}.", error_code=2
            )
            return

        init_tmpl = "app_init_flat.py.jinja2" if flat else "app_init.py.jinja2"
        files = [
            (app_dir / "__init__.py", init_tmpl),
            (app_dir / "interfaces.py", "app_interfaces.py.jinja2"),
            (app_dir / "models.py", "app_models.py.jinja2"),
            (app_dir / "tables.py", "app_tables.py.jinja2"),
            (app_dir / "commands/__init__.py", "app_commands_init.py.jinja2"),
        ]
        for dest, tmpl in files:
            yield self._write_rendered(dest, tmpl, ns)
        if flat:
            yield from self._wire_app_flat(ns["name_snake"])
        else:
            yield from self._wire_app_grouped(ns["name_snake"])

    def add_command(self, name: str, app: str) -> Iterator[OperationResult]:
        """Create a command file inside an app's commands/ directory.

        Args:
            name: Command name (snake_case).
            app: App name to add the command to.

        Yields:
            OperationResult for each file created or modified.
        """
        ns = self._names(name)
        pkg = self._detect_package()
        commands_dir = self._root / "src" / pkg / "apps" / app / "commands"
        if not commands_dir.exists():
            yield OperationResult.error(
                str(commands_dir),
                f"App '{app}' not found. Run `pyclif project add app {app}` first.",
            )
            return
        cmd_file = commands_dir / f"{ns['name_snake']}.py"
        if cmd_file.exists():
            yield OperationResult.error(
                str(cmd_file), f"Command '{name}' already exists at {cmd_file}.", error_code=2
            )
            return

        yield self._write_rendered(cmd_file, "command.py.jinja2", ns)
        yield from self._wire_command(ns["name_snake"], app)
        yield from self._wire_interface_method(ns["name_snake"], app)

    def add_integration(self, name: str, package: bool = False) -> Iterator[OperationResult]:
        """Create an integration module inside core/integrations/.

        Args:
            name: Integration name (snake_case).
            package: When True, generate a package with a client, helpers, models.

        Yields:
            OperationResult for each file created or modified.
        """
        ns = self._names(name)
        pkg = self._detect_package()
        integrations_dir = self._root / "src" / pkg / "core" / "integrations"
        if not integrations_dir.exists():
            yield OperationResult.error(
                str(integrations_dir),
                "core/integrations/ not found. Are you in a pyclif project root?",
            )
            return

        if package:
            pkg_dir = integrations_dir / ns["name_snake"]
            if pkg_dir.exists():
                yield OperationResult.error(
                    str(pkg_dir),
                    f"Integration '{name}' already exists at {pkg_dir}.",
                    error_code=2,
                )
                return
            files = [
                (pkg_dir / "__init__.py", "integration_package_init.py.jinja2"),
                (pkg_dir / "client.py", "integration_package_client.py.jinja2"),
                (pkg_dir / "helpers.py", "integration_package_helpers.py.jinja2"),
                (pkg_dir / "models.py", "integration_package_models.py.jinja2"),
            ]
            for dest, tmpl in files:
                yield self._write_rendered(dest, tmpl, ns)
        else:
            simple_file = integrations_dir / f"{ns['name_snake']}.py"
            if simple_file.exists():
                yield OperationResult.error(
                    str(simple_file),
                    f"Integration '{name}' already exists at {simple_file}.",
                    error_code=2,
                )
                return
            yield self._write_rendered(simple_file, "integration_simple.py.jinja2", ns)

        yield from self._wire_integration(ns["name_snake"], ns["name_pascal"])

    def _wire_app_grouped(self, name_snake: str) -> Iterator[OperationResult]:
        """Insert import and expand the group list in apps/__init__.py for a grouped app.

        Produces idiomatic code: all imports are grouped together above the
        `groups = [...]` list, and the new name is added inline to that list
        rather than via a separate `.append()` call.

        Args:
            name_snake: Snake-case app name.

        Yields:
            OperationResult for the modified file.
        """
        pkg = self._detect_package()
        apps_init = self._root / "src" / pkg / "apps" / "__init__.py"
        if not apps_init.exists():
            yield OperationResult.error(str(apps_init), f"File '{apps_init}' not found.")
            return

        content = apps_init.read_text()
        new_import = f"from .{name_snake} import {name_snake}\n"

        # Insert import after the last existing `from .` block, or just before
        # `groups =` when the file has no local imports yet.
        if re.search(r"^from \.", content, re.MULTILINE):
            content = re.sub(
                r"((?:^from \.[^\n]*\n)+)",
                lambda m: m.group(0) + new_import,
                content,
                count=1,
                flags=re.MULTILINE,
            )
        else:
            content = re.sub(r"(groups\s*=\s*\[)", new_import + r"\1", content, count=1)

        # Expand groups = [...] to include the new name inline.
        def _expand(m: re.Match) -> str:
            existing = m.group(1).strip()
            if existing:
                return f"groups = [{existing}, {name_snake}]"
            return f"groups = [{name_snake}]"

        content = re.sub(r"groups\s*=\s*\[(.*?)]", _expand, content)
        apps_init.write_text(content)
        yield OperationResult.ok(str(apps_init), message="modified", data={"action": "modified"})

    def _wire_app_flat(self, name_snake: str) -> Iterator[OperationResult]:
        """Append import and exports.extend call to apps/__init__.py for a flat app.

        Args:
            name_snake: Snake-case app name.

        Yields:
            OperationResult for the modified file.
        """
        pkg = self._detect_package()
        apps_init = self._root / "src" / pkg / "apps" / "__init__.py"
        yield from self._append_to_init(
            apps_init,
            f"\nfrom .{name_snake} import commands as {name_snake}_commands\n"
            f"groups.extend({name_snake}_commands)\n",
        )

    def _wire_command(self, name_snake: str, app: str) -> Iterator[OperationResult]:
        """Append import and commands.append call to the app's commands/__init__.py.

        Args:
            name_snake: Snake-case command name.
            app: App name that owns this command.

        Yields:
            OperationResult for the modified file.
        """
        pkg = self._detect_package()
        commands_init = self._root / "src" / pkg / "apps" / app / "commands" / "__init__.py"
        yield from self._append_to_init(
            commands_init,
            f"\nfrom .{name_snake} import {name_snake}\ncommands.append({name_snake})\n",
        )

    def _append_to_init(self, path: Path, content: str) -> Iterator[OperationResult]:
        """Check an init file exists, append content, and yield a modified result.

        Args:
            path: Path to the __init__.py file to modify.
            content: Text to append.

        Yields:
            OperationResult indicating the success or a missing-file error.
        """
        if not path.exists():
            yield OperationResult.error(str(path), f"File '{path}' not found.")
            return
        self._append_to_file(path, content)
        yield OperationResult.ok(str(path), message="modified", data={"action": "modified"})

    def _wire_interface_method(self, name_snake: str, app: str) -> Iterator[OperationResult]:
        """Inject a renderer entry and a method stub into an app's interfaces.py.

        Args:
            name_snake: Snake-case command name.
            app: App name that owns the command.

        Yields:
            OperationResult for the modified file.
        """
        pkg = self._detect_package()
        interfaces_file = self._root / "src" / pkg / "apps" / app / "interfaces.py"
        if not interfaces_file.exists():
            yield OperationResult.error(
                str(interfaces_file), f"File '{interfaces_file}' not found."
            )
            return

        app_pascal = "".join(w.capitalize() for w in app.split("_"))
        renderer_cls = f"{app_pascal}Renderer"
        content = interfaces_file.read_text()

        if "# --- renderers ---" not in content or "# --- commands ---" not in content:
            yield OperationResult.error(
                str(interfaces_file),
                "Sentinel comments not found in interfaces.py — skipping method injection.",
            )
            return

        sentinel_renderers = (
            "        # --- renderers --- (used by `pyclif project add command` — do not remove)\n"
        )
        sentinel_commands = (
            "    # --- commands --- (used by `pyclif project add command` — do not remove)"
        )
        content = content.replace(
            sentinel_renderers,
            f'        "{name_snake}": {renderer_cls},\n{sentinel_renderers}',
        )
        method = (
            f"\n    def {name_snake}(self) -> list[OperationResult]:\n"
            f'        """{name_snake.replace("_", " ").title()}.\n\n'
            f"        Returns:\n"
            f"            List of OperationResult objects.\n"
            f'        """\n'
            f"        # TODO: implement\n"
            f"        return []\n"
            f"\n{sentinel_commands}"
        )
        content = content.replace(sentinel_commands, method)
        interfaces_file.write_text(content)
        yield OperationResult.ok(
            str(interfaces_file), message="modified", data={"action": "modified"}
        )

    def _wire_integration(self, name_snake: str, name_pascal: str) -> Iterator[OperationResult]:
        """Inject an integration import and property stub into core/context.py.

        Args:
            name_snake: Snake-case integration name.
            name_pascal: PascalCase integration name.

        Yields:
            OperationResult for the modified file.
        """
        pkg = self._detect_package()
        context_file = self._root / "src" / pkg / "core" / "context.py"
        if not context_file.exists():
            yield OperationResult.error(str(context_file), f"File '{context_file}' not found.")
            return
        content = context_file.read_text()

        new_import = f"from .integrations.{name_snake} import {name_pascal}Integration\n"
        content = re.sub(
            r"((?:^(?:from|import)[^\n]+\n)+)",
            lambda m: m.group(0) + new_import,
            content,
            count=1,
            flags=re.MULTILINE,
        )
        content = content.replace(
            "        super().__init__()\n",
            f"        super().__init__()\n        self.{name_snake} = {name_pascal}Integration()\n",
            1,
        )
        context_file.write_text(content)
        yield OperationResult.ok(str(context_file), message="modified", data={"action": "modified"})

    def _render(self, template_name: str, variables: dict) -> str:
        """Render a Jinja2 template with the given variables.

        Args:
            template_name: Filename inside the templates/ directory.
            variables: Template context variables.

        Returns:
            Rendered string content.
        """
        return self._env.get_template(template_name).render(**variables)

    def _write_rendered(self, path: Path, template_name: str, variables: dict) -> OperationResult:
        """Render a template and write it to disk.

        Args:
            path: Destination file path.
            template_name: Template to render.
            variables: Template context variables.

        Returns:
            OperationResult indicating success or failure.
        """
        if path.exists():
            return OperationResult.error(str(path), f"File '{path}' already exists.", error_code=2)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self._render(template_name, variables))
        return OperationResult.ok(str(path), message="created", data={"action": "created"})

    @staticmethod
    def _append_to_file(path: Path, content: str) -> None:
        """Append content to an existing file.

        Args:
            path: File to append to.
            content: Text to append.
        """
        with path.open("a") as fh:
            fh.write(content)

    @staticmethod
    def _names(name: str) -> dict[str, str]:
        """Derive snake_case and PascalCase variants from a name.

        Args:
            name: Raw name (kebab-case or snake_case).

        Returns:
            Dict with keys: name, name_snake, name_pascal.
        """
        snake = name.replace("-", "_")
        pascal = "".join(word.capitalize() for word in snake.split("_"))
        return {"name": name, "name_snake": snake, "name_pascal": pascal}

    def _detect_package(self) -> str:
        """Detect the Python package name from the src/ directory.

        Returns:
            The package directory name is found under src/.

        Raises:
            RuntimeError: If src/ does not exist or contains no package.
        """
        src = self._root / "src"
        if not src.exists():
            raise RuntimeError("src/ directory not found. Are you in a pyclif project root?")
        candidates = [d for d in src.iterdir() if d.is_dir() and not d.name.startswith(".")]
        if not candidates:
            raise RuntimeError("No package found under src/.")
        return candidates[0].name
