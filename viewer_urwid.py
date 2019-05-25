#!/usr/bin/env python

import re
import os
import sys
import kshelp
import urwid

import kaitaistruct

ktb = None

def callback_tree_modified(listBox, footer):
	kaitaiNode = listBox.get_focus()[1]

	fieldName = kaitaiNode.get_key()

	range_ = None
	tmp = kaitaiNode.get_parent()
	if tmp:
		range_ = kshelp.getFieldRange(tmp._ksobj, fieldName)
	if not range_:
		range_ = ''
	footer.set_text(".%s %s" % (fieldName, str(range_)))

class KaitaiTreeWidget(urwid.TreeWidget):
	global ktb

	unexpanded_icon = urwid.AttrMap(urwid.TreeWidget.unexpanded_icon, 'dirmark')
	expanded_icon = urwid.AttrMap(urwid.TreeWidget.expanded_icon, 'dirmark')

	def __init__(self, node):
		self.__super.__init__(node)
		self._w = urwid.AttrWrap(self._w, None)
		self._w.attr = 'body'
		self._w.focus_attr = 'focus'

	def get_display_text(self):
		# default display will be "key: value"
		return urwid.TreeWidget.get_display_text(self)

	def selectable(self):
		return True

class KaitaiNode(urwid.TreeNode):
	# same as TreeNode constructor + ksobj
	def __init__(self, value, ksobj, parent=None, key=None, depth=None):
		self._ksobj = ksobj
		urwid.TreeNode.__init__(self, value, parent=parent, key=key, depth=depth)

	def load_widget(self):
		return KaitaiTreeWidget(self)

class KaitaiParentNode(urwid.ParentNode):
	# same as ParentNode constructor + ksobj
	def __init__(self, value, ksobj, parent=None, key=None):
		self._ksobj = ksobj

		# depth is steps from root, count them
		depth = 0
		traveller = ksobj
		while traveller._parent:
			depth += 1
			traveller = traveller._parent

		# if a field description isn't provided, generate it from the ksobj
		if value == None:
			value = kshelp.objToStr(ksobj)

		# parent constructor
		urwid.ParentNode.__init__(
			self,
			value,					# field description		self._value
			key=key,				# field name			self._key
			parent=parent,			#						self._parent
			depth=depth				#						self._depth
		)

	def load_widget(self):
		return KaitaiTreeWidget(self)

	# URWID asks us the names ("keys") of our children
	def load_child_keys(self):
		result = []

		kshelp.exercise(self._ksobj)
		for fieldName in (kshelp.getFieldNamesPrint(self._ksobj) + kshelp.getFieldNamesDescend(self._ksobj)):
			childObj = getattr(self._ksobj, fieldName)
			if isinstance(childObj, list):
				for i in range(len(childObj)):
					result.append('%s[%d]' % (fieldName, i))
			else:
				result.append(fieldName)

		return result

	# URWID asks us for nodes for each of the names ("keys") of our children
	def load_child_node(self, key):
		childObj = None

		# is the key like "blah[5]"? then list
		m = re.match(r'^(\w*)\[(\d+)\]$', key)
		if m:
			(fieldName, fieldIdx) = m.group(1,2)
			childObj = getattr(self._ksobj, fieldName)[int(fieldIdx)]
		else:
			childObj = getattr(self._ksobj, key)

		if isinstance(childObj, kaitaistruct.KaitaiStruct):
			return KaitaiParentNode(None, childObj, parent=self, key=key)
		else:
			return KaitaiNode(kshelp.objToStr(childObj), childObj, parent=self, key=key, depth=self.get_depth()+1)

class KaitaiTreeBrowser:
	palette = [
		('body', 'light gray', 'black'),
		('flagged', 'black', 'dark green', ('bold','underline')),
		('focus', 'light gray', 'dark blue', 'standout'),
		('flagged focus', 'yellow', 'dark cyan',
		('bold','standout','underline')),
		('head', 'yellow', 'black', 'standout'),
		('foot', 'light gray', 'black'),
		('key', 'light cyan', 'black','underline'),
		('title', 'white', 'black', 'bold'),
		('dirmark', 'black', 'dark cyan', 'bold'),
		('flag', 'dark gray', 'light gray'),
		('error', 'dark red', 'light gray'),
	]

	footer_text = [
		('title', "Kaitai Data Browser"), "	",
		('key', "UP"), ",", ('key', "DOWN"), ",",
		('key', "PAGE UP"), ",", ('key', "PAGE DOWN"),
		"  ",
		('key', "+"), ",",
		('key', "-"), "  ",
		('key', "LEFT"), "  ",
		('key', "HOME"), "  ",
		('key', "END"), "  ",
		('key', "Q"),
		]

	def __init__(self, ksobj=None):
		self.topnode = KaitaiParentNode(None, ksobj, key=kshelp.objToStr(ksobj))
		self.walker = urwid.TreeWalker(self.topnode)
		self.listbox = urwid.TreeListBox(self.walker)
		self.listbox.offset_rows = 0
		self.header = urwid.Text( "" )
		self.footer = urwid.AttrWrap( urwid.Text( self.footer_text ),
			'foot')
		self.view = urwid.Frame(
			urwid.AttrWrap( self.listbox, 'body' ),
			header=urwid.AttrWrap(self.header, 'head' ),
			footer=self.footer )

		urwid.connect_signal(self.walker, "modified", callback_tree_modified, weak_args=[self.listbox, self.footer])

	def main(self):
		"""Run the program."""

		self.loop = urwid.MainLoop(self.view, self.palette,
			unhandled_input=self.unhandled_input)
		self.loop.run()

	def unhandled_input(self, k):
		if k in ('q','Q'):
			raise urwid.ExitMainLoop()

#------------------------------------------------------------------------------
# main
#------------------------------------------------------------------------------

if __name__ == '__main__':
	assert len(sys.argv) == 3
	(cmd, fpath) = (sys.argv[1], sys.argv[2])

	#kshelp.fieldPrintExceptionsPatterns += [r'^__.*__$']
	# level0 shows the rawest data returned by kaitai
	if cmd == 'level0':
		kshelp.setFieldExceptionLevel0()
	elif cmd == 'level1':
		kshelp.setFieldExceptionLevel1()
	elif cmd == 'level2':
		kshelp.setFieldExceptionLevel2()

	ksobj = kshelp.parseFpath(fpath)

	ktb = KaitaiTreeBrowser(ksobj)
	ktb.main()
	#dumpDict(treeDict, 0)
