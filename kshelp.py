#!/usr/bin/env python

import io
import os
import re
import sys
import struct
import types
import binascii
import importlib
import traceback
import collections

import kaitaistruct

assert sys.version_info[0] == 3

#------------------------------------------------------------------------------
# misc
#------------------------------------------------------------------------------

def objToStr(obj):
	objType = type(obj)

	# blacklist: functions, types, callables
	#
	if isinstance(obj, type):
		#print('reject %s because its a type' % fieldName)
		return '(type)'
	elif hasattr(obj, '__call__'):
		#print('reject %s because its a callable' % fieldName)
		return '(callable)'

	result = None

	# whitelist: strings, unicodes, bytes, ints, bools, enums
	#
	if obj == None:
		return 'None'
	elif isinstance(obj, str):
		if len(obj) > 8:
			result = '%s...%s (0x%X==%d chars total)' % \
				(repr(obj[0:8]), repr(obj[-1]), len(obj), len(obj))
		else:
			result = repr(obj)
	elif isinstance(obj, bytes):
		if len(obj) > 8:
			result = binascii.hexlify(obj[0:8]).decode('utf-8') + '...' + \
				('%02X' % obj[-1]) + ' (0x%X==%d bytes total)' % (len(obj), len(obj))
		else:
			result = binascii.hexlify(obj).decode('utf-8')
	# note: bool needs to appear before int (else int determination will dominate)
	elif isinstance(obj, bool):
		result = '%s' % (obj)
	elif isinstance(obj, int):
		result = '0x%X (%d)' % (obj, obj)
	elif str(objType).startswith('<enum '):
		result = '%s' % (obj)
	elif isinstance(obj, list):
		result = repr(obj)
	elif isinstance(obj, kaitaistruct.KaitaiStruct):
		return re.match(r'^.*\.(\w+) object at ', repr(obj)).group(1)
	elif isinstance(obj, kaitaistruct.KaitaiStream):
		return re.match(r'^.*\.(\w+) object at ', repr(obj)).group(1)
	elif isinstance(obj, collections.defaultdict):
		# probably _debug
		result = repr(obj)
	else:
		result = '(unknown type %s)' % (str(objType))

	return result

# access all fields that may be properties, which could compute internal results
# (often '_m_XXX' fields)
def exercise(ksobj):
	for candidate in dir(ksobj):
		#if candidate.startswith('_') and (not candidate.startswith('_m_')):
		#	continue
		try:
			foo = getattr(ksobj, candidate)
		except Exception:
			pass

# get the [start,end) data for a given field within a ks object
#
# abstracts away:
# * the debug['arr'] stuff, you just give it 'foo' or 'foo[3]'
# * the 'foo' vs. '_m_foo' complication, you just give it 'foo'
#
# restrictedToRoot: means the start/end are only returned if they're in the
# original file (vs. being in a kaitai substream)

def getFieldRange(ksobj, fieldName:str, restrictedToRoot=False):
	if restrictedToRoot:
		if ksobj._io != ksobj._root._io:
			return None

	# does given kaitai object even have ._debug?
	debug = None
	try:
		debug = getattr(ksobj, '_debug')
	except Exception:
		return None

	tmp = None

	# is the request for a list member? eg. "load_commands[13]" ?
	if fieldName.endswith(']'):
		m = re.match(r'^(\w*)\[(\d+)\]$', fieldName)
		if not m:
			raise Exception('malformed field name: %s' % fieldName)
		fieldName = m.group(1)
		index = int(m.group(2))

		# prefer the '_m_' version
		if not fieldName.startswith('_m_'):
			mfield = '_m_'+fieldName
			if mfield in debug and 'arr' in debug[mfield]:
				tmp = debug['_m_'+fieldName]['arr'][index]

		# fall back to normal version
		if not tmp:
			if fieldName in debug and 'arr' in debug[fieldName]:
				tmp = debug[fieldName]['arr'][index]
	else:
		# prefer the '_m_' version
		if not fieldName.startswith('_m_'):
			mfield = '_m_'+fieldName
			if mfield in debug:
				tmp = debug[mfield]
		if not tmp:
			if fieldName in debug:
				tmp = debug[fieldName]

	if not tmp:
		return None

	result = [None, None]
	if 'start' in tmp:
		result[0] = tmp['start']
	if 'end' in tmp:
		result[1] = tmp['end']
	return result

#------------------------------------------------------------------------------
# determine what kaitai module to use
#------------------------------------------------------------------------------

