"""Trusted JSON bridge. No candidate module, pickle or code is imported here."""
import builtins
import collections.abc
import inspect
import json
import math
import os
from pathlib import Path
import select
import subprocess
import sys
import time
import types
import warnings

MAX=1_000_000
ACTIVE=None
CLASSES={}
ROOT=None
ERRORS={name:getattr(builtins,name) for name in ('Exception','AssertionError','AttributeError','TypeError','ValueError',
    'KeyError','IndexError','RuntimeError','StopIteration','OSError','FileNotFoundError','PermissionError','FileExistsError',
    'NotImplementedError','ZeroDivisionError')}


class BridgeError(RuntimeError):pass


def require(condition):
    if not condition:raise BridgeError('candidate protocol/policy violation')


class Remote:
    def __getattr__(self,name):return ACTIVE.request('get',self,name=name)
    def __setattr__(self,name,value):
        try:object.__getattribute__(self,'_rid');remote=True
        except AttributeError:remote=False
        if name=='_rid' or not remote:object.__setattr__(self,name,value)
        else:ACTIVE.request('set',self,name=name,args=[value])
    def __call__(self,*args,**kw):return ACTIVE.request('call',self,args=args,kwargs=kw)
    def __repr__(self):return ACTIVE.request('repr',self)
    def __bool__(self):return ACTIVE.request('bool',self)
    def __len__(self):return ACTIVE.request('len',self)
    def __hash__(self):return ACTIVE.request('hash',self)
    def __iter__(self):return ACTIVE.request('iter',self)
    def __next__(self):return ACTIVE.request('next',self)
    def __getitem__(self,key):return ACTIVE.request('getitem',self,args=[key])
    def __setitem__(self,key,value):ACTIVE.request('setitem',self,args=[key,value])
    def __delitem__(self,key):ACTIVE.request('delitem',self,args=[key])
    def __contains__(self,key):return ACTIVE.request('contains',self,args=[key])
    def __eq__(self,other):return ACTIVE.request('eq',self,args=[other])
    def __ne__(self,other):return ACTIVE.request('ne',self,args=[other])
    def __lt__(self,other):return ACTIVE.request('lt',self,args=[other])
    def __le__(self,other):return ACTIVE.request('le',self,args=[other])
    def __gt__(self,other):return ACTIVE.request('gt',self,args=[other])
    def __ge__(self,other):return ACTIVE.request('ge',self,args=[other])
    def __and__(self,other):return ACTIVE.request('and',self,args=[other])
    def __or__(self,other):return ACTIVE.request('or',self,args=[other])
    def __invert__(self):return ACTIVE.request('invert',self)
    def __enter__(self):return self.__getattr__('__enter__')()
    def __exit__(self,*args):return self.__getattr__('__exit__')(*args)


class ProxyMeta(type):
    def __getattr__(cls,name):
        return getattr(ACTIVE.symbol(*cls._symbol),name)
    def __call__(cls,*args,**kwargs):
        local=cls.__module__.startswith('tests.')
        if local and cls._symbol[1]=='Storage':
            if not all(any(n in b.__dict__ for b in cls.__mro__ if b.__module__.startswith('tests.')) for n in ('read','write')):raise TypeError('abstract storage')
            return type.__call__(cls,*args,**kwargs)
        if local and cls._symbol[1]=='Middleware':
            instance=object.__new__(cls)
            methods={name for name,fn in cls.__dict__.items() if inspect.isfunction(fn) and not name.startswith('_')}
            require(methods and all(Path(cls.__dict__[n].__code__.co_filename).resolve().is_relative_to(ROOT) for n in methods))
            key=id(instance);ACTIVE.host[key]=instance;ACTIVE.host_methods[key]=methods
            value=ACTIVE.request('subclass',ACTIVE.symbol(*cls._symbol),args=args,kwargs=kwargs,
                                 overrides={name:key for name in methods})
            object.__setattr__(instance,'_rid',object.__getattribute__(value,'_rid'))
            ACTIVE.cache[instance._rid]=instance
            return instance
        value=ACTIVE.symbol(*cls._symbol)(*args,**kwargs)
        if local and cls._symbol[1]=='Query':
            ACTIVE.overrides['Query']=cls
            object.__setattr__(value,'__class__',cls)
        return value
    def __instancecheck__(cls,value):
        return isinstance(value,Remote) and any(b.__name__==cls.__name__ for b in type(value).__mro__)


