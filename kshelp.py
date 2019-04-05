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
	elif isinstance(obj, int):
		result = '0x%X (%d)' % (obj, obj)
	elif isinstance(obj, bool):
		result = '%s' % (obj)
	elif str(objType).startswith('<enum '):
		result = '%s' % (obj)
	elif isinstance(obj, list):
		result = repr(obj)
	else:
		result = '(unknown type %)' % (str(objType))

	return result

# access fields that may be properties, which could compute internal results
# (often '_m_XXX' fields)
def exercise(ksobj):
	for candidate in dir(ksobj):
		#if candidate.startswith('_') and (not candidate.startswith('_m_')):
		#	continue
		try:
			foo = getattr(ksobj, candidate, False)
		except Exception:
			pass

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
		result = 'kaitai_struct_formats.executable.microsoft_pe'
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

fieldDescendExceptions = ['_parent', '_root']
fieldDescendExceptionsPatterns = []

fieldPrintExceptions = []
fieldPrintExceptionsPatterns = []

def isFieldExceptionDescend(fieldName):
	global fieldDescendExceptions, fieldDescendExceptionsPatterns

	if fieldName in fieldDescendExceptions:
		return True

	for fep in fieldDescendExceptionsPatterns:
		if re.match(fep, fieldName):
			return True

	return False

def isFieldExceptionPrint(fieldName):
	global fieldExceptions, fieldExceptionsPatterns

	if fieldName in fieldPrintExceptions:
		return True

	for fep in fieldPrintExceptionsPatterns:
		if re.match(fep, fieldName):
			return True

	return False

def setFieldExceptionLevel0():
	global fieldDescendExceptions, fieldDescendExceptionsPatterns
	global fieldPrintExceptions, fieldPrintExceptionsPatterns
	fieldDescendExceptions = ['_parent', '_root']
	fieldDescendExceptionsPatterns = []
	fieldPrintExceptions = []
	fieldPrintExceptionsPatterns = []

def setFieldExceptionLevel1():
	global fieldDescendExceptions, fieldDescendExceptionsPatterns
	global fieldPrintExceptions, fieldPrintExceptionsPatterns

	setFieldExceptionLevel0()

	fieldPrintExceptionsPatterns += [r'_raw__.*$']
	fieldPrintExceptions += ['_io', '_is_le', '_root', '_parent', '_debug']
	fieldPrintExceptions += ['_read', '_read_be', '_read_le']
	fieldPrintExceptions += ['from_bytes', 'from_file', 'from_io']
	fieldPrintExceptions += ['SEQ_FIELDS']

def setFieldExceptionLevel2():
	global fieldDescendExceptions, fieldDescendExceptionsPatterns
	global fieldPrintExceptions, fieldPrintExceptionsPatterns

	setFieldExceptionLevel1()

	fieldPrintExceptionsPatterns += [r'^_m_.*$', r'^__.*$']
	fieldDescendExceptionsPatterns += [r'^_m_.*$']

#------------------------------------------------------------------------------
# kaitai object exploring stuff
#------------------------------------------------------------------------------

# return all field names qualified for printing
#
def getFieldNamesPrint(ksobj):
	result = []

	for fieldName in dir(ksobj):
		if isFieldExceptionPrint(fieldName):
			continue

		try:
			subobj = getattr(ksobj, fieldName, False)

			# do not return kaitai objects (are for descending, not printing)
			if isinstance(subobj, kaitaistruct.KaitaiStruct):
				continue
			elif isinstance(subobj, list):
				if len(subobj)<=0 or isinstance(subobj[0], kaitaistruct.KaitaiStruct):
					continue

			#print('%s is ok' % fieldName)
			#print('%s is instance? %s' % (fieldName, isinstance(subobj, kaitaistruct.KaitaiStruct)))
			result.append(fieldName)
		except Exception:
			pass

	return result

# return all field names required for descending
#
# IN:	kaitai object
# OUT:	field names that are either:
#		- kaitai objects
#		- lists of kaitai objects
#
def getFieldNamesDescend(ksobj):
	result = []

	for fieldName in dir(ksobj):
		if isFieldExceptionDescend(fieldName):
			continue

		try:
			subobj = getattr(ksobj, fieldName, False)

			if isinstance(subobj, kaitaistruct.KaitaiStruct):
				result += [fieldName]
			elif isinstance(subobj, list):
				if len(subobj)>0 and isinstance(subobj[0], kaitaistruct.KaitaiStruct):
					result += [fieldName]
		except Exception:
			pass

	return result

# compute all kaitai objects linked to from the given object
#
# IN:	kaitai object
# OUT:	[obj0, obj1, obj2, ...]
#
def getLinkedKaitaiObjects(ksobj):
	result = []

	for fieldName in getFieldNamesDescend(ksobj):
		subobj = getattr(ksobj, fieldName, False)
		if isinstance(subobj, list):
			result += subobj
		else:
			result += [subobj]

	return result

# compute all kaitai objects linked to from the given object, and from its
# descendents, and so on...
def getLinkedKaitaiObjectsAll(ksobj, depth=0):
	#if depth > 2:
	#	return []

	exercise(ksobj)

	result = [ksobj]

	linkedObjects = getLinkedKaitaiObjects(ksobj)
	for subobj in linkedObjects:
		result += getLinkedKaitaiObjectsAll(subobj, depth+1)
	return result
