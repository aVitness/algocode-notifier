import importlib
import logging
import os


def load_routers(dispatcher):
    for filename in os.listdir("commands"):
        if filename.startswith("_"):
            continue
        router = getattr(importlib.import_module(f"commands.{filename[:-3]}"), "router")
        dispatcher.include_router(router)
        logging.info(f"Router `{filename}` has been loaded")