# return the name of the kaitai module to service this data
#
# dsample:	str		data sample
# length:	int		total length of data
def idData(dataSample, length):
	result = None
	#print('idData() here with sample: %s' % repr(dataSample))

	if len(dataSample) < 16:
		return result

	if dataSample[0:4] == b'\x7fELF':
		result = 'elf'
	if dataSample[0:4] in [b'\xfe\xed\xfa\xce', b'\xce\xfa\xed\xfe', b'\xfe\xed\xfa\xcf', b'\xcf\xfa\xed\xfe']:
		result = 'mach_o'
	if dataSample[0:2] == b'MZ':
		result = 'microsoft_pe'
	if dataSample[0:8] == b'\x89PNG\x0d\x0a\x1a\x0a':
		result = 'png'
	if dataSample[2:11] == b'\xFF\xe0\x00\x10JFIF\x00':
		result = 'jpeg'
	if dataSample[0:4] == b'GIF8':
		result = 'gif'
	if dataSample[0:2] in [b'BM', b'BA', b'CI', b'CP', b'IC', b'PT'] and struct.unpack('<I', dataSample[2:6])[0]==length:
		result = 'bmp'
	if dataSample[0:2] == b'PK' and dataSample[2:4] in [b'\x01\x02', b'\x03\x04', b'\x05\x06']:
		result = 'zip'
	if dataSample[0:6] == b'Rar!\x1a\x07':
		result = 'rar'
	if dataSample[0:2] == b'\x1f\x8b' and dataSample[2:3]==b'\x08':
		result = 'gzip'

	#print('idData() returning \'%s\'' % result)
	return result

def idFile(fpath):
	with open(fpath, 'rb') as fp:
		return idData(fp.read(16), os.path.getsize(fpath))

#------------------------------------------------------------------------------
# determine what kaitai module to use
#------------------------------------------------------------------------------

def ksModuleToClass(moduleName):
	# kaitai_struct_formats.executable.microsoft_pe -> microsoft_pe
	if '.' in moduleName:
		moduleName = moduleName.split('.')[-1]

	# microsoft_pe -> MicrosoftPe
	# split on underscores, camelcase
	return ''.join(map(lambda x: x.capitalize(), moduleName.split('_')))

def ksImportClass(moduleName):
	global __name__, __package__
	if not moduleName:
		return None

	classThing = None
	try:
		#print('importing kaitai module %s' % moduleName)
		module = importlib.import_module(moduleName)
		className = ksModuleToClass(moduleName)
		classThing = getattr(module, className)
	except Exception as e:
		print('ERROR: importing kaitai module %s\n%s' % (moduleName, e))
		pass

	return classThing

def parseFpath(fpath, ksModuleName=None):
	if not ksModuleName:
		ksModuleName = idFile(fpath)
	#print('parseFpath() using kaitai format: %s' % ksModuleName)

	ksClass = ksImportClass(ksModuleName)
	if not ksClass: return None

	parsed = None
	try:
		parsed = ksClass.from_file(fpath)
		parsed._read()
	except Exception as e:
		print('parseFpath(): kaitai module %s threw exception, check file type' % ksModuleName)
		parsed = None

	return parsed

def parseData(data, ksModuleName=None):
	if not ksModuleName:
		ksModuleName = idData(data, len(data))
	#print('parseData() using kaitai format: %s' % ksModuleName)

	ksClass = ksImportClass(ksModuleName)
	if not ksClass: return None

	parsed = None
	try:
		parsed = ksClass.from_bytes(data)
		parsed._read()
	except Exception as e:
		print('parseData(): kaitai module %s threw exception, check file type' % ksModuleName)
		parsed = None

	return parsed

def parseIo(ioObj, ksModuleName=None):
	ioObj.seek(0, io.SEEK_END)
	length = ioObj.tell()

	if not ksModuleName:
		ioObj.seek(0, io.SEEK_SET)
		ksModuleName = idData(ioObj.read(16), length)
	#print('parseIo() using kaitai format: %s' % ksModuleName)

	ioObj.seek(0, io.SEEK_SET)
	ksClass = ksImportClass(ksModuleName)
	if not ksClass: return None

	parsed = None
	try:
		ioObj.seek(0, io.SEEK_SET)
		parsed = ksClass.from_io(ioObj)
		parsed._read()
	except Exception as e:
		print('parseIo(): kaitai module %s threw exception, check file type' % ksModuleName)
		parsed = None

	return parsed

