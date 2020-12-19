import sys
import os.path
import imp
import ffi

import ullvm_c_conf
#ullvm_c_conf.init("/usr/lib/x86_64-linux-gnu/libLLVM-7.so")
from ullvm_c import *


i32_t = LLVMInt32Type()


def init_jit():
    LLVMInitializeX86TargetInfo()
    LLVMInitializeX86Target()
    LLVMInitializeX86TargetMC()
    LLVMInitializeX86AsmPrinter()


def compile_mod(mod):
    engine_ref = by_ref("P")
    errstr_ref = by_ref("s")

    res = LLVMCreateExecutionEngineForModule(engine_ref, mod, errstr_ref)
    assert not res
    #print("CreateExecutionEngine:", res, errstr_ref[0])
    engine = engine_ref[0]
    return engine


def import_llvm_bc(path):
    my_path = path + ".bc"
    if not os.path.isfile(my_path):
        return _old_hook(path) if _old_hook else None

    with open(my_path, "rb") as f:
        bc = f.read()

    buf = LLVMCreateMemoryBufferWithMemoryRangeCopy(bc, len(bc), my_path)
    #print(buf)

    llmod = LLVMParseBitcode2(buf)
    #print("llmod:", llmod)

    LLVMDumpModule(llmod)
    print()

    engine = compile_mod(llmod)

    pymod = imp.new_module("__llvm__")

    f = LLVMGetFirstFunction(llmod)
    while f:
        f_name = LLVMGetValueName(f)
        num_params = LLVMCountParams(f)
        #print(f_name, num_params)
        for i in range(num_params):
            param = LLVMGetParam(f, i)
            #print(" ", LLVMGetValueName(param), LLVMPrintTypeToString(LLVMTypeOf(param)), LLVMTypeOf(param) == i32_t)
            assert LLVMTypeOf(param) == i32_t

        addr = LLVMGetFunctionAddress(engine, f_name)
        #print("func addr:", f_name, addr)
        fun_obj = ffi.func("i", addr, "i" * num_params)
        setattr(pymod, f_name, fun_obj)

        f = LLVMGetNextFunction(f)

    return pymod


init_jit()

if __name__ == "__main__":
    pymod = import_llvm_bc(sys.argv[1])
    print(pymod.sum(5, 10))
else:
    _old_hook = sys.set_import_hook(import_llvm_bc, ("bc",))
