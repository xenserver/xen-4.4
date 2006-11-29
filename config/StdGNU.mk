AS         = $(CROSS_COMPILE)as
LD         = $(CROSS_COMPILE)ld
CC         = $(CROSS_COMPILE)gcc
CPP        = $(CROSS_COMPILE)gcc -E
AR         = $(CROSS_COMPILE)ar
RANLIB     = $(CROSS_COMPILE)ranlib
NM         = $(CROSS_COMPILE)nm
STRIP      = $(CROSS_COMPILE)strip
OBJCOPY    = $(CROSS_COMPILE)objcopy
OBJDUMP    = $(CROSS_COMPILE)objdump

INSTALL      = install
INSTALL_DIR  = $(INSTALL) -d -m0755
INSTALL_DATA = $(INSTALL) -m0644
INSTALL_PROG = $(INSTALL) -m0755

LIB64DIR = lib64

SOCKET_LIBS =
CURSES_LIBS = -lncurses
SONAME_LDFLAG = -soname
SHLIB_CFLAGS = -shared

ifneq ($(debug),y)
# Optimisation flags are overridable
CFLAGS ?= -O2 -fomit-frame-pointer
else
# Less than -O1 produces bad code and large stack frames
CFLAGS ?= -O1 -fno-omit-frame-pointer
endif
