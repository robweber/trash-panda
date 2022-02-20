from jinja2.runtime import Undefined


def load_default(value, default_value):
    """returns given value if not undefined otherwise the supplied default"""
    return default_value if type(value) is Undefined else value