class StorageBase:
    def __init__(self,*a,**kw):pass
    def close(self):pass


class Session:
    def __init__(self,process,scratch,timeout=10):
        self.process=process;self.scratch=Path(scratch).resolve();self.timeout=timeout
        self.seq=0;self.cache={};self.host={};self.host_methods={};self.overrides={}
        self.buffer=b'';self.symbols={}
        self.poisoned=False
        require(process.stdin is not None and process.stdout is not None)
    def close(self):
        timed_out=False
        try:self.process.stdin.close()
        except OSError:pass
        try:code=self.process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            timed_out=True;self.process.kill();code=self.process.wait(timeout=5)
        trailing=self.buffer
        eof=False;deadline=time.monotonic()+1
        while time.monotonic()<deadline and len(trailing)<=MAX:
            if not select.select([self.process.stdout],[],[],max(0,deadline-time.monotonic()))[0]:break
            chunk=os.read(self.process.stdout.fileno(),65536)
            if not chunk:eof=True;break
            trailing+=chunk
        if trailing or not eof:self.poisoned=True
        self.process.stdout.close()
        return {'worker_exit_status':code,'worker_timed_out':timed_out}
    def _receive(self):
        deadline=time.monotonic()+self.timeout
        while b'\n' not in self.buffer:
            remaining=deadline-time.monotonic()
            require(remaining>0 and select.select([self.process.stdout],[],[],remaining)[0])
            chunk=os.read(self.process.stdout.fileno(),65536)
            require(chunk and len(self.buffer)+len(chunk)<=MAX)
            self.buffer+=chunk
        line,self.buffer=self.buffer.split(b'\n',1)
        try:value=json.loads(line)
        except (ValueError,TypeError,RecursionError):raise BridgeError('malformed candidate data') from None
        require(isinstance(value,dict))
        return value
    def _send(self,value):
        raw=json.dumps(value,ensure_ascii=True,separators=(',',':'),allow_nan=False).encode()+b'\n'
        require(len(raw)<=MAX)
        try:self.process.stdin.write(raw);self.process.stdin.flush()
        except (OSError,ValueError):raise BridgeError('candidate process ended') from None
    def symbol(self,module,name):
        key=(module,name)
        if key not in self.symbols:self.symbols[key]=self.request('symbol',module=module,name=name)
        return self.symbols[key]
    def request(self,op,target=None,**fields):
        require(not self.poisoned)
        try:return self._request(op,target,**fields)
        except (BridgeError,RecursionError,MemoryError):
            self.poisoned=True
            raise BridgeError('candidate protocol/policy violation') from None
    def _request(self,op,target=None,**fields):
        self.seq+=1;ident=self.seq
        value={'id':ident,'op':op}
        if target is not None:value['target']=object.__getattribute__(target,'_rid')
        for key,item in fields.items():
            if key=='args':value[key]=[self.pack(v) for v in item]
            elif key=='kwargs':value[key]={k:self.pack(v) for k,v in item.items()}
            else:value[key]=item
        self._send(value)
        while True:
            reply=self._receive()
            if reply.get('kind')=='callback':
                self.callback(reply);continue
            require(reply.get('kind')=='result' and type(reply.get('id')) is int and reply['id']==ident)
            notices=reply.get('warnings',[])
            require(isinstance(notices,list) and len(notices)<=100)
            for w in notices:
                require(isinstance(w,dict) and isinstance(w.get('type'),str) and isinstance(w.get('message'),str))
                cls=getattr(builtins,w.get('type',''),None)
                require(isinstance(cls,type) and issubclass(cls,Warning) and len(w.get('message',''))<3000)
                warnings.warn(w['message'],cls,stacklevel=2)
            if 'error' in reply:
                error=reply['error']
                require(isinstance(error,dict))
                name=error.get('type')
                require(isinstance(name,str) and isinstance(error.get('message'),str))
                if name=='JSONDecodeError':
                    require(isinstance(error.get('doc'),str) and type(error.get('pos')) is int and len(error['doc'])<100000)
                    raise json.JSONDecodeError(error['message'],error['doc'],error['pos'])
                cls=ERRORS.get(name)
                require(cls is not None and len(error['message'])<3000)
                raise cls(error.get('message','candidate exception'))
            require('value' in reply)
            return self.unpack(reply['value'])
    def pack(self,value,depth=0):
        require(depth<=30)
        if isinstance(value,int) and type(value) is not bool:value=int(value)
        if type(value) is float and not math.isfinite(value):return {'kind':'float-special','value':'nan' if math.isnan(value) else ('inf' if value>0 else '-inf')}
        if value is None or type(value) in (str,int,float,bool):return {'kind':'value','value':value}
        if isinstance(value,Remote):
            try:return {'kind':'remote','id':object.__getattribute__(value,'_rid')}
            except AttributeError:return self.register(value)
        if isinstance(value,ProxyMeta):
            if value.__module__.startswith('tests.'):
                return self.register(value)
            return self.pack(self.symbol(*value._symbol),depth+1)
        if value in (int,str,bool,float,len) if isinstance(value,type) or inspect.isbuiltin(value) else False:
            return {'kind':'builtin','name':value.__name__}
        if isinstance(value,Path):return {'kind':'value','value':str(value)}
        if type(value) is tuple:return {'kind':'tuple','items':[self.pack(v,depth+1) for v in value]}
        if type(value) is frozenset:return {'kind':'frozenset','items':[self.pack(v,depth+1) for v in value]}
        if type(value) is set:return {'kind':'set','items':[self.pack(v,depth+1) for v in value]}
        if isinstance(value,collections.abc.Mapping):
            if type(value) is not dict and type(value).__module__.startswith('tests.'):
                record=self.register(value);record['mapping']=True;return record
            return {'kind':'dict','items':[[self.pack(k,depth+1),self.pack(v,depth+1)] for k,v in value.items()]}
        if isinstance(value,list):return {'kind':'list','items':[self.pack(v,depth+1) for v in value]}
        if isinstance(value,collections.abc.Iterator):return self.pack(list(value),depth+1)
        if type(value) is type and issubclass(value,BaseException):
            return {'kind':'exception_type','name':value.__name__}
        if inspect.isfunction(value) or isinstance(value,type):return self.register(value)
        if value is NotImplemented:return {'kind':'notimplemented'}
        if type(value).__module__.startswith('tests.'):return self.register(value)
        return {'kind':'opaque'}
    def register(self,value):
        require(inspect.isfunction(value) or getattr(value,'__module__',type(value).__module__).startswith('tests.'))
        if inspect.isfunction(value):
            require(ROOT is not None and Path(value.__code__.co_filename).resolve().is_relative_to(ROOT))
        key=id(value);self.host[key]=value
        methods={'__hash__','__eq__'}
        is_callable=callable(value)
        if isinstance(value,Remote):is_callable=False
        if is_callable:methods.add('__call__')
        if inspect.isfunction(value) and hasattr(value,'is_cacheable'):methods.add('is_cacheable')
        if not isinstance(value,type) and not inspect.isfunction(value):methods|={'read','write','close'}
        if isinstance(value,collections.abc.Mapping):methods|={'__getitem__','__len__','keys'}
        self.host_methods[key]=methods
        return {'kind':'host','id':key,'callable':is_callable,'hashable':type(value).__hash__ is not None}
    def unpack(self,value,depth=0):
        require(isinstance(value,dict) and depth<=30)
        kind=value.get('kind')
        require(isinstance(kind,str))
        if kind=='float-special':
            require(value.get('value') in ('nan','inf','-inf'));return float(value['value'])
        if kind=='value':
            item=value.get('value');require(item is None or type(item) in (str,int,float,bool))
            require(type(item) is not float or math.isfinite(item))
            return item
        if kind in ('tuple','frozenset','list'):
            require(isinstance(value.get('items'),list) and len(value['items'])<=10000)
            items=[self.unpack(v,depth+1) for v in value['items']]
            return {'tuple':tuple,'frozenset':frozenset,'list':list}[kind](items)
        if kind=='dict':
            require(isinstance(value.get('items'),list) and len(value['items'])<=10000)
            require(all(isinstance(v,list) and len(v)==2 for v in value['items']))
            return {self.unpack(k,depth+1):self.unpack(v,depth+1) for k,v in value['items']}
        if kind=='notimplemented':return NotImplemented
        if kind=='host':
            require(type(value.get('id')) is int and value['id'] in self.host)
            return self.host[value['id']]
        require(kind=='remote' and type(value.get('id')) is int and 0<value['id']<1_000_000)
        key=value['id']
        if key not in self.cache:
            name=value.get('type','');shape=value.get('shape')
            require(shape in ('object','dict','list','iterator') and isinstance(name,str) and len(name)<100)
            cls=self.overrides.get(name,CLASSES.get(name,Remote))
            instance=object.__new__(cls);object.__setattr__(instance,'_rid',key);self.cache[key]=instance
        return self.cache[key]
    def callback(self,message):
        require(type(message.get('id')) is int and type(message.get('target')) is int)
        key=message['target'];method=message.get('method')
        require(isinstance(method,str) and isinstance(message.get('args'),list) and isinstance(message.get('kwargs'),dict))
        require(key in self.host and method in self.host_methods[key])
        args=[self.unpack(v) for v in message.get('args',[])]
        kwargs={k:self.unpack(v) for k,v in message.get('kwargs',{}).items()}
        require(len(args)<=20 and len(kwargs)<=20)
        reply={'kind':'callback_result','id':message['id']}
        try:
            target=self.host[key]
            if isinstance(target,type):
                # A candidate may invoke only this registered fixture constructor;
                # filenames must stay inside the shared fixture filesystem.
                for v in [*args,*kwargs.values()]:
                    require(isinstance(v,(str,Path)))
                    try:inside=Path(v).resolve().is_relative_to(self.scratch)
                    except (OSError,ValueError):inside=False
                    require(inside)
            try:
                import authority_fs as filesystem
            except ImportError:
                from . import authority_fs as filesystem
            filesystem.enter()
            try:
                if method=='__call__':result=target(*args,**kwargs)
                elif method=='__hash__':result=hash(target)
                elif method=='__eq__':result=target==args[0]
                else:result=getattr(target,method)(*args,**kwargs)
                if method=='keys':result=list(result)
            finally:filesystem.leave()
            reply.update(value=self.pack(result),mutated_args=[self.pack(v) for v in args])
        except Exception as error:
            name=type(error).__name__
            require(getattr(builtins,name,None) is type(error))
            reply['error']={'type':name,'message':str(error)[:2000]}
        self._send(reply)


