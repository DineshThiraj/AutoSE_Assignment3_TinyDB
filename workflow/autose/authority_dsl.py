"""Fail-closed generated-test interpreter. No eval/exec/import of candidate tests."""
import ast
import operator
import itertools

try:
    from .authority_bridge import Remote, BridgeError
except ImportError:
    from authority_bridge import Remote, BridgeError

def limited(value):
    values=list(itertools.islice(iter(value),1001))
    if len(values)>1000:raise BridgeError('generated iterable budget')
    return values


PURE={'len':len,'list':lambda v=():limited(v),'tuple':lambda v=():tuple(limited(v)),
      'set':lambda v=():set(limited(v)),'sorted':lambda v:sorted(limited(v)),
      'all':lambda v:all(limited(v)),'any':lambda v:any(limited(v)),'sum':lambda v:sum(limited(v))}
DATA_METHODS={'get','keys','values','items','append','extend','count','index','copy'}
ALLOWED=(ast.Module,ast.ImportFrom,ast.Import,ast.alias,ast.FunctionDef,ast.arguments,ast.arg,
         ast.Assign,ast.Assert,ast.Expr,ast.Return,ast.Name,ast.Load,ast.Store,ast.Constant,
         ast.Call,ast.keyword,ast.Attribute,ast.Subscript,ast.List,ast.Tuple,ast.Dict,ast.Set,
         ast.Compare,ast.Eq,ast.NotEq,ast.Lt,ast.LtE,ast.Gt,ast.GtE,ast.In,ast.NotIn,ast.Is,ast.IsNot,
         ast.UnaryOp,ast.Not,ast.USub,ast.UAdd,ast.Invert,ast.BinOp,ast.BitAnd,ast.BitOr,ast.Add,ast.Sub,
         ast.BoolOp,ast.And,ast.Or,ast.ListComp,ast.GeneratorExp,ast.comprehension)
COMPARE={ast.Eq:operator.eq,ast.NotEq:operator.ne,ast.Lt:operator.lt,ast.LtE:operator.le,
         ast.Gt:operator.gt,ast.GtE:operator.ge,ast.In:lambda a,b:a in b,ast.NotIn:lambda a,b:a not in b,
         ast.Is:operator.is_,ast.IsNot:operator.is_not}
BINARY={ast.BitAnd:operator.and_,ast.BitOr:operator.or_,ast.Add:operator.add,ast.Sub:operator.sub}


def check(source):
    if len(source.encode())>150000:raise BridgeError('generated test size')
    tree=ast.parse(source)
    for node in ast.walk(tree):
        if not isinstance(node,ALLOWED):raise BridgeError('unsupported generated test syntax')
        if isinstance(node,ast.Attribute) and node.attr.startswith('_'):raise BridgeError('private generated attribute')
        if isinstance(node,ast.Name) and node.id.startswith('_'):raise BridgeError('private generated name')
        if isinstance(node,ast.Name) and node.id in {'exec','eval','open','getattr','setattr','delattr','globals','locals','vars','compile','breakpoint','type','object','input'}:
            raise BridgeError('generated capability denied')
    imports={}
    functions=[]
    for node in tree.body:
        if isinstance(node,ast.ImportFrom):
            if node.level or node.module not in ('tinydb','tinydb.storages'):raise BridgeError('generated import denied')
            for entry in node.names:
                if entry.name not in ('Query','where','TinyDB','MemoryStorage','JSONStorage'):raise BridgeError('generated symbol denied')
                imports[entry.asname or entry.name]=(node.module,entry.name)
        elif isinstance(node,ast.FunctionDef):
            if not node.name.startswith('test_') or node.decorator_list or node.returns or node.args.defaults or node.args.kwonlyargs or node.args.vararg or node.args.kwarg or node.args.posonlyargs:
                raise BridgeError('generated function policy')
            if [a.arg for a in node.args.args]!=['db'] or any(a.annotation for a in node.args.args):raise BridgeError('generated fixture policy')
            if not any(isinstance(s,ast.Assert) for s in ast.walk(node)):raise BridgeError('generated assertion missing')
            functions.append(node)
        else:raise BridgeError('generated top-level execution denied')
    if not functions or len({f.name for f in functions})!=len(functions):raise BridgeError('generated collection invalid')
    return imports,functions


