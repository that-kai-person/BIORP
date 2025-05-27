# The BioRP project - by K. Dekel 4X5KD
# Version: ALPHA 1

import BIORP_Utilities as brp
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from datetime import datetime
import threading

root = tk.Tk() # Create and name the window
root.title("BioRP by 4X5KD")
root.minsize(800, 400)
tabControl = ttk.Notebook(root) # Tab control




# ------------ MENUS ------------

# FUNCTIONS
is_full_view = True
def toggleView():
    global is_full_view
    if is_full_view:
        # Switch to HAM mode (remove RX and TX)
        tabControl.forget(RX_tab)
        tabControl.forget(TX_tab)
    else:
        # Switch to FULL mode (add RX and TX back)
        tabControl.add(RX_tab, text='RX')
        tabControl.add(TX_tab, text='TX')
    is_full_view = not is_full_view

# MENU CONFIG

main_menu = tk.Menu(root)
root.config(menu=main_menu)

# FILE
file_menu = tk.Menu(main_menu, tearoff=0)
main_menu.add_cascade(label="File", menu=file_menu)
file_menu.add_command(label="EXIT", command=root.destroy)

# VIEW
view_menu = tk.Menu(main_menu, tearoff=0)
main_menu.add_cascade(label="View", menu=view_menu)
view_menu.add_command(label="Toggle view", command=toggleView)





# ------------ TAB CONTROL ------------
# Creating tabs for RX/TX/HAM modes
RX_tab = ttk.Frame(tabControl)
TX_tab = ttk.Frame(tabControl)
HAM_tab = ttk.Frame(tabControl)

# Adding tabs to tab control
tabControl.add(HAM_tab, text ='HAM')
tabControl.add(RX_tab, text ='RX') 
tabControl.add(TX_tab, text ='TX') 
tabControl.pack(expand = 1, fill ="both")





# ------------ HAM TAB ------------

# FUNCTIONS
def update_utc_clock():
    now_utc = datetime.utcnow().strftime("UTC %H:%M:%S")
    utc_clock_label_ham.config(text=now_utc)
    utc_clock_label_rx.config(text=now_utc)
    utc_clock_label_tx.config(text=now_utc)
    root.after(1000, update_utc_clock)

def HAM_transmit():
    # Get inputs
    prefix = prefix_entry.get().strip() or None
    station_call = stationcall_entry.get().strip()
    suffix = suffix_entry.get().strip() or None

    # Validate callsign
    if not station_call:
        messagebox.showerror("Input Error", "Please enter a station callsign.")
        return

    # Validate coordinates
    try:
        lon = float(lon_entry.get())
        lat = float(lat_entry.get())
        bad_lon = (lon<-180) or (lon>180)
        bad_lat = (lat<-90) or (lat>90)
        if bad_lon and bad_lat:
            messagebox.showerror("Input Error", "Impossible longitude and latitude.")
        elif bad_lon:
            messagebox.showerror("Input Error", "Impossible longitude.")
        elif bad_lat:
            messagebox.showerror("Input Error", "Impossible lattitude.")
    except ValueError:
        messagebox.showerror("Input Error", "Longitude and Latitude must be valid numbers.")
        return

    # Build message
    time_str = datetime.utcnow().strftime("%H:%M:%S")
    bits = brp.ham_msg(
        pre=prefix,
        call=station_call,
        suff=suffix,
        qth=(lon, lat),
        time=time_str
    )
    audio_data = brp.to_transmit_audio(bits)

    # Transmit in background so we don't freeze the GUI
    def _do_tx():
        HAM_tx_btn.config(text="Transmitting...", bg="red")
        try:
            brp.play_audio(audio_data=audio_data)
        finally:
            HAM_tx_btn.config(text="Transmit", bg="SystemButtonFace")

    threading.Thread(target=_do_tx, daemon=True).start()

def add_log(rx_tree : ttk.Treeview, UTC : str, Call : str, loc : str, full_msg : str):
    rx_tree.insert("", "end", values=(UTC, Call, loc, full_msg))

def HAM_receive():
    rx_audio_data = brp.listen_record()
    rx_dominant_freqs = brp.to_dominant_freqs(rx_audio_data)
    rx_bit_data = brp.freqs_to_bits(rx_dominant_freqs)
    
    return


# TAB CONSTRUCTION

