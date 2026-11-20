"""Trusted fixture I/O guard. Worker-writable symlinks never reach verifier files.

This mediates immutable trusted tests/callbacks; it is NOT a Python sandbox.
Candidate Python runs in another OS namespace and never imports this module.
"""
import builtins
import io
import os
import errno

DEPTH=0
SCRATCH=None
VIOLATIONS=0
OPEN=builtins.open
IO_OPEN=io.open
OS_OPEN=os.open


def enter():
    global DEPTH
    DEPTH+=1


def leave():
    global DEPTH
    DEPTH-=1


def denied():
    global VIOLATIONS
    VIOLATIONS+=1
    raise PermissionError('trusted fixture filesystem policy violation')


def _path(value):
    if isinstance(value,int):
        if DEPTH:denied()
        return None
    name=os.path.abspath(os.fspath(value))
    if name==SCRATCH or name.startswith(SCRATCH+os.sep):return name
    if DEPTH:denied()
    return None


def descriptor(path,flags,mode=0o666):
    relative=os.path.relpath(path,SCRATCH)
    parts=relative.split(os.sep)
    if any(p in ('','..','.') for p in parts):denied()
    fd=OS_OPEN(SCRATCH,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
    try:
        for part in parts[:-1]:
            following=OS_OPEN(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=fd)
            os.close(fd);fd=following
        return OS_OPEN(parts[-1],flags|os.O_NOFOLLOW|os.O_CLOEXEC,mode,dir_fd=fd)
    except OSError as error:
        if error.errno in (errno.ELOOP,errno.ENOTDIR):denied()
        raise
    finally:os.close(fd)


def safe_open(file,mode='r',buffering=-1,encoding=None,errors=None,newline=None,closefd=True,opener=None):
    path=_path(file)
    if path is None:return OPEN(file,mode,buffering,encoding,errors,newline,closefd,opener)
    if opener is not None or not closefd:
        if DEPTH:denied()
        return OPEN(file,mode,buffering,encoding,errors,newline,closefd,opener)
    flags=os.O_RDWR if '+' in mode else (os.O_RDONLY if 'r' in mode else os.O_WRONLY)
    if 'w' in mode:flags|=os.O_CREAT|os.O_TRUNC
    if 'a' in mode:flags|=os.O_CREAT|os.O_APPEND
    if 'x' in mode:flags|=os.O_CREAT|os.O_EXCL
    fd=descriptor(path,flags)
    try:return OPEN(fd,mode,buffering,encoding,errors,newline,True)
    except BaseException:
        os.close(fd);raise


def safe_os_open(path,flags,mode=0o777,*,dir_fd=None):
    if dir_fd is not None:
        if DEPTH:denied()
        return OS_OPEN(path,flags,mode,dir_fd=dir_fd)
    checked=_path(path)
    return OS_OPEN(path,flags,mode) if checked is None else descriptor(checked,flags,mode)


def install(scratch):
    global SCRATCH
    SCRATCH=os.path.abspath(os.fspath(scratch))
    builtins.open=safe_open;io.open=safe_open;os.open=safe_os_open
