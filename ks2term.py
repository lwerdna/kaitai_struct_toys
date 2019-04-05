#!/usr/bin/env python

# test script

from __future__ import print_function

import sys
assert sys.version_info[0] == 3
import types

import kaitaistruct
import kshelp

NORMAL = '\033[0m'
BLACK = '\033[0;30m'
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[0;33m'
BLUE = '\033[0;34m'
PURPLE = '\033[0;35m'
CYAN = '\033[0;36m'
GRAY = '\033[0;37m'

LBLACK = '\033[1;30m'
LRED = '\033[1;31m'
LGREEN = '\033[1;32m'
LYELLOW = '\033[1;33m'
LBLUE = '\033[1;34m'
LPURPLE = '\033[1;35m'
LCYAN = '\033[1;36m'
LGRAY = '\033[1;37m'

#------------------------------------------------------------------------------
# text dumping stuff
#------------------------------------------------------------------------------

def dump(obj, depth=0):
	indent = '    '*depth
		
	print((PURPLE+'%s%s'+NORMAL) % (indent, repr(obj)))

	kshelp.exercise(obj)
	for fieldName in kshelp.getFieldNamesPrint(obj):
		subObj = None
		try:
			subObj = getattr(obj, fieldName)
		except Exception:
			continue
		if subObj == None:
			continue

		subObjStr = kshelp.objToStr(subObj)

		color = ''

		if type(subObj) == types.MethodType:
			pass
		elif isinstance(subObj, type):
			pass
		elif fieldName == '_debug':
			color = RED
		elif isinstance(subObj, list):
			pass
		elif isinstance(subObj, dict):
			pass
		elif isinstance(subObj, str):
			color = CYAN
		elif isinstance(subObj, bytes):
			color = CYAN
		elif type(subObj) == int:
			color = YELLOW
		elif str(type(subObj)).startswith('<enum '):
			color = GREEN
			pass

		print('%s.%s: %s%s%s' % (indent, fieldName, color, subObjStr, NORMAL))

	for fieldName in kshelp.getFieldNamesDescend(obj):
		subObj = getattr(obj, fieldName)
		
		#print('recurring on: %s' % repr(subObj))

		if isinstance(subObj, list):
			for (i, tmp) in enumerate(subObj):
				print('%s.%s[%d]:' % (indent, fieldName, i))
				dump(subObj[i], depth+1)
		else:
			print('%s.%s:' % (indent, fieldName))
			#print(dir(subObj))
			dump(subObj, depth+1)

#------------------------------------------------------------------------------
# main
#------------------------------------------------------------------------------

if __name__ == '__main__':
	assert len(sys.argv) == 3

	kshelp.setFieldExceptionLevel2()

	cmd = sys.argv[1]
	fpath = sys.argv[2]

	if cmd == 'dump0':
		kshelp.setFieldExceptionLevel0()
	elif cmd == 'dump1':
		kshelp.setFieldExceptionLevel1()
	elif cmd == 'dump2':
		kshelp.setFieldExceptionLevel2()

	parsed = kshelp.parseFpath(fpath)
	dump(parsed)

