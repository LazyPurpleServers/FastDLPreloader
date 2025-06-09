#!/usr/bin/env python3
import sys, pathlib, argparse, time, re, bz2, time, threading
import urllib.request


crawl_files = 0
crawl_dirs = 0
crawl_start = 0

option_replace = False
stop_request = False


def log(string):
    print(string)


def create_index(url):
    global crawl_files, crawl_dirs

    path = url[url.index('/', url.index('.')):]
    log(f'-- Scanning {path}')
    with urllib.request.urlopen(url) as f:
        content = f.read().decode('utf-8')
    if stop_request:
        return []

    links = [x.group(1) for x in re.finditer(r'<a href="([^"]*)">', content)]
    links = [x for x in links if not x.startswith(('/','?'))] # remove meta links
    files = [url+x for x in links if not x.endswith('/')] # dirs end in /
    nfiles = len(files)
    ndirs = len(links)-nfiles
    crawl_files += nfiles
    crawl_dirs += ndirs
    log(f'   Files: {crawl_files} (+{nfiles})  Dirs: {crawl_dirs} (+{ndirs})')
    for sub in [x for x in links if x.endswith('/')]:
        crawl_dirs -= 1
        files = files + create_index(url + sub)
    return files


def fetch_and_unpack(url, path, progress):
    global option_replace, crawl_start

    path.parent.mkdir(parents=True, exist_ok=True)
    target = path.parent / path.name.removesuffix('.bz2') if path.name.endswith('.bz2') else path
    tmpfile = path.parent / (target.name+'.tmp')

    if target.exists() and not option_replace:
        return

    log(f'-- Downloading {progress[0]}/{progress[1]}: {target}')

    if path.name.endswith('.bz2'):
        decomp = bz2.BZ2Decompressor()
        with urllib.request.urlopen(url) as f, open(tmpfile, 'wb') as t:
            while chunk := f.read(16*1024):
                t.write(decomp.decompress(chunk))
    else:
        with urllib.request.urlopen(url) as f, open(tmpfile, 'wb') as t:
            while chunk := f.read(16*1024):
                t.write(chunk)

    if target.exists():
        target.unlink() # windows does not replace
    tmpfile.rename(target)


def download(target):
    global crawl_start
    baseurl = 'https://lazypurple.com/tf/fastdl/tf/' #<-- should end in slash
    files = create_index(baseurl)
    count = 0
    crawl_start = time.time()
    for next in files:
        if stop_request:
            return
        if not next.startswith(baseurl):
            continue
        relative = next[len(baseurl):]
        dest = target / relative
        count += 1
        fetch_and_unpack(next, dest, (count, len(files)))


def withGUI():
    import tkinter as tk  # install python3-tk
    from tkinter import messagebox as msgbox  # install python3-tk
    from tkinter import filedialog as filepicker  # install python3-tk
    if not msgbox.askokcancel('LazyPurple FastDL Preloader', """Hello player,
This tool will help you download all content on our FastDL.
First choose the directory to download into. Make sure you have around 90 GB of free disc space!
You can pick your games tf/download folder, a mod directory tf/custom/lazyfastdl or any other directory really."""):
        return

    global option_replace

    dlpath = filepicker.askdirectory(title='LazyPurple FastDL Preloader - Pick directory', mustexist=True)
    if not dlpath:
        return
    directory = pathlib.Path(dlpath)

    option_replace = msgbox.askquestion('LazyPurple FastDL Preloader', 'Do you want to replace files in the directory?') == 'yes'

    thread: threading.Thread = None
    hack = {"label": "<Waiting>"}
    root = tk.Tk()

    root.title('LazyPurple FastDL Preloader')
    root.geometry('800x64+50+50')
    root.resizable(True, False)

    def guiDownload():
        global log
        log = lambda msg: hack.__setitem__('label',msg)
        button.config(state='disabled')
        button.pack()
        thread = threading.Thread(target=download, args=(directory,))
        thread.start()
        return thread
    def closwWindow():
        global stop_request
        stop_request = True
        button.config(text='Stopping')
        button.pack()

    label = tk.Label(root, text="<Waiting>")
    label.pack()
    button = tk.Button(root, text="Start", command=guiDownload)
    button.pack()
    root.protocol("WM_DELETE_WINDOW", closwWindow)

    while not stop_request or (thread and thread.is_alive()):
        label.config(text = hack['label'])
        root.update()
        time.sleep(0.5)

    root.destroy()


def withTerminal(args):
    parser = argparse.ArgumentParser(prog='lp_fastdl_preloader', description='Download all of fastdl into a directory. Place this script into your tf2 installation directory, next to tf_win64.exe / tf_linux64. The default download directory of the game is "tf/download", but you can also download to a mod directory with "tf/custom/lazypurple".', epilog='Bottom text')
    parser.add_argument('-r', '--replace', action='store_true', help='Ignore existing files and replace them. If not set, existing files are ignored')
    parser.add_argument('--gui', action='store_true', help='Force TKinter GUI', required=False)
    parser.add_argument('-t', '--directory', type=pathlib.Path, required=True)
    arguments = parser.parse_args(args)
    if not (arguments.directory.is_dir() or (not arguments.directory.exists() and arguments.directory.parent.is_dir())):
        print('Target directory is not a directory or parent directory does not exist')
        sys.exit(1)

    global option_replace
    option_replace = arguments.replace
    arguments.directory.mkdir(exist_ok=True)
    #download(arguments.directory.resolve())


def main(args):
    if not args:
        if sys.stdin and sys.stdin.isatty():
            args = ['--help']
        else:
            withGUI()
            return
    if '--gui' in args:
        withGUI()
    else:
        withTerminal(args)


if __name__ == '__main__':
    main(sys.argv[1:])
