import tkinter as tk
from tkinter import ttk
from utils import get_int_value

class EditableTableWidget:
    """An editable table widget with configurable number of columns."""
    
    def __init__(self, master, columns, data=None, max_values=None, sxl_objs=None,
                 base_addr=0, format_func=None, update_func=None):
        """
        Initialize the editable table widget.
        
        Parameters:
        - master: The Tkinter main window or container
        - columns: A list of column names
        - data: A list of tuples or lists with the initial data for the table (optional)
        - max_values: A list of maximum values for each column
        - sxl_objs: An array of sxl_objs for all editable items
        - format_func: A reference to the formatter function to update the editable cell
        - update_func: A reference to teh update function for target value updates
        """
        # Create a frame for the table widget and scrollbars
        self.frame = ttk.Frame(master)
        self.frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create scrollbar
        self.y_scrollbar = ttk.Scrollbar(self.frame, orient=tk.VERTICAL)
        self.y_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Create the table widget with index column and configured data columns
        self.columns = ['index'] + columns
        self.table = ttk.Treeview(self.frame, columns=self.columns, show='headings', 
                                  yscrollcommand=self.y_scrollbar.set)
        
        # Configure the scrollbar
        self.y_scrollbar.config(command=self.table.yview)
        
        # Define data column headings, prepare maximum value list
        col0 = self.columns[0]
        self.table.heading(col0, text=col0.capitalize())
        self.table.column(col0, width=48, anchor='c')
        self.column_max = list()
        for column in self.columns[1:]:
            self.table.heading(column, text=column.capitalize())
            self.table.column(column, width=120, anchor='c')
            self.column_max.append(None)
        
        self.table.pack(fill=tk.BOTH, expand=True)
        
        # Bind double-click event for table cells
        self.table.bind('<Double-1>', self.edit_cell)
        self.table.bind('<F2>', self.edit_cell)

        # define the background color
        # FIXME: no themes supported yet, use static background color
        self.color = "#c0e0f0"
        self.table.tag_configure(tagname="row", background=self.color)
        
        # Insert example data if available
        if data:
            self.load_data(data)
        
        # set maximum values if applicable
        if max_values:
            self.set_max_values(max_values)
        
        self.sxl_objs = sxl_objs
            
        # Variable to store current entry widget
        self.current_entry = None

        # function references
        self.format_func = format_func
        self.update_func = update_func

        # Keep base address offset
        self.base_addr = base_addr

        # create cell edit style
        self.estyle = ttk.Style()
        if "plain.field" not in self.estyle.element_names():
            # must be created only once per tkinter instance
            self.estyle.element_create("plain.field", "from", "clam")
            self.estyle.layout("EntryStyle.TEntry",
                            [('Entry.plain.field', {'children': [(
                                'Entry.background', {'children': [(
                                    'Entry.padding', {'children': [(
                                        'Entry.textarea', {'sticky': 'nswe'})],
                                'sticky': 'nswe'})], 'sticky': 'nswe'})],
                                'border':'2', 'sticky': 'nswe'})])
            self.estyle.configure("EntryStyle.TEntry",
                            background="green", 
                            foreground="black",
                            fieldbackground="green3")
    
    def load_data(self, data):
        """
        Load data into the table widget.
        
        Parameters:
        - data: A list of tuples or lists with data for the table
        """
        # Clear existing data
        self.table.delete(*self.table.get_children())
            
        # Insert new data
        for i, row in enumerate(data):
            item_node = self.table.insert('', tk.END, values=[str(i)] + list(row))
            self.table.item(item=item_node, tags="row")
    
    def set_max_values(self, max_values):
        """
        Set max values of table widget items.
        
        Parameters:
        - max_values: A list of tuples or lists with max values for each column
        """
        for i, m in enumerate(max_values):
            self.column_max[i] = m

    def get_data(self):
        """
        Get all data from the table.
        
        Returns:
        - A list of tuples containing all rows in the table
        """
        data = []
        for item in self.table.get_children():
            data.append(self.table.item(item, 'values'))
        return data
    
    def add_row(self, values=None):
        """
        Add a new row to the table.
        
        Parameters:
        - values: A tuple or list with values for the new row (optional)
        """
        if values is None:
            values = ('', '', '')
        self.table.insert('', tk.END, values=values)
    
    def delete_selected_row(self):
        """
        Delete the selected row from the table.
        """
        selected = self.table.selection()
        if selected:
            for item in selected:
                self.table.delete(item)
    
    def edit_cell(self, event):
        """
        Edit a cell on double-click.
        
        Parameters:
        - event: The event triggered by double-clicking a cell
        """
        # Check if there are any selections
        if not self.table.selection():
            return
            
        # Selected item
        item = self.table.selection()[0]
        column = self.table.identify_column(event.x)
        
        # Only data columns are editable
        if column != "#1":
            # Get current values
            values = self.table.item(item, 'values')
            
            # Determine position and size of selected cell
            x, y, width, height = self.table.bbox(item, column)
            
            # Destroy any existing entry widget
            if self.current_entry:
                self.current_entry.destroy()
            
            # Create input field
            self.current_entry = ttk.Entry(self.table, style="EntryStyle.TEntry", width=20, justify='center', background="red3")
            self.current_entry.place(x=x, y=y, width=width, height=height)
            current_value = values[int(column[1]) - 1].split(" ")[0]
            current_value = current_value if current_value is not None else ''
            self.current_entry.insert(0, current_value)
            self.current_entry.select_range(0, tk.END)
            self.current_entry.focus()
            
            # Store references for use in the save and cancel functions
            self.edit_item = item
            self.edit_column = int(column[1:]) - 1
            self.edit_values = values
            self.edit_objs = self.sxl_objs[int(values[0])]
            
            # Bind entry field events
            self.current_entry.bind(sequence='<Return>', func=self.save_edit)
            self.current_entry.bind(sequence="<KP_Enter>", func=self.save_edit)
            self.current_entry.bind(sequence="<Extended-Return>", func=self.save_edit)
            self.current_entry.bind(sequence='<Escape>', func=self.cancel_edit)
            self.current_entry.bind(sequence='<FocusOut>', func=self.save_edit)
            self.current_entry.bind(sequence="<KeyRelease>", func=self.set_widget_state)

    def save_edit(self, event):
        """
        Save the edited value.
        
        Parameters:
        - event: The event that triggered saving (Return key or focus out)
        """
        if self.current_entry:
            new_values = list(self.edit_values)
            updated_value = self.current_entry.get()
            value = int(updated_value)
            sxl_obj=self.edit_objs[self.edit_column-1]
            if self.format_func is not None:
                updated_value = self.format_func(sxl_obj=sxl_obj,
                                                 value=value, status=1)
            if self.update_func is not None:
                self.update_func(sxl_obj=sxl_obj, value=value, base_addr=self.base_addr)
            new_values[self.edit_column] = updated_value
            self.table.item(self.edit_item, values=new_values)
            self.current_entry.destroy()
            self.current_entry = None
    
    def cancel_edit(self, event):
        """
        Cancel the current edit.
        
        Parameters:
        - event: The event that triggered cancellation (Escape key)
        """
        if self.current_entry:
            self.current_entry.destroy()
            self.current_entry = None
    
    def get_widget(self):
        """
        Get the frame containing the table widget.
        
        Returns:
        - The frame containing the table widget
        """
        return self.frame

    def get_int_value(self, value: str, max_value: int):
        """
        Parses a string containing numbers in different formats and returns
        the corresponding integer value.
        
        Supported formats:
        - Decimal: '123'
        - Hexadecimal: '0xABC' or '0XaBc'
        - Binary: '0b101' or '0B101'
        
        Args:
            value_str (str): The string to be parsed
            
        Returns:
            int: The parsed integer value
            None: If the string cannot be parsed as a number
        """
        # Remove whitespace at the beginning and end, make lowercase
        value = value.strip().lower()
        try:
            # Check the format and apply the appropriate conversion
            if value.startswith('0x'):
                # Hexadecimal format
                value_int = int(value, 16)
            elif value.startswith('0b'):
                # Binary format
                value_int = int(value, 2)
            else:
                # Treat as decimal number
                value_int = int(value)
            
            # Check whether value is in valid range
            if 0 <= value_int <= max_value:
                return value_int
        except:
            pass
        
        # parsing errors occured, return None
        return None

    def set_widget_state(self, event=None):
        """Set the widget state."""
        # disable ok button per default
        # enable it again after input checks are successful
        sig_max = self.column_max[self.edit_column - 1]

        value = get_int_value(value=self.current_entry.get(), max_value=sig_max)
        if value is None:
            self.estyle.configure("EntryStyle.TEntry",
                            background="green", 
                            foreground="black",
                            fieldbackground="orange")
            self.current_entry.unbind(sequence='<Return>')
        else:
            self.estyle.configure("EntryStyle.TEntry",
                            background="green", 
                            foreground="black",
                            fieldbackground="green2")
            self.current_entry.bind(sequence='<Return>', func=self.save_edit)
