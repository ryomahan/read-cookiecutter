#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
cookiecutter.hooks
------------------

Functions for discovering and executing various cookiecutter hooks.
"""

import errno
import io
import logging
import os
import subprocess
import sys
import tempfile

from jinja2 import Template

from cookiecutter import utils
from .exceptions import FailedHookException


_HOOKS = [
    'pre_gen_project',
    'post_gen_project',
    # TODO: other hooks should be listed here
]
EXIT_SUCCESS = 0


def find_hooks():
    """
    Must be called with the project template as the current working directory.
    Returns a dict of all hook scripts provided.
    Dict's key will be the hook/script's name, without extension, while
    values will be the absolute path to the script.
    Missing scripts will not be included in the returned dict.
    """
    hooks_dir = 'hooks'
    r = {}
    logging.debug('hooks_dir is {0}'.format(hooks_dir))
    if not os.path.isdir(hooks_dir):
        logging.debug('No hooks/ dir in template_dir')
        return r
    for f in os.listdir(hooks_dir):
        basename = os.path.splitext(os.path.basename(f))[0]
        if basename in _HOOKS:
            r[basename] = os.path.abspath(os.path.join(hooks_dir, f))
    return r


def run_script(script_path, cwd='.'):
    """
    Executes a script from a working directory.

    :param script_path: Absolute path to the script to run.
    :param cwd: The directory to run the script from.
    """
    run_thru_shell = sys.platform.startswith('win')
    if script_path.endswith('.py'):
        script_command = [sys.executable, script_path]
    else:
        script_command = [script_path]

    utils.make_executable(script_path)

    try:
        proc = subprocess.Popen(
            script_command,
            shell=run_thru_shell,
            cwd=cwd
        )
        exit_status = proc.wait()
        if exit_status != EXIT_SUCCESS:
            raise FailedHookException(
                "Hook script failed (exit status: %d)" % exit_status)
    except OSError as oe:
        if oe.errno == errno.ENOEXEC:
            raise FailedHookException(
                "Hook script failed, might be an "
                "empty file or missing a shebang")
        raise FailedHookException(
            "Hook script failed (error: %s)" % oe)


def run_script_with_context(script_path, cwd, context):
    """
    Executes a script after rendering with it Jinja.

    :param script_path: Absolute path to the script to run.
    :param cwd: The directory to run the script from.
    :param context: Cookiecutter project template context.
    """
    _, extension = os.path.splitext(script_path)

    contents = io.open(script_path, 'r', encoding='utf-8').read()

    with tempfile.NamedTemporaryFile(
        delete=False,
        mode='wb',
        suffix=extension
    ) as temp:
        output = Template(contents).render(**context)
        temp.write(output.encode('utf-8'))

    run_script(temp.name, cwd)


def run_hook(hook_name, project_dir, context):
    """
    Try to find and execute a hook from the specified project directory.

    :param hook_name: The hook to execute.
    :param project_dir: The directory to execute the script from.
    :param context: Cookiecutter project context.
    """
    script = find_hooks().get(hook_name)
    if script is None:
        logging.debug('No hooks found')
        return
    run_script_with_context(script, project_dir, context)
