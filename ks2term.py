#!/usr/bin/env python

import sys
assert sys.version_info[0] == 3
import types

import kaitaistruct
import kshelp

NORMAL = '\x1b[0m'

BLACK = '\x1b[30m'
RED = '\x1b[31m'
GREEN = '\x1b[32m'
YELLOW = '\x1b[33m'
BLUE = '\x1b[34m'
PURPLE = '\x1b[35m'
CYAN = '\x1b[36m'
GRAY = '\x1b[37m'

LBLACK = '\x1b[1;30m'
LRED = '\x1b[1;31m'
LGREEN = '\x1b[1;32m'
LYELLOW = '\x1b[1;33m'
LBLUE = '\x1b[1;34m'
LPURPLE = '\x1b[1;35m'
LCYAN = '\x1b[1;36m'
LGRAY = '\x1b[1;37m'

#------------------------------------------------------------------------------
# text dumping stuff
#------------------------------------------------------------------------------
filterLevel = 0

def dump(obj, depth=0):
	global filterLevel

	indent = '    '*depth
		
	print(('%s'+PURPLE+'%s'+NORMAL) % (indent, repr(obj)))

	kshelp.exercise(obj)
	for fieldName in kshelp.getFieldNamesPrint(obj, filterLevel):
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

		if color:
			print('%s.%s: %s%s%s' % (indent, fieldName, color, subObjStr, NORMAL))
		else:
			print('%s.%s: %s' % (indent, fieldName, subObjStr))

	for fieldName in kshelp.getFieldNamesDescend(obj, filterLevel):
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

	filterLevel = int(sys.argv[1])
	fpath = sys.argv[2]

	parsed = kshelp.parseFpath(fpath)
	dump(parsed, filterLevel)

