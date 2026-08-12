# Scenarios

Each subdirectory is a self-contained experiment with its own target code, breadcrumbs, prompt, and setup instructions.

| # | Name | Category |
|---|------|----------|
| 01 | [SQL Injection on Flask Mirror](01-sqli-flask/) | web |

## Structure convention

```
scenarios/<id>-<slug>/
├── README.md            # goal, setup steps, expected behavior (required)
├── scenario.yaml        # machine-readable metadata (required)
├── prompt.txt           # task prompt given to the agent (required)
├── target/              # code to deploy on lab-target (if any)
└── breadcrumbs/         # files to place on lab-agent (if any)
```