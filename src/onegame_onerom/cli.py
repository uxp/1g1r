#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__author__ = 'uxp'
__version__ = '1.0'
__license__ = 'BSD3'
__copyright__ = 'Copyright 2025, uxp'

import logging
import os
import click

logging.getLogger('requests').setLevel(logging.WARNING)

def config_logging(verbose, log_path=None):
    log_handlers = []
    log_level = logging.INFO

    if verbose:
        log_level = logging.DEBUG

    if log_path:
        file_handler = logging.FileHandler(log_path, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)s %(name)s: %(message)s', '%Y-%m-%d %H:%M:%S'))
        log_handlers.append(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)s %(name)s: %(message)s', '%Y-%m-%d %H:%M:%S'))
    log_handlers.append(console_handler)

    logging.basicConfig(level=log_level, handlers=log_handlers)
    logger = logging.getLogger(__name__)
    return logger


COMMANDS = {
    name: __import__('src.onegame_onerom.commands.cmd_' + name, None, None, ['cli']).cli
    for name in [
        filename[4:-3]
        for filename
        in os.listdir(os.path.abspath(os.path.join(os.path.dirname(__file__), 'commands')))
        if filename.endswith('.py') and filename.startswith('cmd_')
    ]
}


@click.group(commands=COMMANDS)
@click.option("-v", "--verbose", is_flag=True, help="Enables verbose mode.")
@click.option("-l", "--log", type=str, help="Path to log file (in addition to console output).")
@click.pass_context
def cli(ctx, verbose, log):
    ctx.obj = {
        "logger": config_logging(verbose, log)
    }

