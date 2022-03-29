import logging
from collections import OrderedDict

from functools import wraps

from graphql.backend.core import GraphQLCoreBackend
from graphql.execution import ExecutionResult

from .middleware import TracingMiddleware

logger = logging.getLogger(__name__)


class ExtendedExecutionResult(ExecutionResult):
    def to_dict(self, format_error=None, dict_class=OrderedDict):
        r = super(ExtendedExecutionResult, self).to_dict()
        if self.extensions:
            r["extensions"] = self.extensions
        return r


# todo tracing on validation errors?
class TracingGQLBackend(GraphQLCoreBackend):
    def __init__(self, *args, enable_ftv1_tracing=None, **kwargs):
        self.enable_ftv1_tracing = enable_ftv1_tracing
        super().__init__(*args, **kwargs)

    def _is_tracing_enabled(self, context):
        if self.enable_ftv1_tracing is not None:
            return self.enable_ftv1_tracing
        try:
            return context.META.get('HTTP_APOLLO_FEDERATION_INCLUDE_TRACE') == 'ftv1'
        except:
            pass
        return False

    def document_from_string(self, schema, document_string):
        tracing_middleware = TracingMiddleware()
        tracing_middleware.start()

        document = super().document_from_string(schema, document_string)

        def execute_decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                tracing_enabled = self._is_tracing_enabled(kwargs['context_value'])
                if tracing_enabled:
                    # todo should it be the first or last middleware?
                    kwargs['middleware'] = (kwargs.get('middleware') or []) + [tracing_middleware]

                result = func(*args, **kwargs)

                if not tracing_enabled:
                    return result

                tracing_middleware.end()

                if isinstance(result, ExecutionResult):
                    result.extensions["ftv1"] = tracing_middleware.get_tracing_ftv1()
                    result = ExtendedExecutionResult(
                        data=result.data,
                        errors=result.errors,
                        invalid=result.invalid,
                        extensions=result.extensions
                    )
                return result
            return wrapper

        document.execute = execute_decorator(document.execute)
        return document


tracing_backend = TracingGQLBackend()
