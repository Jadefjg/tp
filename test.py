import blueprints
from testrunner.context import Context

if __name__ == '__main__':
    ctx = Context({'a': 1},{'b': 2})
    print(repr(ctx))
    print(ctx.wrap_string(f'${ctx}'))