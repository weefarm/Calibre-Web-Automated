# Calibre-Web Automated – fork of Calibre-Web
# Copyright (C) 2018-2026 Calibre-Web contributors
# Copyright (C) 2024-2026 Calibre-Web Automated contributors
# SPDX-License-Identifier: GPL-3.0-or-later
# See CONTRIBUTORS for full list of authors.

import logging
import os
import re
import sys
import json

from .constants import BASE_DIR
try:
    from importlib.metadata import version
    importlib = True
    ImportNotFound = BaseException
except ImportError:
    importlib = False
    version = None

if not importlib:
    try:
        import pkg_resources
        from pkg_resources import DistributionNotFound as ImportNotFound
        pkgresources = True
    except ImportError as e:
        pkgresources = False


def load_dependencies(optional=False):
    deps = list()
    if getattr(sys, 'frozen', False):
        pip_installed = os.path.join(BASE_DIR, ".pip_installed")
        if os.path.exists(pip_installed):
            with open(pip_installed) as f:
                exe_deps = json.loads("".join(f.readlines()))
        else:
            return deps
    if importlib or pkgresources:
        if optional:
            req_path = os.path.join(BASE_DIR, "optional-requirements.txt")
        else:
            req_path = os.path.join(BASE_DIR, "requirements.txt")
        if os.path.exists(req_path):
            with open(req_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#') or line.startswith('git'):
                        continue
                    res = re.match(r'(.*?)([<=>\s]+)([\d\.]+),?\s?([<=>\s]+)?([\d\.]+)?(?:\s?;\s?'
                                   r'(?:(python_version)\s?([<=>]+)\s?\'([\d\.]+)\'|'
                                   r'(sys_platform)\s?([\!=]+)\s?\'([\w]+)\'))?', line)
                    try:
                        if getattr(sys, 'frozen', False):
                            dep_version = exe_deps[res.group(1).lower().replace('_', '-')]
                        else:
                            if res.group(7) and res.group(8):
                                val = res.group(8).split(".")
                                current = (sys.version_info[0], sys.version_info[1])
                                required = (int(val[0]), int(val[1]) if len(val) > 1 else 0)
                                op = res.group(7).strip()
                                if not {
                                    '<': current < required,
                                    '<=': current <= required,
                                    '>': current > required,
                                    '>=': current >= required,
                                    '==': current == required,
                                    '!=': current != required,
                                }.get(op, current >= required):
                                    continue
                            elif res.group(10) and res.group(11):
                                # only installed if platform is eqal, don't check if platform is not equal
                                if res.group(10) == "==":
                                    if sys.platform != res.group(11):
                                        continue
                                # installed if platform is not eqal, don't check if platform is equal
                                elif res.group(10) == "!=":
                                    if sys.platform == res.group(11):
                                        continue
                            if importlib:
                                dep_version = version(res.group(1))
                            else:
                                dep_version = pkg_resources.get_distribution(res.group(1)).version
                    except (ImportNotFound, KeyError):
                        if optional:
                            continue
                        dep_version = "not installed"
                    deps.append([dep_version, res.group(1), res.group(2), res.group(3), res.group(4), res.group(5)])
    return deps


def dependency_check(optional=False):
    d = list()
    dep_version_int = None
    low_check = None
    deps = load_dependencies(optional)
    for dep in deps:
        try:
            dep_version_int = [int(x) if x.isnumeric() else 0 for x in dep[0].split('.')[:3]]
            low_check = [int(x) for x in dep[3].split('.')]
            high_check = [int(x) for x in dep[5].split('.')]
        except AttributeError:
            high_check = []
        except ValueError:
            d.append({'name': dep[1],
                      'target': "available",
                      'found': "Not available"
                      })
            continue

        if dep[2].strip() == "==":
            if dep_version_int != low_check:
                d.append({'name': dep[1],
                          'found': dep[0],
                          "target": dep[2] + dep[3]})
                continue
        elif dep[2].strip() == ">=":
            if dep_version_int < low_check:
                d.append({'name': dep[1],
                          'found': dep[0],
                          "target": dep[2] + dep[3]})
                continue
        elif dep[2].strip() == ">":
            if dep_version_int <= low_check:
                d.append({'name': dep[1],
                          'found': dep[0],
                          "target": dep[2] + dep[3]})
                continue
        if dep[4] and dep[5]:
            if dep[4].strip() == "<":
                if dep_version_int >= high_check:
                    d.append(
                        {'name': dep[1],
                         'found': dep[0],
                         "target": dep[4] + dep[5]})
                    continue
            elif dep[4].strip() == "<=":
                if dep_version_int > high_check:
                    d.append(
                        {'name': dep[1],
                         'found': dep[0],
                         "target": dep[4] + dep[5]})
                    continue
        elif dep[4] or dep[5]:
            logging.warning("Incomplete upper-bound version constraint for %s: operator=%r version=%r",
                            dep[1], dep[4], dep[5])
    return d