class Evaluator:
    def __init__(self,environment):
        self.env=dict(environment);self.steps=0
        self.approved=list(PURE.values())+[v for k,v in environment.items() if k!='db']
    def step(self):
        self.steps+=1
        if self.steps>10000:raise BridgeError('generated evaluation budget')
    def assign(self,target,value):
        if isinstance(target,ast.Name):self.env[target.id]=value
        elif isinstance(target,(ast.Tuple,ast.List)):
            values=list(value)
            if len(values)!=len(target.elts):raise BridgeError('generated unpack mismatch')
            for name,v in zip(target.elts,values):self.assign(name,v)
        else:raise BridgeError('generated assignment target denied')
    def expr(self,node):
        result=self._expr(node)
        if type(result) in (str,bytes,list,tuple,dict,set) and len(result)>10000:raise BridgeError('generated value size')
        if type(result) is int and result.bit_length()>4096:raise BridgeError('generated integer size')
        return result
    def _expr(self,node):
        self.step()
        if isinstance(node,ast.Constant):return node.value
        if isinstance(node,ast.Name):
            if node.id in self.env:return self.env[node.id]
            if node.id in PURE:return PURE[node.id]
            raise BridgeError('unknown generated name')
        if isinstance(node,(ast.List,ast.Tuple,ast.Set)):
            values=[self.expr(e) for e in node.elts]
            return {ast.List:list,ast.Tuple:tuple,ast.Set:set}[type(node)](values)
        if isinstance(node,ast.Dict):return {self.expr(k):self.expr(v) for k,v in zip(node.keys,node.values)}
        if isinstance(node,ast.Attribute):
            value=self.expr(node.value)
            if not isinstance(value,Remote) and (type(value) not in (dict,list,tuple,str) or node.attr not in DATA_METHODS):
                raise BridgeError('generated attribute receiver denied')
            return getattr(value,node.attr)
        if isinstance(node,ast.Subscript):return self.expr(node.value)[self.expr(node.slice)]
        if isinstance(node,ast.Call):
            fn=self.expr(node.func)
            if not isinstance(fn,Remote) and not any(fn is x for x in self.approved):
                owner=getattr(fn,'__self__',None)
                if type(owner) not in (dict,list,tuple,str) or getattr(fn,'__name__','') not in DATA_METHODS:raise BridgeError('generated call denied')
            args=[self.expr(v) for v in node.args]
            kw={v.arg:self.expr(v.value) for v in node.keywords}
            if None in kw:raise BridgeError('generated keyword expansion denied')
            if getattr(fn,'__name__','')=='extend' and not isinstance(fn,Remote):
                if len(args)!=1 or type(args[0]) not in (list,tuple):raise BridgeError('generated extension denied')
            return fn(*args,**kw)
        if isinstance(node,ast.Compare):
            left=self.expr(node.left)
            result=True
            for i,(op,right) in enumerate(zip(node.ops,node.comparators)):
                value=self.expr(right)
                result=COMPARE[type(op)](left,value)
                if i<len(node.ops)-1 and not result:return result
                left=value
            return result
        if isinstance(node,ast.UnaryOp):
            return {ast.Not:operator.not_,ast.USub:operator.neg,ast.UAdd:operator.pos,ast.Invert:operator.invert}[type(node.op)](self.expr(node.operand))
        if isinstance(node,ast.BinOp):return BINARY[type(node.op)](self.expr(node.left),self.expr(node.right))
        if isinstance(node,ast.BoolOp):
            for value in node.values:
                result=self.expr(value)
                if isinstance(node.op,ast.And) and not result:return result
                if isinstance(node.op,ast.Or) and result:return result
            return result
        if isinstance(node,(ast.ListComp,ast.GeneratorExp)):
            if len(node.generators)!=1 or node.generators[0].is_async:raise BridgeError('generated comprehension denied')
            g=node.generators[0];result=[]
            for i,value in enumerate(self.expr(g.iter)):
                if i>=1000:raise BridgeError('generated iterable budget')
                self.assign(g.target,value)
                if all(self.expr(c) for c in g.ifs):result.append(self.expr(node.elt))
            return result
        raise BridgeError('generated expression denied')
    def run(self,function):
        assertions=0
        for node in function.body:
            self.step()
            if isinstance(node,ast.Assign):
                value=self.expr(node.value)
                for target in node.targets:self.assign(target,value)
            elif isinstance(node,ast.Expr):self.expr(node.value)
            elif isinstance(node,ast.Assert):
                assertions+=1
                if not self.expr(node.test):raise AssertionError('generated acceptance assertion failed')
            elif isinstance(node,ast.Return):
                if node.value is not None:raise BridgeError('generated return value denied')
                if not assertions:raise BridgeError('generated assertion not executed')
                return
            else:raise BridgeError('generated statement denied')
        if not assertions:raise BridgeError('generated assertion not executed')
