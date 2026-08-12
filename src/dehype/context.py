from contextvars import ContextVar

run_id_var: ContextVar[str | None] = ContextVar("run_id", default=None)
