import tkinter as tk
from tkinter import ttk
import time

root = tk.Tk() # Root
root.title("BioRP by 4X5KD") # Give a title to the window root

def on_click(event=None): # For the bind to work, the function is passed an event object
    text = entry.get() # Get text from entry
    if text: # If there's text
        text_list.insert(tk.END, text) # Insert at the *END* of the widget
        entry.delete(0, tk.END) # Erase current text in entry

root.columnconfigure(0, weight=1)
root.rowconfigure(0, weight=1)

frame = ttk.Frame(root)
frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5) # Grid the frame with sticking and padding

frame.columnconfigure(0, weight=1)
frame.rowconfigure(1, weight=1)

entry = ttk.Entry(frame) # Writable text box
entry.grid(row=0, column=0, sticky="nsew")

entry.bind("<Return>", on_click) # Bind the entry to perform on_click when return is pressed

btn = ttk.Button(frame, text="ADD", command=on_click) # Button
btn.grid(row=0, column=1)

text_list = tk.Listbox(frame) # Unwritable text box
text_list.grid(row=1, column=0, columnspan=2, sticky="nsew",)

root.mainloop() # Main Loop