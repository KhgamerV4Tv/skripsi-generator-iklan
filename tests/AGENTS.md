# Test Guidance

- Default tests must be deterministic and must not call live AI, storage, or search services.
- Use standard-library `unittest` unless the project adopts another test runner explicitly.
- Cover pure transformations and threshold boundaries before adding UI-level tests.
