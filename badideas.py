import builtins
import fishhook

IDEAS = {}
IS_IPYTHON = hasattr(builtins, "get_ipython")


class Idea:
    def __init__(self):
        self.enabled = None

    def enable(self):
        self.enabled = True

    def disable(self):
        self.enabled = False


def camelize(match):
    a, b = match.groups()
    return f"{a}_{b.lower()}" if a else b.lower()


def register(cls):
    import re

    inst = cls()
    IDEAS[re.sub(r"(.?)([A-Z])", camelize, cls.__name__)] = inst
    return inst


@register
class DictSort(Idea):
    def enable(self):
        @fishhook.hook(dict)
        def sort(self, key=None):
            keys = sorted(self, key=key)
            new = {key: self[key] for key in keys}
            self.clear()
            self.update(new)

        super().enable()

    def disable(self):
        fishhook.unhook(dict, "sort")
        super().disable()


@register
class IterableInt(Idea):
    def enable(self):
        @fishhook.hook(int)
        def __iter__(self):
            yield from range(self)

        super().enable()

    def disable(self):
        fishhook.unhook(int, "__iter__")
        super().disable()


@register
class SpellcheckClasses(Idea):
    def enable(self):
        import spelcheck

        if spelcheck.new != builtins.__build_class__:
            builtins.__build_class__ = spelcheck.new
        super().enable()

    def disable(self):
        import spelcheck

        builtins.__build_class__ = spelcheck.old
        super().disable()


@register
class WeakTyping(Idea):
    def enable(self):
        @fishhook.hook(str)
        def __add__(self, other):
            if isinstance(other, (int, float, type(None))):
                try:
                    val = int(self)
                except ValueError:
                    try:
                        val = float(self)
                    except ValueError:
                        return self + str(other)
                return val + other
            elif isinstance(other, list):
                return [self, *other]
            elif isinstance(other, tuple):
                return tuple(self, *other)
            elif isinstance(other, dict):
                return {self: None, **other}
            return fishhook.orig(self, other)

        @fishhook.hook(str)
        def __sub__(self, other):
            error = TypeError(
                f"unsupported operand type(s) for -: 'str' and {type(other).__name__!r}"
            )
            if isinstance(other, (int, float)):
                try:
                    val = int(self)
                except ValueError:
                    try:
                        val = float(self)
                    except ValueError:
                        raise error
                return val - other
            raise error

        if not IS_IPYTHON:
            @fishhook.hook(list)
            def __add__(self, other):
                if isinstance(other, (int, float, type(None))):
                    return [*self, other]
                elif other is Ellipsis:
                    new = [*self]
                    new.append(new)
                    return new
                elif isinstance(other, (dict, tuple)):
                    return [*self, *other]
                return fishhook.orig(self, other)

        super().enable()

    def disable(self):
        fishhook.unhook(str, "__add__")
        fishhook.unhook(str, "__sub__")
        if not IS_IPYTHON:
            fishhook.unhook(list, "__add__")
        super().disable()


def __getattr__(idea):
    if idea not in IDEAS:
        raise AttributeError
    bad_idea = IDEAS[idea]
    if bad_idea.enabled is None:
        bad_idea.enable()
    return bad_idea
