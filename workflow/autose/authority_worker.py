"""JSON-only candidate-side adapter. This process is UNTRUSTED, never a verifier."""
import builtins
import collections.abc
import importlib
import json
import math
import sys
import warnings

MAX=1_000_000
objects={}
next_id=0
callback_id=0
CALLBACK_EXCEPTION=type('HostCallbackError',(Exception,),{})


def send(value):
    raw=json.dumps(value,ensure_ascii=True,separators=(',',':'))
    if len(raw)>MAX:raise ValueError('protocol size limit')
    sys.stdout.write(raw+'\n');sys.stdout.flush()


def receive():
    raw=sys.stdin.buffer.readline(MAX+1)
    if not raw or len(raw)>MAX or not raw.endswith(b'\n'):raise EOFError()
    return json.loads(raw)


def remember(value):
    global next_id
    for key,obj in objects.items():
        if obj is value:return key
    next_id+=1;objects[next_id]=value;return next_id


def pack(value,by_value=False,depth=0):
    if depth>30:raise ValueError('protocol depth limit')
    if type(value) is float and not math.isfinite(value):return {'kind':'float-special','value':'nan' if math.isnan(value) else ('inf' if value>0 else '-inf')}
    if value is None or type(value) in (str,int,float,bool):return {'kind':'value','value':value}
    if value is NotImplemented:return {'kind':'notimplemented'}
    if type(value) is tuple:return {'kind':'tuple','items':[pack(v,by_value,depth+1) for v in value]}
    if type(value) is frozenset:return {'kind':'frozenset','items':[pack(v,by_value,depth+1) for v in value]}
    if by_value and isinstance(value,dict):
        return {'kind':'dict','items':[[pack(k,True,depth+1),pack(v,True,depth+1)] for k,v in value.items()]}
    if by_value and isinstance(value,list):return {'kind':'list','items':[pack(v,True,depth+1) for v in value]}
    if isinstance(value,HostObject):return {'kind':'host','id':value._host_id}
    kind='object'
    if isinstance(value,dict):kind='dict'
    elif isinstance(value,list):kind='list'
    elif isinstance(value,collections.abc.Iterator):kind='iterator'
    module=type(value).__module__
    typename=type(value).__name__ if module.startswith('tinydb') else ''
    return {'kind':'remote','id':remember(value),'shape':kind,'type':typename}


def unpack(value):
    kind=value['kind']
    if kind=='value':return value['value']
    if kind=='float-special':return float(value['value'])
    if kind=='remote':return objects[value['id']]
    if kind=='builtin':return getattr(builtins,value['name'])
    if kind=='exception_type':return getattr(builtins,value['name'])
    if kind=='notimplemented':return NotImplemented
    if kind=='tuple':return tuple(unpack(x) for x in value['items'])
    if kind=='frozenset':return frozenset(unpack(x) for x in value['items'])
    if kind=='set':return set(unpack(x) for x in value['items'])
    if kind=='list':return [unpack(x) for x in value['items']]
    if kind=='dict':return {unpack(k):unpack(v) for k,v in value['items']}
    if kind=='opaque':return object()
    if kind=='host':
        cls=HostMapping if value.get('mapping') else (HostCallable if value.get('callable') else HostObject)
        if not value.get('hashable',True) and cls is HostObject:cls=HostUnhashable
        return cls(value['id'])
    raise ValueError('unsupported value')


class HostObject:
    def __init__(self,host_id):object.__setattr__(self,'_host_id',host_id)
    def _invoke(self,method,args=(),kwargs=None):
        global callback_id
        callback_id+=1
        ident=callback_id
        send({'kind':'callback','id':ident,'target':self._host_id,'method':method,
              'args':[pack(a,True) for a in args],'kwargs':{k:pack(v,True) for k,v in (kwargs or {}).items()}})
        reply=receive()
        while reply.get('kind')!='callback_result':
            dispatch(reply)
            reply=receive()
        if reply.get('kind')!='callback_result' or reply.get('id')!=ident:raise ValueError('callback sequence mismatch')
        if 'error' in reply:
            name=reply['error'].get('type')
            cls=getattr(builtins,name,ValueError)
            if not isinstance(cls,type) or not issubclass(cls,Exception):cls=ValueError
            raise cls(reply['error'].get('message','callback failed'))
        for original,new in zip(args,reply.get('mutated_args',[])):
            data=unpack(new)
            if isinstance(original,dict) and isinstance(data,dict):original.clear();original.update(data)
        return unpack(reply['value'])
    def __getattr__(self,name):
        if name not in ('read','write','close','is_cacheable'):raise AttributeError(name)
        return lambda *a,**kw:self._invoke(name,a,kw)
    def __hash__(self):return self._invoke('__hash__')
    def __eq__(self,other):return self._invoke('__eq__',(other,))


class HostMapping(HostObject,collections.abc.Mapping):
    __hash__=None
    def __getitem__(self,key):return self._invoke('__getitem__',(key,))
    def __iter__(self):return iter(self._invoke('keys'))
    def __len__(self):return self._invoke('__len__')


class HostCallable(HostObject):
    def __call__(self,*args,**kwargs):return self._invoke('__call__',args,kwargs)


class HostUnhashable(HostObject):
    __hash__=None


def operation(request):
    op=request['op']
    args=[unpack(v) for v in request.get('args',[])]
    kwargs={k:unpack(v) for k,v in request.get('kwargs',{}).items()}
    if op=='symbol':
        module=importlib.import_module(request['module'])
        return getattr(module,request['name'])
    obj=objects[request['target']]
    if op=='subclass':
        def override(name,key):
            def invoke(self,*a,**kw):return HostObject(key)._invoke(name,a,kw)
            return invoke
        cls=type('VerifierOverride',(obj,),{name:override(name,key) for name,key in request['overrides'].items()})
        return cls(*args,**kwargs)
    if op=='get':return getattr(obj,request['name'])
    if op=='set':setattr(obj,request['name'],args[0]);return None
    if op=='call':return obj(*args,**kwargs)
    if op=='method':return getattr(obj,request['name'])(*args,**kwargs)
    if op=='iter':return iter(obj)
    if op=='next':return next(obj)
    if op=='repr':return repr(obj)
    if op=='bool':return bool(obj)
    if op=='len':return len(obj)
    if op=='hash':return hash(obj)
    if op=='getitem':return obj[args[0]]
    if op=='setitem':obj[args[0]]=args[1];return None
    if op=='delitem':del obj[args[0]];return None
    if op=='contains':return args[0] in obj
    if op in ('eq','ne','lt','le','gt','ge','and','or','invert'):
        import operator
        return getattr(operator,{'and':'and_','or':'or_','invert':'invert'}.get(op,op))(obj,*args)
    raise ValueError('unsupported operation')


def dispatch(request):
    try:
        with warnings.catch_warnings(record=True) as observed:
            warnings.simplefilter('always')
            result=pack(operation(request))
        send({'kind':'result','id':request['id'],'value':result,
              'warnings':[{'type':type(w.message).__name__,'message':str(w.message)} for w in observed]})
    except BaseException as error:
        info={'type':type(error).__name__,'message':str(error)[:2000]}
        if isinstance(error,json.JSONDecodeError):info.update(doc=error.doc,pos=error.pos)
        send({'kind':'result','id':request['id'],'error':info})


def main():
    sys.path.insert(0,sys.argv[1])
    while True:
        try:request=receive()
        except EOFError:return
        dispatch(request)


if __name__=='__main__':main()
