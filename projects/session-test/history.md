# Workspace History: projects

## [2026-07-12 18:54] User:
semantic search how do we calculate speed metrics

### Agent:
To calculate speed metrics, we use the `calculate_velocity` function in physics.py, which relies on distance and time inputs. This function is imported and executed within the `run_test` function in simulation.py to process the test data.

---

## [2026-07-12 18:55] User:
❯ blast radius calculate_velocity

### Agent:
The `calculate_velocity` function in physics.py is directly called by the `run_test` function in simulation.py, meaning any changes to `calculate_velocity` will affect the simulation output and potentially downstream tests or integrations that depend on simulation.py.

---

