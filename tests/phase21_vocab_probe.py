"""Owned model-free C API grammar QA. No context, logits or inference is computed."""
import ctypes as c,json,math,resource
import contextlib,io
# C API declarations: llama.cpp b11750 (MIT), include/llama.h at
# dd002b91f583af0b80140f9a140dc04856bfc2e0, SHA256
# 961430f89e2553dbcd99e3e6c59826af9ec143f05911520c74f804d986ff3cd2.
from pathlib import Path
class Params(c.Structure):
 _fields_=[('devices',c.c_void_p),('tensor_buft_overrides',c.c_void_p),('n_gpu_layers',c.c_int32),('split_mode',c.c_int),('load_mode',c.c_int),('lazy_mode',c.c_int),('main_gpu',c.c_int32),('tensor_split',c.c_void_p),('progress_callback',c.c_void_p),('progress_callback_user_data',c.c_void_p),('kv_overrides',c.c_void_p),('vocab_only',c.c_bool),('check_tensors',c.c_bool),('use_extra_bufts',c.c_bool),('no_host',c.c_bool),('no_alloc',c.c_bool),('load_mtp',c.c_bool)]
class Token(c.Structure):_fields_=[('id',c.c_int32),('logit',c.c_float),('p',c.c_float)]
class Array(c.Structure):_fields_=[('data',c.POINTER(Token)),('size',c.c_size_t),('selected',c.c_int64),('sorted',c.c_bool)]
def boundary():
 capture=io.StringIO()
 with contextlib.redirect_stdout(capture):exec(Path('/workspace/boundary.py').read_text(),{})
 return json.loads(capture.getvalue())
before=boundary()
lib=c.CDLL('/opt/qwen/llama-b11750/libllama.so')
def bind(name,args,result):
 f=getattr(lib,name);f.argtypes=args;f.restype=result;return f
init=bind('llama_backend_init',[],None)
defaults=bind('llama_model_default_params',[],Params)
load=bind('llama_model_load_from_file',[c.c_char_p,Params],c.c_void_p)
vocabof=bind('llama_model_get_vocab',[c.c_void_p],c.c_void_p)
tokenize=bind('llama_tokenize',[c.c_void_p,c.c_char_p,c.c_int32,c.POINTER(c.c_int32),c.c_int32,c.c_bool,c.c_bool],c.c_int32)
eos=bind('llama_vocab_eos',[c.c_void_p],c.c_int32)
grammar=bind('llama_sampler_init_grammar',[c.c_void_p,c.c_char_p,c.c_char_p],c.c_void_p)
apply=bind('llama_sampler_apply',[c.c_void_p,c.POINTER(Array)],None)
accept=bind('llama_sampler_accept',[c.c_void_p,c.c_int32],None)
free=bind('llama_sampler_free',[c.c_void_p],None)
model_free=bind('llama_model_free',[c.c_void_p],None)
init();params=defaults();params.vocab_only=True;params.n_gpu_layers=0
model=load(b'/opt/qwen/model.gguf',params)
if not model:raise RuntimeError('VOCAB_LOAD_FAILED')
vocab=vocabof(model)
def admits(rule,text):
 sampler=grammar(vocab,rule.encode(),b'root')
 if not sampler:raise RuntimeError('GRAMMAR_COMPILATION_FAILED')
 try:
  raw=text.encode();tokens=(c.c_int32*4096)();n=tokenize(vocab,raw,len(raw),tokens,4096,False,True)
  if not 0<n<=4096:raise ValueError('BOUNDED_TOKENIZATION_FAILED')
  for tid in [*tokens[:n],eos(vocab)]:
   row=Token(tid,0.0,1.0);arr=Array(c.pointer(row),1,-1,False);apply(sampler,c.byref(arr))
   if not math.isfinite(row.logit):return False
   accept(sampler,tid)
  return True
 finally:free(sampler)
try:
 data=json.loads(Path('/workspace/cases.json').read_text());rows=[]
 for name,rule in data['grammars'].items():
  for case in data['witnesses']:
   rows.append({'grammar':name,'witness':case['name'],'accepted':admits(rule,case['text'])})
 print(json.dumps({'kind':'MODEL_FREE_VOCABULARY_GRAMMAR_QA','vocab_only':True,'model_weights_loaded':False,'model_forward_passes':0,'model_requests':0,'rows':rows,'boundary_before':before,'boundary_after':boundary(),'abi_model_params_bytes':c.sizeof(Params),'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024}))
finally:model_free(model)
