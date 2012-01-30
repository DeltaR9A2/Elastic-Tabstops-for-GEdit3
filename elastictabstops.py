import uuid

from gi.repository import GObject, Gedit, Gtk, Pango

MINIMUM_CELL_WIDTH = 32
MINIMUM_CELL_PADDING = 16

class TabGroup:
	def __init__(self, first_line):
		self.first_line	= first_line
		self.line_count	= 0

		self.cell_widths = []

		self.tabs = Pango.TabArray.new(3, True)
		
		self.tag = None
		self.buffer = None

	def add_row_structs(self, *row_structs):
		for row in row_structs:
			while len(self.cell_widths) < len(row):
				self.cell_widths.append(0)
			
			for cell_num, cell_width in enumerate(row):
				if cell_width > self.cell_widths[cell_num]:
					self.cell_widths[cell_num] = cell_width
			
			self.line_count += 1
		
		self.regenerate_tabs()
	
	def regenerate_tabs(self):
		self.tabs.resize(len(self.cell_widths))
		tab_offset = 0
		for i, w in enumerate(self.cell_widths):
			tab_offset += w
			self.tabs.set_tab(i, Pango.TabAlign.LEFT, tab_offset)

	def apply_to_view(self, view):
		self.buffer = view.get_buffer()

		self.tag = self.buffer.create_tag(None, tabs = self.tabs)
		for x in xrange(self.line_count):
			start_iter	= self.buffer.get_iter_at_line(self.first_line+x)
			end_iter	= start_iter.copy()
			end_iter.forward_to_line_end()
			self.buffer.apply_tag(self.tag, start_iter, end_iter)

	def destroy(self):
		if self.tag is not None and self.buffer is not None:
			self.buffer.delete_tag(self.tag)
			
class CellParser:
	cell_enders = ("\t", "\0")
	line_enders = ("\n", "\0")
	
	minimum_cell_width = 32
	minimum_cell_padding = 16

	def __init__(self, view):
		self.view = view
		self.buffer = self.view.get_buffer()
		self.iterator = self.buffer.get_start_iter()

		self.rows = []
		self.row_blankness = []
		
		self.current_row = []
		self.current_row_is_blank = True
		
		self.cell_start = None
		self.cell_end = None
		
		self.parse()
		
	def next_row(self):
		self.rows.append(self.current_row)
		self.row_blankness.append(self.current_row_is_blank)
		
		self.current_row = []
		self.current_row_is_blank = True
		
		self.cell_start	= self.cell_end = None
	
	def add_cell(self, width):
		self.current_row.append(width)
	
	def end_cell(self):
		if self.cell_start is not None and self.cell_end is not None:
			self.cell_end.backward_char()
			start_rect = self.view.get_iter_location(self.cell_start)
			end_rect = self.view.get_iter_location(self.cell_end)
			width = (end_rect.x + end_rect.width) - start_rect.x
			self.add_cell(max(	width + self.minimum_cell_padding,
				self.minimum_cell_width))
			self.cell_start = self.cell_end = None
		else:
			self.add_cell(self.minimum_cell_width)
	
	def parse(self):
		cell_start = None
		cell_end = None

		while not self.iterator.is_end():
			char = self.iterator.get_char()
			self.iterator.forward_char()

			if char in self.cell_enders:
				self.end_cell()
			
			if char in self.line_enders:
				self.next_row()

			if char not in self.cell_enders and char not in self.line_enders:
				self.current_row_is_blank = False
			
				self.cell_end = self.iterator.copy()

				if self.cell_start is None:
					self.cell_start = self.iterator.copy()

	def yield_rows(self):
		row_set = []
		for row, blank in zip(self.rows, self.row_blankness):
			row_set.append(row)
			if blank:
				yield row_set
				row_set = []
			

class ElasticTabstopsPlugin(GObject.Object, Gedit.ViewActivatable):

	__gtype_name__ = "ElasticTabstopsPlugin"

	view = GObject.property(type=Gedit.View)
	
	def __init__(self):
		GObject.Object.__init__(self)

		self.outstanding_tags = []

	def do_activate(self):
		print "ETP Activate"

		self.buffer = self.view.get_buffer()

		self.buffer.connect("changed", self.changed_callback, self.view)

	def do_deactivate(self):
		print "ETP Deactivate"

	def do_update_state(self):
		print "ETP Update"

	def changed_callback(self, buffer, view):
		parser = CellParser(view)
		line_number = 0
		for row_set in parser.yield_rows():
			tab_group = TabGroup(line_number)
			tab_group.add_row_structs(*row_set)
			tab_group.apply_to_view(view)
			line_number += len(row_set)

