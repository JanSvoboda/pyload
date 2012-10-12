#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import inspect
import sys
from os.path import abspath, dirname, join

path = dirname(abspath(__file__))
module = join(path, "..", "..")

sys.path.append(join(module, "lib"))
sys.path.append(join(module, "remote"))

from thrift.Thrift import TType
from thriftgen.pyload import ttypes
from thriftgen.pyload import Pyload

type_map = {
    TType.BOOL: 'bool',
    TType.DOUBLE: 'float',
    TType.I16: 'int',
    TType.I32: 'int',
    TType.I64: 'int',
    TType.STRING: 'basestring',
    TType.MAP: 'dict',
    TType.LIST: 'list',
    TType.SET: 'set',
    TType.VOID: 'None',
    TType.STRUCT: 'BaseObject',
    TType.UTF8: 'unicode',
}

def get_spec(spec, optional=False):
    """ analyze the generated spec file and writes information into file """
    if spec[1] == TType.STRUCT:
        return spec[3][0].__name__
    elif spec[1]  == TType.LIST:
        if spec[3][0] == TType.STRUCT:
            ttype = spec[3][1][0].__name__
        else:
            ttype = type_map[spec[3][0]]
        return "(list, %s)" % ttype
    elif spec[1] == TType.MAP:
        if spec[3][2] == TType.STRUCT:
            ttype = spec[3][3][0].__name__
        else:
            ttype = type_map[spec[3][2]]

        return "(dict, %s, %s)" % (type_map[spec[3][0]], ttype)
    else:
        return type_map[spec[1]]

optional_re = "%d: +optional +[a-z0-9<>_-]+ +%s"

def main():

    enums = []
    classes = []
    tf = open(join(path, "pyload.thrift"), "rb").read()

    print "generating lightweight ttypes.py"

    for name in dir(ttypes):
        klass = getattr(ttypes, name)

        if name in ("TBase", "TExceptionBase") or name.startswith("_") or not (issubclass(klass, ttypes.TBase) or issubclass(klass, ttypes.TExceptionBase)):
            continue

        if hasattr(klass, "thrift_spec"):
           classes.append(klass)
        else:
            enums.append(klass)


    f = open(join(path, "ttypes.py"), "wb")
    f.write(
        """#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Autogenerated by pyload
# DO NOT EDIT UNLESS YOU ARE SURE THAT YOU KNOW WHAT YOU ARE DOING

class BaseObject(object):
\t__slots__ = []

""")

    dev = open(join(path, "ttypes_debug.py"), "wb")
    dev.write("""#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Autogenerated by pyload
# DO NOT EDIT UNLESS YOU ARE SURE THAT YOU KNOW WHAT YOU ARE DOING\n
from ttypes import *\n
""")

    ## generate enums
    for enum in enums:
        name = enum.__name__
        f.write("class %s:\n" % name)

        for attr in sorted(dir(enum), key=lambda x: getattr(enum, x)):
            if attr.startswith("_") or attr in ("read", "write"): continue

            f.write("\t%s = %s\n" % (attr, getattr(enum, attr)))

        f.write("\n")

    dev.write("classes = {\n")

    for klass in classes:
        name = klass.__name__
        base = "Exception" if issubclass(klass, ttypes.TExceptionBase) else "BaseObject"
        f.write("class %s(%s):\n" % (name,  base))
        f.write("\t__slots__ = %s\n\n" % klass.__slots__)
        dev.write("\t'%s' : [" % name)

        #create init
        args = ["self"] + ["%s=None" % x for x in klass.__slots__]
        specs = []

        f.write("\tdef __init__(%s):\n" % ", ".join(args))
        for i, attr in enumerate(klass.__slots__):
            f.write("\t\tself.%s = %s\n" % (attr, attr))

            spec = klass.thrift_spec[i+1]
            # assert correct order, so the list of types is enough for check
            assert spec[2] == attr
            # dirty way to check optional attribute, since it is not in the generated code
            # can produce false positives, but these are not critical
            optional = re.search(optional_re % (i+1, attr), tf, re.I)
            if optional:
                specs.append("(None, %s)" % get_spec(spec))
            else:
                specs.append(get_spec(spec))

        f.write("\n")
        dev.write(", ".join(specs) + "],\n")

    dev.write("}\n\n")

    f.write("class Iface(object):\n")
    dev.write("methods = {\n")

    for name in dir(Pyload.Iface):
        if name.startswith("_"): continue

        func = inspect.getargspec(getattr(Pyload.Iface, name))

        f.write("\tdef %s(%s):\n\t\tpass\n" % (name, ", ".join(func.args)))

        spec = getattr(Pyload, "%s_result" % name).thrift_spec
        if not spec or not spec[0]:
            dev.write("\t'%s': None,\n" % name)
        else:
            spec = spec[0]
            dev.write("\t'%s': %s,\n" % (name, get_spec(spec)))

    f.write("\n")
    dev.write("}\n")

    f.close()
    dev.close()

if __name__ == "__main__":
    main()