SYMBOLS={
 'tinydb':('TinyDB','Query','where','JSONStorage','Storage'),
 'tinydb.queries':('Query','QueryInstance','where'),
 'tinydb.table':('Table','Document'),
 'tinydb.storages':('Storage','JSONStorage','MemoryStorage','touch'),
 'tinydb.middlewares':('Middleware','CachingMiddleware'),
 'tinydb.operations':('delete','increment','decrement','add','subtract','set'),
 'tinydb.utils':('LRUCache','freeze','FrozenDict'),
}
FUNCTIONS={'where','touch','delete','increment','decrement','add','subtract','set','freeze'}


def install(session,trusted_root):
    global ACTIVE,ROOT
    ACTIVE=session;ROOT=Path(trusted_root).resolve()
    for module,names in SYMBOLS.items():
        stub=types.ModuleType(module);stub.__path__=[];stub.__file__=__file__
        for name in names:
            if name in FUNCTIONS:
                def invoke(*args,_module=module,_name=name,**kw):return ACTIVE.symbol(_module,_name)(*args,**kw)
                setattr(stub,name,invoke)
            else:
                if name not in CLASSES:
                    bases=(StorageBase,Remote) if name=='Storage' else (Remote,)
                    CLASSES[name]=ProxyMeta(name,bases,{'_symbol':(module,name),'__module__':module})
                setattr(stub,name,CLASSES[name])
        sys.modules[module]=stub
        if '.' in module:setattr(sys.modules['tinydb'],module.split('.')[1],stub)
