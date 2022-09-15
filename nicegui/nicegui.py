# isort:skip_file
from typing import Awaitable, Callable

if True:  # NOTE: prevent formatter from mixing up these lines
    import builtins
    print_backup = builtins.print
    builtins.print = lambda *args, **kwargs: kwargs.get('flush') and print_backup(*args, **kwargs)
    from .ui import Ui  # NOTE: before justpy
    import justpy as jp
    builtins.print = print_backup

from . import binding, globals
from .task_logger import create_task
from .timer import Timer
from .elements.page import error404

jp.app.router.on_startup.clear()  # NOTE: remove JustPy's original startup function


@jp.app.on_event('startup')
async def patched_justpy_startup():
    jp.WebPage.loop = jp.asyncio.get_event_loop()
    jp.JustPy.loop = jp.WebPage.loop
    jp.JustPy.STATIC_DIRECTORY = jp.os.environ["STATIC_DIRECTORY"]
    print(f'NiceGUI ready to go on {"https" if jp.SSL_KEYFILE else "http"}://{jp.HOST}:{jp.PORT}')


@jp.app.on_event('startup')
async def startup():
    jp.Route("/{path:path}", error404, last=True)
    for route, page_builder in globals.page_builders.items():
        if page_builder.shared:
            jp.Route(route, (await page_builder.function())._route_function)
        else:
            jp.Route(route, page_builder.function)
    globals.tasks.extend(create_task(t.coro, name=t.name) for t in Timer.prepared_coroutines)
    Timer.prepared_coroutines.clear()
    globals.tasks.extend(create_task(t, name='startup task')
                         for t in globals.startup_handlers if isinstance(t, Awaitable))
    [safe_invoke(t) for t in globals.startup_handlers if isinstance(t, Callable)]
    jp.run_task(binding.loop())


@jp.app.on_event('shutdown')
def shutdown():
    [create_task(t, name='shutdown task') for t in globals.shutdown_handlers if isinstance(t, Awaitable)]
    [safe_invoke(t) for t in globals.shutdown_handlers if isinstance(t, Callable)]
    [t.cancel() for t in globals.tasks]


def safe_invoke(func: Callable):
    try:
        result = func()
        if isinstance(result, Awaitable):
            create_task(result)
    except:
        globals.log.exception(f'could not invoke {func}')


app = globals.app = jp.app
ui = Ui()
