"""Main tkinter GUI for the Outlook File Repair Tool."""

import datetime
import os
import platform
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
from typing import Dict, List, Optional


class OutlookRepairApp:
    APP_TITLE = 'Outlook File Repair Tool'
    APP_VERSION = '1.0.0'

    def __init__(self):
        self.root = tk.Tk()
        self.found_files: List[Dict] = []
        self.selected_file: Optional[Dict] = None
        self._stop_event = threading.Event()
        self._setup_window()
        self._setup_styles()
        self._build_ui()

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def _setup_window(self):
        self.root.title(f'{self.APP_TITLE} v{self.APP_VERSION}')
        self.root.geometry('960x680')
        self.root.minsize(800, 580)
        self.root.update_idletasks()
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        self.root.geometry(f'960x680+{(sw-960)//2}+{(sh-680)//2}')

    def _setup_styles(self):
        s = ttk.Style()
        for theme in ('vista', 'winnative', 'clam', 'alt', 'default'):
            if theme in s.theme_names():
                s.theme_use(theme)
                break
        s.configure('H.TLabel', font=('Segoe UI', 12, 'bold'))
        s.configure('Action.TButton', padding=(12, 5))

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        hdr = ttk.Frame(self.root, padding=(12, 8))
        hdr.pack(fill=tk.X)
        ttk.Label(hdr, text=self.APP_TITLE, style='H.TLabel').pack(side=tk.LEFT)
        ttk.Label(hdr, text=f'v{self.APP_VERSION}', foreground='gray').pack(side=tk.LEFT, padx=6)
        ttk.Separator(self.root).pack(fill=tk.X)

        self.nb = ttk.Notebook(self.root, padding=5)
        self.nb.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self._build_scanner_tab()
        self._build_repair_tab()
        self._build_recovery_tab()
        self._build_log_tab()

        ttk.Separator(self.root).pack(fill=tk.X)
        bar = ttk.Frame(self.root, padding=(10, 3))
        bar.pack(fill=tk.X)
        self._status_lbl = ttk.Label(bar, text='Ready')
        self._status_lbl.pack(side=tk.LEFT)
        ttk.Label(bar, text=f'{platform.system()} {platform.release()}',
                  foreground='gray').pack(side=tk.RIGHT)

    # ---------- Scanner tab ----------

    def _build_scanner_tab(self):
        f = ttk.Frame(self.nb, padding=10)
        self.nb.add(f, text='  Scanner  ')

        ctrl = ttk.Frame(f)
        ctrl.pack(fill=tk.X, pady=(0, 6))
        ttk.Button(ctrl, text='Scan System', style='Action.TButton',
                   command=self._scan_system).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(ctrl, text='Add Folder…', command=self._add_folder).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(ctrl, text='Add File…', command=self._add_file_manually).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(ctrl, text='Clear', command=self._clear_list).pack(side=tk.LEFT, padx=(0, 4))
        self._stop_btn = ttk.Button(ctrl, text='Stop', command=self._stop_scan, state=tk.DISABLED)
        self._stop_btn.pack(side=tk.LEFT)
        ttk.Button(ctrl, text='Use Selected →', style='Action.TButton',
                   command=self._use_selected).pack(side=tk.RIGHT)

        lf = ttk.LabelFrame(f, text='Found Files', padding=5)
        lf.pack(fill=tk.BOTH, expand=True)

        cols = ('name', 'type', 'size', 'path', 'status')
        self.tree = ttk.Treeview(lf, columns=cols, show='headings', selectmode='browse')
        for col, w, label in [
            ('name', 200, 'File Name'), ('type', 190, 'Type'),
            ('size', 80, 'Size'), ('path', 320, 'Path'), ('status', 90, 'Status'),
        ]:
            self.tree.heading(col, text=label)
            self.tree.column(col, width=w, minwidth=60,
                             anchor='e' if col == 'size' else 'w')

        vsb = ttk.Scrollbar(lf, orient=tk.VERTICAL, command=self.tree.yview)
        hsb = ttk.Scrollbar(lf, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        lf.grid_rowconfigure(0, weight=1)
        lf.grid_columnconfigure(0, weight=1)
        self.tree.bind('<Double-1>', lambda _e: self._use_selected())

        pf = ttk.Frame(f)
        pf.pack(fill=tk.X, pady=(6, 0))
        self._scan_lbl = ttk.Label(pf, text='Ready')
        self._scan_lbl.pack(side=tk.LEFT)
        self._scan_bar = ttk.Progressbar(pf, mode='indeterminate', length=180)
        self._scan_bar.pack(side=tk.RIGHT)

    # ---------- Repair tab ----------

    def _build_repair_tab(self):
        f = ttk.Frame(self.nb, padding=10)
        self.nb.add(f, text='  Repair  ')

        sf = ttk.LabelFrame(f, text='Target File', padding=10)
        sf.pack(fill=tk.X, pady=(0, 8))
        self._repair_lbl = ttk.Label(sf,
            text='No file selected — use Scanner or Browse.', foreground='gray')
        self._repair_lbl.pack(anchor='w')
        ttk.Button(sf, text='Browse…', command=self._browse_repair).pack(anchor='w', pady=(4, 0))

        vf = ttk.LabelFrame(f, text='Validation Result', padding=10)
        vf.pack(fill=tk.X, pady=(0, 8))
        self._valid_lbl = ttk.Label(vf, text='Not validated yet.')
        self._valid_lbl.pack(anchor='w')
        self._valid_txt = scrolledtext.ScrolledText(
            vf, height=4, state=tk.DISABLED, font=('Consolas', 9), wrap=tk.WORD)
        self._valid_txt.pack(fill=tk.X, pady=(4, 0))

        of = ttk.LabelFrame(f, text='Options', padding=10)
        of.pack(fill=tk.X, pady=(0, 8))
        self._do_backup = tk.BooleanVar(value=True)
        self._use_scanpst = tk.BooleanVar(value=True)
        ttk.Checkbutton(of, text='Create .bak backup before repair',
                        variable=self._do_backup).pack(anchor='w')
        ttk.Checkbutton(of, text='Use scanpst.exe if available (Windows)',
                        variable=self._use_scanpst).pack(anchor='w')

        bf = ttk.Frame(f)
        bf.pack(fill=tk.X, pady=(0, 6))
        ttk.Button(bf, text='Validate', style='Action.TButton',
                   command=self._do_validate).pack(side=tk.LEFT, padx=(0, 6))
        self._repair_btn = ttk.Button(bf, text='Repair', style='Action.TButton',
                                      command=self._do_repair)
        self._repair_btn.pack(side=tk.LEFT)

        self._repair_bar = ttk.Progressbar(f, mode='indeterminate')
        self._repair_bar.pack(fill=tk.X, pady=(0, 4))
        self._repair_status = ttk.Label(f, text='')
        self._repair_status.pack(anchor='w')

    # ---------- Recovery tab ----------

    def _build_recovery_tab(self):
        f = ttk.Frame(self.nb, padding=10)
        self.nb.add(f, text='  Recovery  ')

        sf = ttk.LabelFrame(f, text='Source PST/OST File', padding=10)
        sf.pack(fill=tk.X, pady=(0, 8))
        self._rec_src = tk.StringVar()
        row = ttk.Frame(sf)
        row.pack(fill=tk.X)
        ttk.Entry(row, textvariable=self._rec_src, state='readonly').pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        ttk.Button(row, text='Browse…', command=self._browse_rec_src).pack(side=tk.RIGHT)

        of = ttk.LabelFrame(f, text='Output Directory', padding=10)
        of.pack(fill=tk.X, pady=(0, 8))
        self._rec_out = tk.StringVar(value=str(
            __import__('pathlib').Path.home() / 'recovered_emails'))
        row2 = ttk.Frame(of)
        row2.pack(fill=tk.X)
        ttk.Entry(row2, textvariable=self._rec_out).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        ttk.Button(row2, text='Browse…', command=self._browse_rec_out).pack(side=tk.RIGHT)

        ff = ttk.LabelFrame(f, text='Output Format', padding=10)
        ff.pack(fill=tk.X, pady=(0, 8))
        self._rec_fmt = tk.StringVar(value='eml')
        for val, label in [('eml', 'EML  —  individual files, importable into email clients'),
                           ('csv', 'CSV  —  spreadsheet with all emails'),
                           ('txt', 'TXT  —  plain text file')]:
            ttk.Radiobutton(ff, text=label, variable=self._rec_fmt, value=val).pack(anchor='w')

        bf = ttk.Frame(f)
        bf.pack(fill=tk.X, pady=(0, 6))
        ttk.Button(bf, text='Start Recovery', style='Action.TButton',
                   command=self._start_recovery).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(bf, text='Open Output Folder',
                   command=self._open_out_folder).pack(side=tk.LEFT)

        self._rec_bar = ttk.Progressbar(f, mode='indeterminate')
        self._rec_bar.pack(fill=tk.X, pady=(0, 4))
        self._rec_status = ttk.Label(f, text='')
        self._rec_status.pack(anchor='w', pady=(0, 4))

        rlf = ttk.LabelFrame(f, text='Progress', padding=5)
        rlf.pack(fill=tk.BOTH, expand=True)
        self._rec_log = scrolledtext.ScrolledText(
            rlf, state=tk.DISABLED, font=('Consolas', 9), wrap=tk.WORD, height=6)
        self._rec_log.pack(fill=tk.BOTH, expand=True)

    # ---------- Log tab ----------

    def _build_log_tab(self):
        f = ttk.Frame(self.nb, padding=10)
        self.nb.add(f, text='  Log  ')
        bf = ttk.Frame(f)
        bf.pack(fill=tk.X, pady=(0, 6))
        ttk.Button(bf, text='Clear', command=self._clear_log).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(bf, text='Save…', command=self._save_log).pack(side=tk.LEFT)
        self.log_txt = scrolledtext.ScrolledText(
            f, state=tk.DISABLED, font=('Consolas', 9), wrap=tk.WORD,
            bg='#1e1e1e', fg='#d4d4d4')
        self.log_txt.pack(fill=tk.BOTH, expand=True)
        self.log_txt.tag_config('info', foreground='#9cdcfe')
        self.log_txt.tag_config('success', foreground='#4ec9b0')
        self.log_txt.tag_config('error', foreground='#f44747')
        self.log_txt.tag_config('warning', foreground='#ce9178')
        self.log_txt.tag_config('ts', foreground='#606060')

    # ------------------------------------------------------------------
    # Scanner handlers
    # ------------------------------------------------------------------

    def _scan_system(self):
        from outlook_repair.core.scanner import get_default_scan_paths, scan_directory
        self._stop_event.clear()
        self._scan_bar.start()
        self._stop_btn.config(state=tk.NORMAL)
        paths = get_default_scan_paths()
        self._log(f'Scanning {len(paths)} default path(s)...')

        def run():
            for p in paths:
                if self._stop_event.is_set():
                    break
                self._ui(self._scan_lbl.config, text=f'Scanning: {p[:70]}')
                scan_directory(p, callback=self._file_found_cb, stop_event=self._stop_event)
            self._ui(self._finish_scan)

        threading.Thread(target=run, daemon=True).start()

    def _add_folder(self):
        folder = filedialog.askdirectory(title='Select folder to scan')
        if not folder:
            return
        from outlook_repair.core.scanner import scan_directory
        self._stop_event.clear()
        self._scan_bar.start()
        self._log(f'Scanning: {folder}')

        def run():
            scan_directory(folder, callback=self._file_found_cb, stop_event=self._stop_event)
            self._ui(self._finish_scan)

        threading.Thread(target=run, daemon=True).start()

    def _add_file_manually(self):
        path = filedialog.askopenfilename(
            title='Select Outlook file',
            filetypes=[('Outlook Files', '*.pst *.ost *.lst'), ('All Files', '*.*')])
        if not path:
            return
        from outlook_repair.core.scanner import _build_info
        from pathlib import Path
        try:
            info = _build_info(Path(path))
        except OSError as e:
            messagebox.showerror('Error', f'Cannot read file info:\n{e}')
            return
        self._add_to_tree(info)
        self._log(f'Added: {path}')

    def _clear_list(self):
        self.tree.delete(*self.tree.get_children())
        self.found_files.clear()
        self._scan_lbl.config(text='Cleared')

    def _stop_scan(self):
        self._stop_event.set()
        self._stop_btn.config(state=tk.DISABLED)

    def _use_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning('No selection', 'Select a file first.')
            return
        vals = self.tree.item(sel[0], 'values')
        path = vals[3]
        self.selected_file = {'path': path, 'name': vals[0]}
        self._repair_lbl.config(text=path, foreground='black')
        self._rec_src.set(path)
        self.nb.select(1)
        self._log(f'Selected for repair: {path}')

    def _file_found_cb(self, info: Dict):
        self._ui(self._add_to_tree, info)

    def _add_to_tree(self, info: Dict):
        p = info['path']
        for iid in self.tree.get_children():
            if self.tree.item(iid, 'values')[3] == p:
                return
        self.tree.insert('', tk.END,
            values=(info['name'], info['type'], info['size_str'], p, 'Found'))
        self.found_files.append(info)
        self._status_lbl.config(text=f'{len(self.found_files)} file(s) found')

    def _finish_scan(self):
        self._scan_bar.stop()
        self._stop_btn.config(state=tk.DISABLED)
        n = len(self.found_files)
        self._scan_lbl.config(text=f'Done — {n} file(s) found')
        self._log(f'Scan complete: {n} file(s)', 'success')

    # ------------------------------------------------------------------
    # Repair handlers
    # ------------------------------------------------------------------

    def _browse_repair(self):
        p = filedialog.askopenfilename(
            title='Select file to repair',
            filetypes=[('Outlook Files', '*.pst *.ost *.lst'), ('All Files', '*.*')])
        if p:
            self._repair_lbl.config(text=p, foreground='black')
            self.selected_file = {'path': p}

    def _get_repair_path(self) -> Optional[str]:
        t = self._repair_lbl.cget('text')
        if 'No file' in t or not t:
            messagebox.showwarning('No file', 'Select a file first.')
            return None
        return t

    def _do_validate(self):
        path = self._get_repair_path()
        if not path:
            return
        from outlook_repair.core.validator import validate_file
        self._log(f'Validating: {path}')

        def run():
            r = validate_file(path)
            self._ui(self._show_validation, r, path)

        threading.Thread(target=run, daemon=True).start()

    def _show_validation(self, r, path: str):
        ok = r.is_valid
        self._valid_lbl.config(
            text=('✓ ' if ok else '✗ ') + r.summary,
            foreground='green' if ok else 'red')
        lines = [f'File: {path}', f'Size: {r.file_size:,} bytes',
                 f'Type: {r.file_type}', f'Version: {r.version}']
        if r.errors:
            lines += ['', 'Errors:'] + [f'  • {e}' for e in r.errors]
        if r.warnings:
            lines += ['', 'Warnings:'] + [f'  • {w}' for w in r.warnings]
        self._valid_txt.config(state=tk.NORMAL)
        self._valid_txt.delete('1.0', tk.END)
        self._valid_txt.insert('1.0', '\n'.join(lines))
        self._valid_txt.config(state=tk.DISABLED)
        self._update_tree_status(path, 'Valid' if ok else 'Corrupt')
        self._log(f'Validation: {r.summary}', 'success' if ok else 'error')

    def _do_repair(self):
        path = self._get_repair_path()
        if not path or not os.path.isfile(path):
            messagebox.showerror('Not found', f'File not found:\n{path}')
            return
        backup_note = 'A backup will be created.' if self._do_backup.get() else 'NO backup will be created.'
        if not messagebox.askyesno('Confirm', f'Repair:\n{path}\n\n{backup_note}'):
            return

        from outlook_repair.core import backup as bkp_mod
        from outlook_repair.core.repair import repair_file

        # Snapshot checkbox values on the main thread before handing off
        do_backup = self._do_backup.get()
        use_scanpst = self._use_scanpst.get()

        self._repair_btn.config(state=tk.DISABLED)
        self._repair_bar.start()

        def run():
            backup_path = None
            if do_backup:
                try:
                    self._ui(self._repair_status.config, text='Creating backup...')
                    backup_path = bkp_mod.create_backup(path)
                    self._log(f'Backup: {backup_path}', 'success')
                except Exception as e:
                    self._log(f'Backup failed: {e} — repair aborted', 'error')
                    # Must show dialog on main thread; abort rather than ask
                    self._ui(messagebox.showerror, 'Backup Failed',
                             f'Could not create backup:\n{e}\n\nRepair aborted.')
                    self._ui(self._repair_done)
                    return

            def cb(msg: str):
                self._log(msg)
                self._ui(self._repair_status.config, text=msg[:100])

            result = repair_file(
                path,
                backup_path=backup_path,
                progress_callback=cb,
                use_scanpst=use_scanpst,
            )
            self._ui(self._show_repair_result, result, path)

        threading.Thread(target=run, daemon=True).start()

    def _show_repair_result(self, result, path: str):
        self._repair_done()
        if result.success:
            self._repair_status.config(text='Repair complete.')
            self._update_tree_status(path, 'Repaired')
            self._log(f'Repair OK via {result.method}', 'success')
            messagebox.showinfo('Done', f'Repair successful.\nMethod: {result.method}'
                                + (f'\nBackup: {result.backup_path}' if result.backup_path else ''))
        else:
            errs = '\n'.join(result.errors)
            self._repair_status.config(text='Repair failed.')
            self._log(f'Repair failed: {errs}', 'error')
            messagebox.showerror('Failed', f'Repair failed:\n{errs}')

    def _repair_done(self):
        self._repair_bar.stop()
        self._repair_btn.config(state=tk.NORMAL)

    # ------------------------------------------------------------------
    # Recovery handlers
    # ------------------------------------------------------------------

    def _browse_rec_src(self):
        p = filedialog.askopenfilename(
            title='Select PST/OST',
            filetypes=[('Outlook Data', '*.pst *.ost'), ('All Files', '*.*')])
        if p:
            self._rec_src.set(p)

    def _browse_rec_out(self):
        d = filedialog.askdirectory(title='Output directory')
        if d:
            self._rec_out.set(d)

    def _start_recovery(self):
        src = self._rec_src.get().strip()
        out = self._rec_out.get().strip()
        fmt = self._rec_fmt.get()
        if not src or not os.path.isfile(src):
            messagebox.showwarning('No source', 'Select a valid PST/OST file.')
            return
        if not out:
            messagebox.showwarning('No output', 'Specify an output directory.')
            return

        from outlook_repair.core.recovery import recover_emails
        self._rec_bar.start()
        self._log(f'Recovery started: {src} → {fmt.upper()} in {out}')

        def cb(msg: str):
            self._log(msg)
            self._ui(self._rec_status.config, text=msg[:100])
            self._ui(self._append_rec_log, msg)

        def run():
            result = recover_emails(src, out, fmt, cb)
            self._ui(self._show_recovery_result, result)

        threading.Thread(target=run, daemon=True).start()

    def _show_recovery_result(self, result: Dict):
        self._rec_bar.stop()
        n, fail = result['recovered'], result['failed']
        self._rec_status.config(text=f'Done — {n} recovered, {fail} failed')
        if n > 0:
            self._log(f'Recovery: {n} email(s) saved to {result["output_dir"]}', 'success')
            messagebox.showinfo('Done', f'{n} email(s) recovered.\n{result["output_dir"]}')
        else:
            errs = '; '.join(result.get('errors', []))
            self._log(f'Recovery: nothing recovered. {errs}', 'warning')
            messagebox.showwarning('Nothing recovered', errs or 'No emails found.')

    def _append_rec_log(self, msg: str):
        self._rec_log.config(state=tk.NORMAL)
        self._rec_log.insert(tk.END, msg + '\n')
        self._rec_log.see(tk.END)
        self._rec_log.config(state=tk.DISABLED)

    def _open_out_folder(self):
        out = self._rec_out.get().strip()
        if not out:
            return
        try:
            if platform.system() == 'Windows':
                os.startfile(out)
            elif platform.system() == 'Darwin':
                __import__('subprocess').Popen(['open', out])
            else:
                __import__('subprocess').Popen(['xdg-open', out])
        except Exception as e:
            messagebox.showerror('Error', str(e))

    # ------------------------------------------------------------------
    # Log handlers
    # ------------------------------------------------------------------

    def _clear_log(self):
        self.log_txt.config(state=tk.NORMAL)
        self.log_txt.delete('1.0', tk.END)
        self.log_txt.config(state=tk.DISABLED)

    def _save_log(self):
        p = filedialog.asksaveasfilename(
            defaultextension='.txt',
            filetypes=[('Text', '*.txt'), ('All', '*.*')])
        if not p:
            return
        self.log_txt.config(state=tk.NORMAL)
        content = self.log_txt.get('1.0', tk.END)
        self.log_txt.config(state=tk.DISABLED)
        try:
            with open(p, 'w', encoding='utf-8') as f:
                f.write(content)
            messagebox.showinfo('Saved', p)
        except OSError as e:
            messagebox.showerror('Error', str(e))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _log(self, msg: str, level: str = 'info'):
        ts = datetime.datetime.now().strftime('%H:%M:%S')

        def do():
            self.log_txt.config(state=tk.NORMAL)
            self.log_txt.insert(tk.END, f'[{ts}] ', 'ts')
            self.log_txt.insert(tk.END, msg + '\n', level)
            self.log_txt.see(tk.END)
            self.log_txt.config(state=tk.DISABLED)

        self._ui(do)

    def _ui(self, fn, *args, **kwargs):
        """Schedule *fn* on the main thread (safe to call from any thread)."""
        if threading.current_thread() is threading.main_thread():
            fn(*args, **kwargs)
        else:
            self.root.after(0, lambda: fn(*args, **kwargs))

    def _update_tree_status(self, path: str, status: str):
        for iid in self.tree.get_children():
            vals = list(self.tree.item(iid, 'values'))
            if vals[3] == path:
                vals[4] = status
                self.tree.item(iid, values=vals)
                break

    def run(self):
        self._log(f'{self.APP_TITLE} ready', 'success')
        self._log('Use the Scanner tab to find Outlook files.')
        self.root.mainloop()
