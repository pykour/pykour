# Release Notes

## 0.1.4 - 2024-07-28

### Features

- Implement database access functions
- Implementation of a Logger within the Framework

### Enhancements

- Add Codacy badge
- Fix Gunicorn and Uvicorn logging setting
- Fix type hint
- Transaction control implementation
- Fix Connection class
- Enhancing the way Router is set up
- Test case improvement and refactoring

## Fixed

- Remove pysqlite3 from pyproject.toml
- BAD REQUEST when an exception occurs

## 0.1.3 - 2024-07-15

### Features

- Support for dict type arguments in route methods
- Implementation of the dev subcommand
- Support configuration file
- Support Middleware (UUID, GZIP)

### Enhancement

- Discontinued support for the TRACE method

### Fixed

- Internal Server Error occurs when using the DELETE method

## 0.1.2 - 2024-07-07

### Features

- Add BaseSchema and @validate decorator

### Enhancements

- Write User's Guide
- Improved of test cases
- Support codecov.io
- Changing the default host for Pykour CLI
- Setup Icon and Logo

### Fixed

- Internal Server Error occurs when using the DELETE method
- Add the current directory to the module search path

## 0.1.1 - 2024-07-03

### Changed

- Documentation updates

### Fixed

- Pykour.route() and Router.route() required method and status_code.

## 0.1.0 - 2024-06-30

- Initial release