# HAM TX
tk.Label(HAM_tab, text="HAM", height=1, width=4, bd=3, relief="solid", font=("Helvetica",24, "bold"), anchor="s").grid(column=0, row=0, sticky="w")
tk.Label(HAM_tab, text="Station Prefix", width=10, font=("Helvetica", 9, "bold"), anchor="s").grid(column=1, row=0, padx=3, pady=3)
prefix_entry = tk.Entry(HAM_tab, width=20)
prefix_entry.grid(column=2, row=0, padx=3, pady=3)
utc_clock_label_ham = tk.Label(HAM_tab, font=("Helvetica", 22, "bold"))
utc_clock_label_ham.grid(column=4, row=0, columnspan=2, pady=3, sticky="e")
tk.Label(HAM_tab, text="Station Callsign", width=12, font=("Helvetica", 9, "bold"), justify=tk.CENTER).grid(column=0, row=1, padx=3, pady=3)
stationcall_entry = tk.Entry(HAM_tab, width=20)
stationcall_entry.grid(column=1, row=1, padx=3, pady=3)
tk.Label(HAM_tab, text="Operator Callsign", width=15, font=("Helvetica", 9, "bold"), justify=tk.CENTER).grid(column=2, row=1, padx=3, pady=3)
opcall_entry = tk.Entry(HAM_tab, width=20)
opcall_entry.grid(column=3, row=1, padx=3, pady=3)
tk.Label(HAM_tab, text="Suffix", width=5, font=("Helvetica", 9, "bold"), justify=tk.CENTER).grid(column=4, row=1, padx=3, pady=3)
suffix_entry = tk.Entry(HAM_tab, width=20)
suffix_entry.grid(column=5, row=1, padx=3, pady=3)
tk.Label(HAM_tab, text="LON", width=5, font=("Helvetica", 9, "bold"), justify=tk.CENTER).grid(column=0, row=2, padx=1, pady=1)
lon_entry = tk.Entry(HAM_tab, width=20)
lon_entry.grid(column=1, row=2, padx=1, pady=1)
tk.Label(HAM_tab, text="LAT", width=5, font=("Helvetica", 9, "bold"), justify=tk.CENTER).grid(column=2, row=2, padx=1, pady=1)
lat_entry = tk.Entry(HAM_tab, width=20)
lat_entry.grid(column=3, row=2, padx=1, pady=1)
HAM_tx_btn = tk.Button(HAM_tab, width=20,text="TRANSMIT", font=("Helvetica", 9, "bold"), command=HAM_transmit)
HAM_tx_btn.grid(column=4, row=2, columnspan=2, padx=3, pady=3)

# HAM RX & LOG
HAM_rx_btn = tk.Button(HAM_tab, width=20,text="RECEIVE", font=("Helvetica", 9, "bold"), command=HAM_receive)
HAM_rx_btn.grid(column=0, row=3, padx=3, pady=3)

columns = ("Time", "Callsign", "Location", "Message")
HAM_rx_tree = ttk.Treeview(HAM_tab, columns=columns, show='headings', height=10)
for col in columns:
    HAM_rx_tree.heading(col, text=col)
HAM_rx_tree.column("Time", width=80, anchor="center", stretch=False)
HAM_rx_tree.column("Callsign", width=110, anchor="center", stretch=False)
HAM_rx_tree.column("Location", width=100, anchor="center", stretch=True)
HAM_rx_tree.column("Message", width=300, anchor="w", stretch=True)
HAM_rx_tree.grid(row=4, column=0, columnspan=7, padx=10, pady=10, sticky="nsew")
for i in range(7):
    HAM_tab.grid_columnconfigure(i, weight=1)
HAM_tab.grid_rowconfigure(4, weight=1)
add_log(HAM_rx_tree, "12:10:12", "4X/RU8SX/MM", "12, 31","TEST")


# ------------ RX TAB ------------

# FUNCTIONS

def RX_receive():
    print("WIP")
    return

# TAB CONSTRUCTION

tk.Label(RX_tab, text="RX", height=1, width=4, bd=4, relief="solid", font=("Helvetica",24, "bold")).grid(column=0, row=0, sticky="w")
utc_clock_label_rx = tk.Label(RX_tab, font=("Helvetica", 22, "bold"))
utc_clock_label_rx.grid(column=6, row=0, columnspan=2, pady=3, sticky="e")
RX_btn = tk.Button(RX_tab, width=20,text="RECEIVE", font=("Helvetica", 9, "bold"), command=RX_receive)
RX_btn.grid(column=0, row=1, pady=4, sticky="w")

for i in range(7):
    RX_tab.grid_columnconfigure(i, weight=1)


# ------------ TX TAB ------------

# FUNCTIONS


# TAB CONSTRUCTION

tk.Label(TX_tab, text="TX", height=1, width=4, bd=4, relief="solid", font=("Helvetica",24, "bold")).grid(column=0, row=0, sticky="w")
utc_clock_label_tx = tk.Label(TX_tab, font=("Helvetica", 22, "bold"))
utc_clock_label_tx.grid(column=6, row=0, columnspan=2, pady=3, sticky="e")

for i in range(7):
    TX_tab.grid_columnconfigure(i, weight=1)

update_utc_clock()
root.mainloop()