# The BioRP project - by K. Dekel 4X5KD
# Version: ALPHA 1

import BIORP_Utilities as brp
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from datetime import datetime
import threading
import pyaudio

root = tk.Tk() # Create and name the window
root.title("BioRP by 4X5KD")
root.iconphoto(False, tk.PhotoImage(file="src/top_icon.png"))
root.minsize(800, 400)
tabControl = ttk.Notebook(root) # Tab control

# ------------ GLOBAL PARAMS ------------

rx_running = False
rx_thread = None

tx_running = False
tx_thread = None

STD_FORMAT = brp.STD_FORMAT
STD_CHUNK = brp.STD_CHUNK
STD_CHAN = brp.STD_CHAN
STD_RATE = brp.STD_RATE
STD_TX = brp.STD_TX
frequencies = brp.frequencies

# ------------ MENUS ------------

# FUNCTIONS
is_full_view = True
def toggleView():
    global is_full_view
    if is_full_view:
        # Switch to HAM mode (remove RX and TX)
        tabControl.forget(TEXT_tab)
        tabControl.forget(IMG_tab)
    else:
        # Switch to FULL mode (add RX and TX back)
        tabControl.add(TEXT_tab, text='TEXT')
        tabControl.add(IMG_tab, text='WIP')
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
TEXT_tab = ttk.Frame(tabControl)
IMG_tab = ttk.Frame(tabControl)
HAM_tab = ttk.Frame(tabControl)

# Adding tabs to tab control
tabControl.add(HAM_tab, text ='HAM')
tabControl.add(TEXT_tab, text ='TEXT') 
tabControl.add(IMG_tab, text ='WIP') 
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
    global tx_running, tx_thread, rx_running

    if rx_running: # No TX while RX
        return
    
    if tx_running: # Stop TX if pressed again
        print("TX END")
        tx_running = False
        return

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
    msg = brp.ham_msg(
        pre=prefix,
        call=station_call,
        suff=suffix,
        qth=(lon, lat),
        time=time_str
    )

    # Transmit in background so we don't freeze the GUI
    audio_data = brp.to_transmit_audio(brp.to_protocol(msg, mode='01'))

    def _do_tx():
        global tx_running
        HAM_tx_btn.config(text="Transmitting...", bg="orange red")
        HAM_rx_btn.config(state="disabled")

        p = pyaudio.PyAudio()
        stream = p.open(format=STD_FORMAT, channels=STD_CHAN, rate=STD_RATE, output=True)

        try:
            pos = 0
            chunk = STD_CHUNK
            while tx_running and pos < len(audio_data):
                end = min(pos + chunk, len(audio_data))
                stream.write(audio_data[pos:end].tobytes())
                pos = end
        finally:
            stream.stop_stream()
            stream.close()
            p.terminate()

            tx_running = False
            HAM_tx_btn.config(text="TRANSMIT", bg="SystemButtonFace")
            HAM_rx_btn.config(state="normal")


    tx_thread = threading.Thread(target=_do_tx, daemon=True)
    tx_thread.start()

def add_log(rx_tree : ttk.Treeview, UTC : str, Call : str, loc : str, full_msg : str):
    rx_tree.insert("", "end", values=(UTC, Call, loc, full_msg))

def HAM_receive():
    global rx_running, rx_thread, tx_running

    if tx_running: # No RX while TX
        return

    def _do_rx():
        global rx_running
        HAM_rx_btn.config(text="Receiving...", bg="royal blue")
        HAM_tx_btn.config(state="disabled")

        while rx_running:
            try:

                data_bytes, mode, filetype = brp.handle_rx()
                if mode != '01': # Received non-HAM message.
                    print("Non-HAM message received, continuing RX.")
                    continue
                
                # Decode data
                msg = data_bytes.decode('utf-8', errors='replace')
                print("HAM MESSAGE:", msg)

                try: # Parsing the message
                    call, loc, utc_time = msg.split("|")
                except ValueError:
                    print("Invalid HAM format")
                    break

                add_log(HAM_rx_tree, utc_time, call, loc, msg)
                break
            except Exception as e:
                print("Error in HAM_receive(): ", e)
                break
        
        rx_running = False
        # Return buttons to normal state
        HAM_rx_btn.config(text="RECEIVE", bg="SystemButtonFace")
        HAM_tx_btn.config(state="normal")
    
    if rx_running: # Stop RX if pressed again
        print("RX END")
        rx_running = False
    else: # First press to begin RX
        print("RX BEGIN")
        rx_running = True
        rx_thread = threading.Thread(target=_do_rx, daemon=True)
        rx_thread.start()


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


# ------------ TEXT TAB ------------

# FUNCTIONS

def TEXT_receive():
    print("WIP")
    return

# TAB CONSTRUCTION

tk.Label(TEXT_tab, text="TEXT", height=1, width=4, bd=4, relief="solid", font=("Helvetica",24, "bold")).grid(column=0, row=0, sticky="w")
utc_clock_label_rx = tk.Label(TEXT_tab, font=("Helvetica", 22, "bold"))
utc_clock_label_rx.grid(column=6, row=0, columnspan=2, pady=3, sticky="e")
RX_btn = tk.Button(TEXT_tab, width=20,text="RECEIVE", font=("Helvetica", 9, "bold"), command=TEXT_receive)
RX_btn.grid(column=0, row=1, pady=4, sticky="w")

for i in range(7):
    TEXT_tab.grid_columnconfigure(i, weight=1)


# ------------ IMG TAB ------------

# FUNCTIONS


# TAB CONSTRUCTION

tk.Label(IMG_tab, text="IMG", height=1, width=4, bd=4, relief="solid", font=("Helvetica",24, "bold")).grid(column=0, row=0, sticky="w")
utc_clock_label_tx = tk.Label(IMG_tab, font=("Helvetica", 22, "bold"))
utc_clock_label_tx.grid(column=6, row=0, columnspan=2, pady=3, sticky="e")

for i in range(7):
    IMG_tab.grid_columnconfigure(i, weight=1)

update_utc_clock()
root.mainloop()