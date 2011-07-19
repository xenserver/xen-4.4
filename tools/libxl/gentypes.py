#!/usr/bin/python

import sys
import re

import libxltypes

def format_comment(level, comment):
    indent = reduce(lambda x,y: x + " ", range(level), "")
    s  = "%s/*\n" % indent
    s += "%s * " % indent
    comment = comment.replace("\n", "\n%s * " % indent)
    x = re.compile(r'^%s \* $' % indent, re.MULTILINE)
    comment = x.sub("%s *" % indent, comment)
    s += comment
    s += "\n"
    s += "%s */" % indent
    s += "\n"
    return s

def libxl_C_instance_of(ty, instancename):
    if isinstance(ty, libxltypes.Aggregate) and ty.typename is None:
        if instancename is None:
            return libxl_C_type_define(ty)
        else:
            return libxl_C_type_define(ty) + " " + instancename
    else:
        return ty.typename + " " + instancename

def libxl_C_type_define(ty, indent = ""):
    s = ""

    if isinstance(ty, libxltypes.Enumeration):
        if ty.comment is not None:
            s += format_comment(0, ty.comment)

        if ty.typename is None:
            s += "enum {\n"
        else:
            s += "typedef enum %s {\n" % ty.typename

        for v in ty.values:
            if v.comment is not None:
                s += format_comment(4, v.comment)
            x = "%s = %d" % (v.name, v.value)
            x = x.replace("\n", "\n    ")
            s += "    " + x + ",\n"
        if ty.typename is None:
            s += "}"
        else:
            s += "} %s" % ty.typename

    elif isinstance(ty, libxltypes.Aggregate):
        if ty.comment is not None:
            s += format_comment(0, ty.comment)

        if ty.typename is None:
            s += "%s {\n" % ty.kind
        else:
            s += "typedef %s {\n" % ty.kind

        for f in ty.fields:
            if f.comment is not None:
                s += format_comment(4, f.comment)
            x = libxl_C_instance_of(f.type, f.name)
            if f.const:
                x = "const " + x
            x = x.replace("\n", "\n    ")
            s += "    " + x + ";\n"
        if ty.typename is None:
            s += "}"
        else:
            s += "} %s" % ty.typename
    else:
        raise NotImplementedError("%s" % type(ty))
    return s.replace("\n", "\n%s" % indent)

def libxl_C_type_destroy(ty, v, indent = "    ", parent = None):

    s = ""
    if isinstance(ty, libxltypes.KeyedUnion):
        if parent is None:
            raise Exception("KeyedUnion type must have a parent")
        s += "switch (%s) {\n" % (parent + ty.keyvar_name)
        for f in ty.fields:
            (nparent,fexpr) = ty.member(v, f, parent is None)
            s += "case %s:\n" % f.enumname
            s += libxl_C_type_destroy(f.type, fexpr, indent + "    ", nparent)
            s += "    break;\n"
        s += "}\n"
    elif isinstance(ty, libxltypes.Struct) and (parent is None or ty.destructor_fn is None):
        for f in [f for f in ty.fields if not f.const]:
            (nparent,fexpr) = ty.member(v, f, parent is None)
            s += libxl_C_type_destroy(f.type, fexpr, "", nparent)
    else:
        if ty.destructor_fn is not None:
            s += "%s(%s);\n" % (ty.destructor_fn, ty.pass_arg(v, parent is None))

    if s != "":
        s = indent + s
    return s.replace("\n", "\n%s" % indent).rstrip(indent)

def libxl_C_enum_to_string(ty, e, indent = "    "):
    s = ""
    s += "switch(%s) {\n" % e
    for v in ty.values:
        s += "    case %s:\n" % (v.name)
        s += "        return \"%s\";\n" % (v.valuename.lower())
    s += "    default:\n "
    s += "        return NULL;\n"
    s += "}\n"

    if s != "":
        s = indent + s
    return s.replace("\n", "\n%s" % indent).rstrip(indent)

def libxl_C_enum_strings(ty, indent=""):
    s = ""
    s += "libxl_enum_string_table %s_string_table[] = {\n" % (ty.typename)
    for v in ty.values:
        s += "    { .s = \"%s\", .v = %s },\n" % (v.valuename.lower(), v.name)
    s += "    { NULL, -1 },\n"
    s += "};\n"
    s += "\n"

    if s != "":
        s = indent + s
    return s.replace("\n", "\n%s" % indent).rstrip(indent)

def libxl_C_enum_from_string(ty, str, e, indent = "    "):
    s = ""
    s += "return libxl__enum_from_string(%s_string_table,\n" % ty.typename
    s += "                               %s, (int *)%s);\n" % (str, e)

    if s != "":
        s = indent + s
    return s.replace("\n", "\n%s" % indent).rstrip(indent)


if __name__ == '__main__':
    if len(sys.argv) != 4:
        print >>sys.stderr, "Usage: gentypes.py <idl> <header> <implementation>"
        sys.exit(1)

    (_, idl, header, impl) = sys.argv

    (_,types) = libxltypes.parse(idl)

    print "outputting libxl type definitions to %s" % header

    f = open(header, "w")

    f.write("""#ifndef __LIBXL_TYPES_H
#define __LIBXL_TYPES_H

/*
 * DO NOT EDIT.
 *
 * This file is autogenerated by
 * "%s"
 */

""" % " ".join(sys.argv))

    for ty in types:
        f.write(libxl_C_type_define(ty) + ";\n")
        if ty.destructor_fn is not None:
            f.write("void %s(%s);\n" % (ty.destructor_fn, ty.make_arg("p")))
        if isinstance(ty, libxltypes.Enumeration):
            f.write("const char *%s_to_string(%s);\n" % (ty.typename, ty.make_arg("p")))
            f.write("int %s_from_string(const char *s, %s);\n" % (ty.typename, ty.make_arg("e", passby=libxltypes.PASS_BY_REFERENCE)))
            f.write("extern libxl_enum_string_table %s_string_table[];\n" % (ty.typename))
        f.write("\n")

    f.write("""#endif /* __LIBXL_TYPES_H */\n""")
    f.close()

    print "outputting libxl type implementations to %s" % impl

    f = open(impl, "w")
    f.write("""
/* DO NOT EDIT.
 *
 * This file is autogenerated by
 * "%s"
 */

#include "libxl_osdeps.h"

#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#include "libxl.h"
#include "libxl_internal.h"

#define LIBXL_DTOR_POISON 0xa5

""" % " ".join(sys.argv))

    for ty in [t for t in types if t.destructor_fn is not None and t.autogenerate_destructor]:
        f.write("void %s(%s)\n" % (ty.destructor_fn, ty.make_arg("p")))
        f.write("{\n")
        f.write(libxl_C_type_destroy(ty, "p"))
        f.write("    memset(p, LIBXL_DTOR_POISON, sizeof(*p));\n")
        f.write("}\n")
        f.write("\n")

    for ty in [t for t in types if isinstance(t,libxltypes.Enumeration)]:
        f.write("const char *%s_to_string(%s e)\n" % (ty.typename, ty.typename))
        f.write("{\n")
        f.write(libxl_C_enum_to_string(ty, "e"))
        f.write("}\n")
        f.write("\n")

        f.write(libxl_C_enum_strings(ty))

        f.write("int %s_from_string(const char *s, %s *e)\n" % (ty.typename, ty.typename))
        f.write("{\n")
        f.write(libxl_C_enum_from_string(ty, "s", "e"))
        f.write("}\n")
        f.write("\n")


    f.close()
