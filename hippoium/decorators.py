
from functools import wraps
from typing import Callable, Any
from hippoium.core.hooks import hook_registry
from hippoium.core.context_manager import context_session, PromptContextSession

def with_prompt_context(memory: Any = None, cache_ttl: int = 0, rag: bool = False) -> Callable[[Callable[[str], str]], Callable[[str], str]]:
    """
    Decorator to inject context (memory, negative examples, RAG, etc.) into a prompt handling function.
    Example:
        @with_prompt_context(memory="redis", cache_ttl=3600, rag=True)
        def enhance_prompt(prompt: str) -> str:
            return prompt
    The decorated function will automatically build an enhanced prompt with context.
    """
    def decorator(func: Callable[[str], str]) -> Callable[[str], str]:
        @wraps(func)
        def wrapper(prompt: str, *args, **kwargs) -> str:
            # Use a context session to build the prompt with context
            with context_session(memory=memory, cache_ttl=cache_ttl, rag=rag) as ctx:
                enhanced_prompt = ctx.build(prompt)
            return enhanced_prompt
        return wrapper
    return decorator

def on_event(event_name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator to register a function as a hook for a given event.
    For example, use @on_event("before_prompt_injection") to register a function
    that will be called before prompt injection occurs.
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        # Register the function in the global hook registry for the specified event
        hook_registry.register(event_name, func)
        return func  # Return the original function unchanged
    return decorator

def negative_examples(auto_detect: bool = False) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator to enable negative prompt examples injection for a function (to be used alongside with_prompt_context).
    If auto_detect is True, a generic negative instruction (to avoid harmful content) is automatically added.
    If auto_detect is False, it assumes negative examples will be provided manually via context.
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Define a hook to inject negative examples before prompt injection
            def inject_negative(context: PromptContextSession):
                if auto_detect:
                    # Add a default safety instruction to negative examples
                    context.negative_examples.append("Don't generate harmful or disallowed content.")
                # If auto_detect is False, do nothing here (user may have added custom negative examples in context)
            # Register the hook for this call
            hook_registry.register("before_prompt_injection", inject_negative)
            try:
                # Execute the wrapped function (which likely triggers context building)
                return func(*args, **kwargs)
            finally:
                # Clean up: remove the hook after function execution
                hook_registry.unregister("before_prompt_injection", inject_negative)
        return wrapper
    return decorator