import os
import hashlib
import threading
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from tkinter import messagebox
import datetime
import webbrowser


class ProgressPopup(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Sweeper")

        self.progress_label = ttk.Label(self, text="Indexing files...", style='Custom.TLabel')
        self.progress_label.pack(padx=10, pady=10)

        self.folder_list = tk.Listbox(self, width=60, height=10)
        self.folder_list.pack(padx=10, pady=(0, 10))

        self.indexed_files_label = ttk.Label(self, text="Indexed Files: 0", style='Custom.TLabel')
        self.indexed_files_label.pack(padx=10, pady=(0, 10))

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self, variable=self.progress_var)
        self.progress_bar.pack(padx=10, pady=(0, 10), fill=tk.X)

    def set_progress_label(self, text):
        self.progress_label.configure(text=text)

    def add_folder(self, folder_path):
        self.folder_list.insert(tk.END, folder_path)

    def update_indexed_files_label(self, count):
        self.indexed_files_label.configure(text=f"Indexed Files: {count}")

    def set_progress(self, value):
        self.progress_var.set(value)


class DupliSweep:
    def __init__(self, root):
        self.root = root
        self.root.title("DupliSweep - by Sneaky / TnyavnTo")
        self.root.configure(bg="dark red")

        # frame to hold the folder selection button
        folder_frame = ttk.Frame(self.root, padding=(15, 15, 15, 0), style='Custom.TFrame')
        folder_frame.pack(fill=tk.X)

        # button to select a folder
        select_folder_button = ttk.Button(folder_frame, text="Select Folder", command=self.select_folder)
        select_folder_button.pack(side=tk.LEFT)

        # label to display the selected folder path
        self.folder_label = ttk.Label(folder_frame, text="No folder selected", style='Custom.TLabel')
        self.folder_label.pack(side=tk.LEFT, padx=(15, 0))

        separator = ttk.Separator(self.root, orient=tk.HORIZONTAL)
        separator.pack(fill=tk.X, pady=10)

        # frame to hold the treeview
        treeview_frame = ttk.Frame(self.root)
        treeview_frame.pack(fill=tk.BOTH, expand=True)

        # treeview to display the folder structure and duplicate files
        self.treeview = ttk.Treeview(treeview_frame)
        self.treeview.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # scrollbars for the treeview
        vertical_scrollbar = ttk.Scrollbar(treeview_frame, orient=tk.VERTICAL, command=self.treeview.yview)
        vertical_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.treeview.configure(yscrollcommand=vertical_scrollbar.set)

        # treeview columns
        self.treeview['columns'] = ('Path', 'Size', 'Hash')
        self.treeview.column('#0', width=250, minwidth=80, anchor=tk.W)
        self.treeview.column('Path', width=350, minwidth=120, anchor=tk.W)
        self.treeview.column('Size', width=50, minwidth=80, anchor=tk.CENTER)
        self.treeview.column('Hash', width=150, minwidth=120, anchor=tk.W)

        # treeview headings
        self.treeview.heading('#0', text='Name', anchor=tk.W)
        self.treeview.heading('Path', text='Path', anchor=tk.W)
        self.treeview.heading('Size', text='Size', anchor=tk.CENTER)
        self.treeview.heading('Hash', text='Hash', anchor=tk.W)

        # frame to hold the buttons
        buttons_frame = ttk.Frame(self.root, padding=(15, 0, 15, 10), style='Custom.TFrame')
        buttons_frame.pack(fill=tk.X)

        # button to remove duplicates
        remove_duplicates_button = ttk.Button(buttons_frame, text="Remove Duplicates", command=self.remove_duplicates)
        remove_duplicates_button.pack(side=tk.RIGHT, pady=15)

        # button to open the source code link
        source_code_button = ttk.Button(buttons_frame, text="Source Code", command=self.open_source_code)
        source_code_button.pack(side=tk.LEFT, pady=15)

        # button to preview the selected duplicate file
        preview_button = ttk.Button(buttons_frame, text="Preview", command=self.preview_duplicate)
        preview_button.pack(side=tk.RIGHT, padx=10, pady=15)

        self.indexed_duplicates = set()
        self.file_dict = {}

    def select_folder(self):
        """open a folder selection dialog and update the selected folder label."""
        folder_path = filedialog.askdirectory()

        if folder_path:
            self.folder_label.configure(text=folder_path)
            threading.Thread(target=self.scan_folder, args=(folder_path,), daemon=True).start()

    def scan_folder(self, folder_path):
        """scan a folder and find duplicate files based on selected criteria."""
        self.treeview.delete(*self.treeview.get_children())
        self.indexed_duplicates.clear()

        progress_popup = ProgressPopup(self.root)
        progress_popup.geometry("420x325")

        indexed_files = 0
        progress_value = 0
        total_files = 0

        def update_progress_label(text):
            progress_popup.set_progress_label(text)
            self.root.update_idletasks()

        def update_indexed_files_label(count):
            progress_popup.update_indexed_files_label(count)
            self.root.update_idletasks()

        def update_progress(value):
            progress_popup.set_progress(value)
            self.root.update_idletasks()

        def populate_treeview(file_dict):
            # sort file_dict by hash value and mark duplicates with red
            for file_hash, duplicates in sorted(file_dict.items(), key=lambda x: x[0]):
                parent = ''
                for file, file_path, file_size, _ in duplicates:
                    tags = ()
                    if len(duplicates) > 1:
                        tags = ('red',)

                    if parent == '':
                        parent = self.treeview.insert('', 'end', text=file, values=(file_path, file_size, file_hash),
                                                      tags=tags)
                    else:
                        self.treeview.insert(parent, 'end', text=file, values=(file_path, file_size, file_hash),
                                             tags=tags)

        def calculate_hash(file_path):
            sha256_hash = hashlib.sha256()
            with open(file_path, "rb") as file:
                for chunk in iter(lambda: file.read(4096), b""):
                    sha256_hash.update(chunk)
            return sha256_hash.hexdigest()

        def index_files(folder_path):
            nonlocal indexed_files, progress_value, total_files

            for root, _, files in os.walk(folder_path):
                update_progress_label(f"Indexing files in {root}")
                progress_popup.add_folder(root)
                update_indexed_files_label(indexed_files)

                for file in files:
                    file_path = os.path.join(root, file)
                    file_size = os.path.getsize(file_path)
                    file_hash = calculate_hash(file_path)

                    if file_hash in self.file_dict:
                        self.file_dict[file_hash].append((file, file_path, file_size, root))
                        self.indexed_duplicates.add(file_hash)
                    else:
                        self.file_dict[file_hash] = [(file, file_path, file_size, root)]

                    indexed_files += 1
                    progress_value = (indexed_files / total_files) * 100
                    update_progress(progress_value)

                    # update treeview as files are indexed
                    self.treeview.insert('', 'end', text=file, values=(file_path, file_size, file_hash))
                    self.treeview.update_idletasks()

                    # auto scroll down the treeview
                    self.treeview.yview_moveto(1)

        total_files = sum(len(files) for _, _, files in os.walk(folder_path))

        t1 = threading.Thread(target=index_files, args=(folder_path,), daemon=True)
        t1.start()

        self.root.wait_window(progress_popup)

        populate_treeview(self.file_dict)
        if indexed_files == total_files:
            messagebox.showinfo("Indexing Complete", f"Successfully Indexed {indexed_files} files.")
        else:
            t1.join()
            messagebox.showinfo("Indexing Cancelled", "Indexing process was cancelled.")

    def preview_duplicate(self):
        """preview the selected duplicate file."""
        selected_item = self.treeview.focus()

        if selected_item:
            file_path = self.treeview.item(selected_item)['values'][0]
            if os.path.isfile(file_path):
                os.startfile(file_path)
            else:
                messagebox.showinfo("Error", "The file no longer exists.")

    def remove_duplicates(self):
        """remove the selected duplicate files, keeping one copy of each duplicate."""
        if not self.indexed_duplicates:
            messagebox.showinfo("Error", "No duplicates found. If you suspect this is a false output and that there are in fact duplicate files present, this could be due to their size and hash strings being different regardless of file content. This is a rare occurrence, but I would greatly appreciate feedback @SneakyV2_ on Twitter.")
            return

        deleted_count = 0
        log_file_path = "sweep_results.txt"

        with open(log_file_path, "a") as log_file:
            log_file.write("DupliSweep Results - {}\n".format(datetime.datetime.now()) + "\n")

            for file_hash in self.indexed_duplicates:
                duplicates = self.file_dict[file_hash]
                # keep the first duplicate, remove the rest
                for i in range(1, len(duplicates)):
                    _, file_path, _, _ = duplicates[i]
                    try:
                        os.remove(file_path)
                        log_file.write("File: {}\n".format(file_path))
                        deleted_count += 1
                    except OSError:
                        pass

            log_file.write("\n")

        self.treeview.delete(*self.treeview.get_children())
        self.indexed_duplicates.clear()
        messagebox.showinfo("Duplicates Removed", f"A total of {deleted_count} indexed duplicate files have been removed. A 'sweep_results.txt' file has been created with a list of deleted files.")

    def open_source_code(self):
        """open the source code link in a web browser."""
        webbrowser.open("https://github.com/svxy/DupliSweep")

def main():
    root = tk.Tk()
    root.geometry("1280x720")
    root.resizable(False, False)

    style = ttk.Style()
    style.configure('Custom.TLabel', foreground='white', background='dark red')
    style.configure('Custom.TFrame', background='dark red')
    style.configure('Red.Treeview', foreground='white', background='red')

    DupliSweep(root)

    root.mainloop()

if __name__ == "__main__":
    main()
