# Coding Standards

## General
-   **Language**: English for all code, comments, and documentation.
-   **Formatting**: Adhere to standard style guides (PEP 8 for Python, Prettier/ESLint for JavaScript/React).

## Python (Backend)
-   **Style Guide**: PEP 8.
-   **Type Hinting**: Use Python type hints (`typing` module) for function arguments and return values.
-   **Framework**: FastAPI.
    -   Use Pydantic models for data validation.
    -   Use async/await for route handlers.
-   **Testing**: Pytest.
    -   Test files should be located in `tests/`.
    -   Test functions should start with `test_`.

## JavaScript/React (Frontend)
-   **Framework**: React 19 using Functional Components and Hooks.
-   **Build Tool**: Vite.
-   **Style**: CSS Modules or standard CSS imported in components.
-   **State Management**: `useState` and `useEffect` for local state; minimal global state.
-   **Linting**: ESLint configuration as provided in `package.json`.

## Version Control
-   **Commits**: Clear, descriptive commit messages.
-   **Branching**: Feature branches merged into `main` via Pull Requests (implied).
