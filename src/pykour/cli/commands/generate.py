"""Generate command for scaffolding code."""

from __future__ import annotations

import argparse
import sys


def register_command(subparsers: argparse._SubParsersAction) -> None:
    """Register the generate command."""
    parser = subparsers.add_parser(
        "generate",
        aliases=["gen", "g"],
        help="Generate scaffolding code",
        description="Generate scaffolding code for various components.",
    )

    # Create subparsers for different generators
    gen_subparsers = parser.add_subparsers(
        dest="generator",
        help="Generator to use",
        required=True,
    )

    # CRUD generator
    crud_parser = gen_subparsers.add_parser(
        "crud",
        help="Generate CRUD endpoints for a resource",
        description="Generate route files for CRUD operations on a resource.",
    )
    crud_parser.add_argument(
        "resource",
        help="Resource name (e.g., 'users', 'products')",
    )
    crud_parser.add_argument(
        "--table",
        dest="table_name",
        help="Database table name (defaults to resource name)",
    )
    crud_parser.add_argument(
        "--id-field",
        dest="id_field",
        default="id",
        help="Primary key field name (default: id)",
    )
    crud_parser.add_argument(
        "--id-type",
        dest="id_type",
        default="int",
        choices=["int", "str"],
        help="Primary key type (default: int)",
    )
    crud_parser.add_argument(
        "--routes-dir",
        dest="routes_dir",
        default="routes",
        help="Routes directory (default: routes)",
    )
    crud_parser.add_argument(
        "--with-schema",
        dest="with_schema",
        action="store_true",
        help="Generate schema file for validation",
    )
    crud_parser.add_argument(
        "--with-tests",
        dest="with_tests",
        action="store_true",
        help="Generate test file",
    )
    crud_parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Overwrite existing files",
    )
    crud_parser.add_argument(
        "--table-class",
        dest="table_class",
        help="Table class path for field inference (e.g., 'app.tables:UserTable')",
    )

    crud_parser.set_defaults(func=cmd_generate_crud)

    # Route generator
    route_parser = gen_subparsers.add_parser(
        "route",
        help="Generate route file for specific HTTP methods",
        description="Generate a route file with specified HTTP method handlers.",
    )
    route_parser.add_argument(
        "method",
        help=(
            "HTTP method(s): GET, POST, PUT, DELETE, PATCH, CRUD, "
            "or comma-separated (e.g., GET,POST)"
        ),
    )
    route_parser.add_argument(
        "path",
        help="URL path (e.g., /api/v1/hello, /api/users/{id})",
    )
    route_parser.add_argument(
        "--routes-dir",
        dest="routes_dir",
        default="routes",
        help="Routes directory (default: routes)",
    )
    route_parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Overwrite existing files",
    )

    route_parser.set_defaults(func=cmd_generate_route)


def cmd_generate_route(args: argparse.Namespace) -> int:
    """Execute the generate route command."""
    from pykour.generators.route import RouteGenerator, parse_methods

    try:
        methods = parse_methods(args.method)

        generator = RouteGenerator(
            path=args.path,
            methods=methods,
            routes_dir=args.routes_dir,
        )

        created_file = generator.generate(force=args.force)

        print(f"\n✓ Generated route file for '{args.path}':\n")
        print(f"  • {created_file}")

        methods_str = ", ".join(m.lower() for m in methods)
        print(f"\nHandlers: {methods_str}")
        print("\nNext steps:")
        print("  1. Review and customize the generated file")
        print("  2. Run your application: pykour run app:app --reload")

        return 0

    except FileExistsError as e:
        print(f"\n✗ Error: {e}", file=sys.stderr)
        print("  Use --force to overwrite existing files.", file=sys.stderr)
        return 1

    except ValueError as e:
        print(f"\n✗ Error: {e}", file=sys.stderr)
        return 1

    except Exception as e:
        print(f"\n✗ Error generating route: {e}", file=sys.stderr)
        return 1


def cmd_generate_crud(args: argparse.Namespace) -> int:
    """Execute the generate crud command."""
    import importlib

    from pykour.generators.crud import CRUDGenerator

    try:
        # Import table class if specified
        table_class = None
        if args.table_class:
            module_path, class_name = args.table_class.rsplit(":", 1)
            module = importlib.import_module(module_path)
            table_class = getattr(module, class_name)

        generator = CRUDGenerator(
            resource_name=args.resource,
            table_name=args.table_name,
            table_class=table_class,
            id_field=args.id_field,
            id_type=args.id_type,
            routes_dir=args.routes_dir,
        )

        created_files = generator.generate(
            with_schema=args.with_schema,
            with_tests=args.with_tests,
            force=args.force,
        )

        print(f"\n✓ Generated CRUD endpoints for '{args.resource}':\n")
        for path in created_files:
            print(f"  • {path}")

        print("\nNext steps:")
        print("  1. Review and customize the generated files")
        if args.with_schema and not table_class:
            print(
                f"  2. Add field definitions to schemas/{generator.resource_singular}.py"
            )
        print("  3. Run your application: pykour run app:app --reload")

        return 0

    except FileExistsError as e:
        print(f"\n✗ Error: {e}", file=sys.stderr)
        print("  Use --force to overwrite existing files.", file=sys.stderr)
        return 1

    except ValueError as e:
        if "not enough values to unpack" in str(e) or ":" not in str(
            args.table_class or ""
        ):
            print(
                f"\n✗ Error: Invalid --table-class format: {args.table_class}",
                file=sys.stderr,
            )
            print(
                "  Expected format: 'module.path:ClassName'",
                file=sys.stderr,
            )
        else:
            print(f"\n✗ Error: {e}", file=sys.stderr)
        return 1

    except (ImportError, AttributeError) as e:
        print(f"\n✗ Error loading table class: {e}", file=sys.stderr)
        return 1

    except Exception as e:
        print(f"\n✗ Error generating CRUD: {e}", file=sys.stderr)
        return 1