#------------------------------------------------------------------------------
# kaitai object field control
#------------------------------------------------------------------------------

# certain fields in the kaitai python object we:
# - should not DESCEND into (eg: ._parent, ._root)
# - should not PRINT (eg: ._io)

def filterDescend(ksobj, fieldName, level):
	result = False

	if level >= 0:
		blacklist = ['_root', '_parent']
		if fieldName in blacklist:
			result = True

	if not result and level >= 1:
		pass

	if not result and level >= 2:
		if fieldName.startswith('_m_'):
			result = True

	#if result:
	#	print('field %s has been filtered (descent)' % fieldName)
	return result

def filterPrint(ksobj, fieldName, level):
	result = False

	# at level 0, print everything
	if level >= 0:
		pass

	# level 1
	if not result and level >= 1:
		blacklist = [ '_root', '_parent',
			'_debug', 'SEQ_FIELDS',
			'_is_le', '_read',
			'_read_be', '_read_le', 'close',
			'from_bytes', 'from_file', 'from_io'
		]
		if fieldName in blacklist:
			result = True
		elif re.match(r'^_raw__.*$', fieldName):
			result = True
		elif hasattr(ksobj, fieldName):
			if isinstance(getattr(ksobj, fieldName), type):
				result = True

	# level 2
	if not result and level >= 2:
		blacklist = ['_io']
		if fieldName in blacklist:
			result = True
		elif fieldName.startswith('_m_'):
			result = True
		elif fieldName.startswith('__'):
			result = True

	#if result:
	#	print('field %s has been filtered (print)' % fieldName)
	return result

#------------------------------------------------------------------------------
# kaitai object exploring stuff
#------------------------------------------------------------------------------

# return all field names qualified for printing
#
def getFieldNamesPrint(ksobj, filterLevel=0):
	result = set()

	for fieldName in dir(ksobj):
		if filterPrint(ksobj, fieldName, filterLevel):
			continue

		try:
			subobj = getattr(ksobj, fieldName)

			# do not return kaitai objects (are for descending, not printing)
			if isinstance(subobj, kaitaistruct.KaitaiStruct):
				continue
			elif isinstance(subobj, list):
				if len(subobj)<=0 or isinstance(subobj[0], kaitaistruct.KaitaiStruct):
					continue

			#print('%s is ok' % fieldName)
			#print('%s is instance? %s' % (fieldName, isinstance(subobj, kaitaistruct.KaitaiStruct)))
			result.add(fieldName)
		except Exception:
			pass

	return list(result)

# return all field names required for descending
#
# IN:	kaitai object
# OUT:	field names that are either:
#		- kaitai objects
#		- lists of kaitai objects
#
def getFieldNamesDescend(ksobj, filterLevel=0):
	result = set()

	for fieldName in dir(ksobj):
		if filterDescend(ksobj, fieldName, filterLevel):
			continue

		try:
			subobj = getattr(ksobj, fieldName)

			if isinstance(subobj, kaitaistruct.KaitaiStruct):
				result.add(fieldName)
			elif isinstance(subobj, list):
				if len(subobj)>0 and isinstance(subobj[0], kaitaistruct.KaitaiStruct):
					result.add(fieldName)
		except Exception as e:
			pass

	return list(result)

# compute all kaitai objects linked to from the given object
#
# IN:	kaitai object
# OUT:	[obj0, obj1, obj2, ...]
#
def getLinkedKaitaiObjects(ksobj):
	result = set()

	for fieldName in getFieldNamesDescend(ksobj):
		subobj = getattr(ksobj, fieldName)
		if isinstance(subobj, list):
			for tmp in subobj:
				result.add(tmp)
		else:
			result.add(subobj)

	return result

# compute all kaitai objects linked to from the given object, and from its
# descendents, and so on...
def getLinkedKaitaiObjectsAll(ksobj, depth=0):
	#if depth > 2:
	#	return []

	exercise(ksobj)

	result = set([ksobj])

	linkedObjects = getLinkedKaitaiObjects(ksobj)
	for subobj in linkedObjects:
		subResult = getLinkedKaitaiObjectsAll(subobj, depth+1)
		result = result.union(subResult)

	return result

def getDepth(ksobj, depth=0):
	result = depth

	exercise(ksobj)
	for subObj in getLinkedKaitaiObjects(ksobj):
		result = max(result, getDepth(subObj, depth+1))

	return result
