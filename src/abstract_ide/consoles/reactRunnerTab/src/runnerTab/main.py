from .imports import *
from .initFuncs import initFuncs

class runnerTab(QWidget):
	def __init__(self, parent=None):
		super().__init__(parent)

		self.init_path = '/var/www/TDD/my-app'
		self.initializeInit()

		root = QVBoxLayout(self)

		# --- Top row ------------------------------------------------------------
		top = self.init_top_row_create()
		root.addLayout(top)

		# --- Issue trees + editor ----------------------------------------------
		tree_stack = self.init_tree_creation()
		dict_panel = self.init_dict_panel_creation()
		right_panel = self.init_text_editor_creation()
		editor_row  = self.init_horizontal_split(tree_stack, right_panel)
		lower_split = self.init_vertical_split_creation(dict_panel, editor_row)

		# --- Log panel (this was missing) --------------------------------------
		# Move the existing view toggles (rb_all/err/wrn, cb_try_alt_ext) above the log
		view_row = self.init_view_row_create()
		log_panel = QWidget(); log_lay = QVBoxLayout(log_panel)
		log_lay.addLayout(view_row)
		log_lay.addWidget(self.log_view, 1)

		# --- Final stack: [log panel] over [dict + trees/editor] ----------------
		main_split = self.init_vertical_split_creation(log_panel, lower_split)
		root.addWidget(main_split, 1)

		self.init_set_buttons(tree_stack)

runnerTab = initFuncs(runnerTab)

