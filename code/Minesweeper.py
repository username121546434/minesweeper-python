from functools import partial
import pickle
import sys
from tkinter import *
from grid import ButtonGrid, PickleButtonGrid
from squares import PickleSquare, Square
from datetime import datetime
from tkinter import filedialog, messagebox
import os
from updater import check_for_updates
import ctypes
from custom_menubar import CustomMenuBar
import logging
from ctypes import wintypes

__version__ = '1.3.0'
__license__ = 'GNU GPL v3, see LICENSE.txt for more info'

user32 = ctypes.WinDLL('user32', use_last_error=True)
kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

kernel32.GetConsoleWindow.restype = wintypes.HWND
user32.SendMessageW.argtypes = (wintypes.HWND, wintypes.UINT,
    wintypes.WPARAM, wintypes.LPARAM)
user32.ShowWindow.argtypes = (wintypes.HWND, ctypes.c_int)

SW_HIDE = 0
SW_SHOW = 5


APPDATA = os.path.expanduser(r'~\AppData\Local\Minesweeper')
DEBUG = APPDATA + r'\debug'
# Creates AppData folder if doesn't exist
if not os.path.exists(DEBUG):
    os.makedirs(DEBUG)

STRFTIME = r'%A %B %d, %I:%M %p %Y %Z'
HIGHSCORE_TXT = os.path.join(APPDATA, 'highscore.txt')
LOGO = "data\\images\\logo.ico"
MAX_ROWS_AND_COLS = 75
MIN_ROWS_AND_COLS = 4
DARK_MODE_BG = '#282828'
DARK_MODE_FG = '#FFFFFF'
DEFAULT_BG = '#f0f0f0f0f0f0'
DEFAULT_FG = '#000000'
CURRENT_BG = DEFAULT_BG
CURRENT_FG = DEFAULT_FG


debug_log_file = os.path.join(DEBUG, f"{datetime.now().strftime(STRFTIME.replace(':', '-'))}.log")

with open(debug_log_file, 'w') as _:
    pass

console_open = False
allocated_console = None
if allocated_console is None:
    # one-time set up for all instances
    allocated = bool(kernel32.AllocConsole())
    allocated_console = allocated
    if allocated:
        hwnd = kernel32.GetConsoleWindow()
        user32.ShowWindow(hwnd, SW_HIDE)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s]: %(message)s",
    handlers=[
        logging.FileHandler(debug_log_file),
        logging.StreamHandler(open('CONOUT$', 'w', buffering=1)),
    ]
)

logging.info('Loading app...')

def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logging.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))

sys.excepthook = handle_exception


def show_console():
    global console_open
    hwnd = kernel32.GetConsoleWindow()
    user32.ShowWindow(hwnd, SW_SHOW)
    console_open = True


def hide_console():
    global console_open
    hwnd = kernel32.GetConsoleWindow()
    user32.ShowWindow(hwnd, SW_HIDE)
    console_open = False


def console():
    if console_open:
        hide_console()
    else:
        show_console()


def format_second(seconds: int | float):
    if seconds != float('inf'):
        seconds = int(seconds)
        minutes = int(seconds / 60)
        sec = seconds % 60
        if sec < 10:
            sec = f'0{sec % 60}'

        return f'{minutes}:{sec}'
    else:
        return 'None'


def dark_title_bar(window):
    """
    MORE INFO:
    https://docs.microsoft.com/en-us/windows/win32/api/dwmapi/ne-dwmapi-dwmwindowattribute
    """
    # https://stackoverflow.com/a/70724666
    window.update()
    DWMWA_USE_IMMERSIVE_DARK_MODE = 20
    set_window_attribute = ctypes.windll.dwmapi.DwmSetWindowAttribute
    get_parent = ctypes.windll.user32.GetParent
    hwnd = get_parent(window.winfo_id())
    rendering_policy = DWMWA_USE_IMMERSIVE_DARK_MODE
    value = 2
    value = ctypes.c_int(value)
    set_window_attribute(hwnd, rendering_policy, ctypes.byref(value),
                         ctypes.sizeof(value))


def more_info(
    num_mines,
    mines_found,
    squares_clicked_on,
    squares_not_clicked_on,
    start,
    session_start,
    total_squares
):
    messagebox.showinfo('Additional Information', f'''
Total Mines: {num_mines}
Mines found: {mines_found}
Squares clicked on: {len(squares_clicked_on)}
Squares not clicked on: {len(squares_not_clicked_on)}
Total squares: {total_squares}
Ratio of mines: {round((num_mines/total_squares) * 100, 2)}%
Started Game: {start.strftime(STRFTIME)}
Session Started: {session_start.strftime(STRFTIME)}
''')


def save_game(
    start,
    total_time,
    grid,
    zeros_checked,
    num_mines,
    chording,
):
    global difficulty
    logging.info(f'''Saving game with the following attributes:

start:               {start}
total_time:          {total_time}
grid:                {grid}
zeros_checked:       {zeros_checked}
num_mines:           {num_mines}
chording:            {chording}
grid.grid_size       {grid.grid_size}
''')
    data = {
        'start': start,
        'time played': total_time,
        'grid': PickleButtonGrid.from_grid(grid),
        'zeros checked': zeros_checked,
        'num mines': num_mines,
        'chording': chording,
        'difficulty': difficulty.get()
    }
    logging.info(f'Data to save: {data}')
    with filedialog.asksaveasfile('wb', filetypes=(('Minesweeper Game Files', '*.min'), ('Any File', '*.*'))) as f:  # Pickling
        messagebox.showinfo('Save Game', 'You game is being saved right now, this may a few moments. Please wait until another popup comes before closing the game.')
        logging.info('Saving data...')
        pickle.dump(data, f)
        logging.info('Data successfully saved')
        messagebox.showinfo('Save Game', 'Your game has been saved, you can now close the game.')


def load_game(_=None):
    logging.info('Opening game...')
    file = filedialog.askopenfile('rb', filetypes=(('Minesweeper Game Files', '*.min'), ('Any File', '*.*')))
    logging.info(f'Reading {file}...')
    with file as f:  # Un Pickling
        data = pickle.load(f)
        data: dict[str]
    logging.info(f'{file} successfully read, setting up game...')

    game_window = Toplevel(window)
    game_window.iconbitmap(LOGO)
    game_window.title('Minesweeper')
    if dark_mode_state.get():
        dark_title_bar(game_window)

    grid = data['grid'].grid
    button_grid = ButtonGrid(data['grid'].grid_size, game_window, grid, dark_mode_state.get())

    start: datetime = data['start']
    time = data['time played']
    num_mines: int = data['num mines']
    zeros_checked = data['zeros checked']
    chording = data['chording']
    game_window.grid_columnconfigure(1, weight=1)

    mines_found = 0
    for row in button_grid.grid:
        for square in row:
            if square.category == 'mine' and square.cget('text') == '🚩':
                mines_found += 1

    create_game(
        game_window,
        start,
        button_grid,
        zeros_checked,
        num_mines,
        chording,
        mines_found,
        additional_time=time,
    )


def game(_=None):
    global difficulty
    global window
    global chord_state
    logging.info('Creating a game...')

    chording = chord_state.get()

    game_window = Toplevel(window)
    game_window.iconbitmap(LOGO)
    game_window.title('Minesweeper')
    start = datetime.now()
    game_window.grid_columnconfigure(1, weight=1)

    if dark_mode_state.get():
        dark_title_bar(game_window)
    if difficulty.get() == (None, None) or difficulty.get() == ('None', 'None'):
        logging.error('Game size not chosen')
        messagebox.showerror(title='Game Size not chosen', message='You have not chosen a game size!')
        game_window.destroy()
        return None
    elif difficulty.get() >= (60, 60):
        logging.warning(f'Size too big {difficulty.get()}')
        messagebox.showwarning(title='Size too big', message='Warning: When the game is a size of 60x60 or above, the expierence might be so laggy it is unplayable.')
    elif mines.get() > (difficulty.get()[0] * difficulty.get()[1]) - 10:
        logging.error(f'Mines too high, game size {difficulty.get()}, mines: {mines.get()}')
        messagebox.showerror(title='Mines too high', message='You have chosen too many mines.')
        game_window.destroy()
        return None
    elif mines.get() > ((difficulty.get()[0] * difficulty.get()[1])/2):
        logging.warning(f'Number of mines high, game size {difficulty.get()}, mines: {mines.get()}')
        messagebox.showwarning(title='Number of mines high', message='You have chosen a high amount of mines, so it might take a long time to place them all')

    logging.info('Creating grid of buttons...')
    grid = ButtonGrid(difficulty.get(), game_window, dark_mode=dark_mode_state.get(), num_mines=mines.get())
    zeros_checked = []
    num_mines = 0

    for row in grid.grid:
        for square in row:
            if square.category == 'mine':
                num_mines += 1
    mines_found = 0
    create_game(
        game_window,
        start,
        grid,
        zeros_checked,
        num_mines,
        chording,
        mines_found,
    )


def create_game(
    game_window: Toplevel,
    start: datetime,
    grid: ButtonGrid,
    zeros_checked: list[Square],
    num_mines: int,
    chording: bool,
    mines_found: int,
    additional_time: float = 0.0
):
    logging.info(f'''Creating game with following attributes:

game_window:           {game_window}
start:                 {start}
grid:                  {grid}
zeros_checked:         {zeros_checked}
num_mines:             {num_mines}
chording:              {chording}
mines_found:           {mines_found}
additional_time:       {additional_time}
''')
    session_start: datetime = datetime.now()
    squares_clicked_on = [
        square
        for row in grid.grid
        for square in row
        if square.clicked_on
    ]

    squares_not_clicked_on = [
        square
        for row in grid.grid
        for square in row
        if square.clicked_on == False
    ]
    total_time = StringVar(game_window)

    Label(game_window, textvariable=total_time, bg=CURRENT_BG, fg=CURRENT_FG).grid(
        row=1, column=1, sticky=N+S+E+W, pady=(5, 0))
    game_window.config(bg=CURRENT_BG)

    if additional_time != 0.0:
        total_time.set(f'Time: {format_second(int(additional_time))} 🚩0/{num_mines}💣')

    highscore_data = load_highscore()
    game_size_str = f'{difficulty.get()[0]}x{difficulty.get()[1]}'
    game_window.title(f'{game_size_str} Minesweeper Game')
    logging.info(f'{game_size_str} Minesweeper Game starting...')
    if not isinstance(highscore_data, float):
        try:
            highscore = highscore_data[game_size_str]
        except KeyError:
            highscore = float('inf')
    else:
        highscore = float('inf')
    seconds = additional_time

    # create a menubar
    menubar = CustomMenuBar(game_window, bg=CURRENT_BG, fg=CURRENT_FG)
    menubar.place(x=0, y=0)

    # create the file_menu
    file_menu = Menu(
        menubar,
        tearoff=0
    )
    game_window.bind('<Control-s>', lambda _: save_game(start, seconds, grid, zeros_checked, num_mines, chording))
    game_window.bind('<Alt-q>', lambda _: game_window.destroy())
    game_window.bind('<Alt-i>', lambda _: more_info(
        num_mines, mines_found, squares_clicked_on, squares_not_clicked_on, start, session_start,  grid.grid_size[0] * grid.grid_size[1]))

    file_menu.add_command(label='Save As', accelerator='Ctrl+S', command=partial(save_game, start, seconds, grid, [
                          PickleSquare.from_square(square) for square in zeros_checked], num_mines, chording))
    file_menu.add_command(label='More Info', command=lambda: more_info(
        num_mines, mines_found, squares_clicked_on, squares_not_clicked_on, start, session_start, grid.grid_size[0] * grid.grid_size[1]),
        accelerator='Alt+I')
    file_menu.add_command(label='Exit', command=game_window.destroy, accelerator='Alt+Q')

    menubar.add_menu(menu=file_menu, title='File')
    previous_sec = datetime.now()
    previous_sec = previous_sec.replace(microsecond=0)
    squares_flaged = []
    squares_checked = []

    logging.info('Entering while loop...')
    while True:
        global after_cancel
        after_cancel.append(window.after(100, do_nothing))

        now = datetime.now()
        now = now.replace(microsecond=0)
        if now > previous_sec:
            previous_sec = now
            seconds = (now - session_start).total_seconds() + additional_time

        percent = round(((len(squares_flaged))/num_mines) * 100, 2)
        total_time.set(f'Time: {format_second(seconds)}  🚩 {len(squares_flaged)}/{num_mines} 💣 ({percent}%)')

        for row in grid.iter_rows():
            # Clicks Zeros
            for square in (square for square in row if (square.num == None) and (square.clicked_on) and (square not in zeros_checked) and (square.category != 'mine')):
                zeros_checked.append(square)
                for square2 in (square2 for square2 in grid.around_square(*square.position) if (square2.category != 'mine') and square2 not in squares_checked):
                    square2.clicked()

            # Counts mines found
            for square in (square for square in squares_flaged if square.category == 'mine'):
                mines_found += 1

            if chording:
                # Checks all square if they are completed
                for square in (square for square in row if square.completed == False):
                    mines_around_square = [square for square in grid.around_square(
                        *square.position) if (square.category == 'mine') and (square.clicked_on == True)]
                    if (len(mines_around_square) == square.num and all(mine.category == 'mine' for mine in mines_around_square)) or square.num == None:
                        square.completed = True

                # Shows all squares around a square if it was middle clicked
                for square in (square for square in row if (square.chord)):
                    if square.completed == False:
                        precolors = []
                        squares = [
                            square
                            for square in grid.around_square(*square.position)
                            if square.clicked_on == False
                        ]
                        for square2 in squares:
                            precolors.append(square2.cget('bg'))
                            square2.config(bg='brown')
                        game_window.update()
                        game_window.after(1000)
                        for square2 in squares:
                            precolor = precolors[squares.index(square2)]
                            square2.config(bg=precolor)
                    else:
                        for square2 in (square for square in grid.around_square(*square.position) if not square.clicked_on and square.category != 'mine'):
                            square2.clicked()
                        square.chord = False
        mines_found = 0

        squares_clicked_on = [
            square
            for row in grid.grid
            for square in row
            if square.clicked_on
        ]

        squares_not_clicked_on = [
            square
            for row in grid.grid
            for square in row
            if square.clicked_on == False
        ]

        squares_flaged = [
            square
            for row in grid.grid
            for square in row
            if square.flaged
        ]

        game_overs = [
            square.game_over
            for row in grid.grid
            for square in row
        ]

        if (len(squares_clicked_on) == (grid.grid_size[0] * grid.grid_size[1]) and all(square.category == 'mine' for square in squares_flaged)) or \
                (all(square.category == 'mine' for square in squares_not_clicked_on) and len(squares_not_clicked_on) == num_mines):
            game_over = True
            win = True
            if (len(squares_clicked_on) == (grid.grid_size[0] * grid.grid_size[1]) and all(square.category == 'mine' for square in squares_flaged)):
                logging.info('Game has been won because all squares are clicked and all mines flagged')
            else:
                logging.info('Game has been won because the squares left are mines')
        elif any(game_overs):
            logging.info('The game is over, and it is lost.')
            game_over = True
            win = False
        else:
            game_over = False

        if game_over:
            for row in grid.grid:
                for square in row:
                    if square.category == 'mine' and square.cget('text') != '🚩':
                        square.clicked()
                    elif square.category == 'mine' and square.cget('text') == '🚩':
                        mines_found += 1
                        square.config(text='✅')
                    elif square.num != None and square.cget('text') == '🚩':
                        square.config(text='❌')
            game_window.update()
            break
        game_window.update()

    if win:
        messagebox.showinfo(
            'Game Over', f'Game Over.\nYou won!\nYou found {mines_found} out of {num_mines} mines.\nTime: {format_second(seconds)}\nHighscore: {format_second(highscore)}')
    else:
        messagebox.showinfo(
            'Game Over', f'Game Over.\nYou lost.\nYou found {mines_found} out of {num_mines} mines.\nTime: {format_second(seconds)}\nHighscore: {format_second(highscore)}')
    if win and seconds < highscore:
        logging.info('Highscore has been beaten, writing new highscore data')
        with open(HIGHSCORE_TXT, 'wb') as f:
            if isinstance(highscore_data, dict):
                new_highscore_data = highscore_data.copy()
            else:
                new_highscore_data = {}
            new_highscore_data[game_size_str] = seconds
            pickle.dump(new_highscore_data, f)
    logging.info('Destroying window')
    game_window.destroy()


def change_difficulty(from_spinbox:bool = False):
    global game_size
    global difficulty
    if not from_spinbox:
        logging.info(f'Setting game size to: {tuple(int(i) for i in difficulty.get().split(" "))}')
        difficulty.set(tuple(int(i) for i in difficulty.get().split(' ')))
    else:
        logging.info(f'Setting custom game size: {(rows.get(), cols.get())}')
        difficulty.set((rows.get(), cols.get()))
    game_size.set(f'Your game size will be {difficulty.get()[0]} rows and {difficulty.get()[1]} columns')


def load_highscore() -> dict[str, float | int] | float:
    logging.info('Loading highscore...')
    if not os.path.exists(HIGHSCORE_TXT):
        logging.info(f'{HIGHSCORE_TXT} does not exist, looking in root directory')
        if not os.path.exists(os.path.join(os.getcwd(), 'highscore.txt')):
            logging.info('No highscore was found')
            return float('inf')
        else:
            with open(os.path.join(os.getcwd(), 'highscore.txt'), 'rb') as f:
                value = pickle.load(f)
            messagebox.showerror('Highscore file in wrong place', 'The highscore file was found, but in the wrong spot, as soon as you click OK, Minesweeper will attempt to move the file to a new location, you might have to delete the file yourself.')
            with open(HIGHSCORE_TXT, 'wb') as f:
                pickle.dump(value, f)
            os.remove(os.path.join(os.getcwd(), 'highscore.txt'))
            return value
    else:
        logging.info(f'{HIGHSCORE_TXT} does exist, reading data from it')
        with open(HIGHSCORE_TXT, 'rb') as f:
            value = pickle.load(f)
        if isinstance(value, dict):
            logging.info(f'{HIGHSCORE_TXT} successfully read')
            return value
        else:
            logging.info(f'{HIGHSCORE_TXT} contains invalid data {value}')
            messagebox.showerror('Highscore value invalide', 'The highscore file contains an invalid value, press OK to delete the content of it')
            logging.info('Removing file...')
            os.remove(HIGHSCORE_TXT)
            return float('inf')


def change_theme(*_):
    global CURRENT_BG, CURRENT_FG
    if dark_mode_state.get():
        logging.info('User switched theme to dark mode')
        CURRENT_BG = DARK_MODE_BG
        CURRENT_FG = DARK_MODE_FG
        dark_title_bar(window)
    else:
        logging.info('User switched theme to light mode')
        CURRENT_BG = DEFAULT_BG
        CURRENT_FG = DEFAULT_FG
        window.resizable(False, False)

    window.config(bg=CURRENT_BG)
    for child in window.winfo_children():
        if not isinstance(child, Toplevel) and not isinstance(child, Spinbox) and not isinstance(child, CustomMenuBar):
            child.config(bg=CURRENT_BG, fg=CURRENT_FG)
        elif isinstance(child, CustomMenuBar):
            child.change_bg_fg(bg=CURRENT_BG, fg=CURRENT_FG)
        elif isinstance(child, Spinbox):
            if CURRENT_BG == DEFAULT_BG:
                child.config(bg='white', fg=CURRENT_FG)
            else:
                child.config(bg=CURRENT_BG, fg=CURRENT_FG)
        elif isinstance(child, Toplevel):
            if CURRENT_BG == DARK_MODE_BG:
                dark_title_bar(child)
            else:
                child.resizable(True, True)
            child.config(bg=CURRENT_BG)
            for child2 in child.winfo_children():
                if not isinstance(child2, Frame) and not isinstance(child2, CustomMenuBar):
                    child2.config(bg=CURRENT_BG, fg=CURRENT_FG)
                elif isinstance(child2, CustomMenuBar):
                    child2.change_bg_fg(bg=CURRENT_BG, fg=CURRENT_FG)
                elif isinstance(child2, Frame):
                    for square in child2.winfo_children():
                        if isinstance(square, Square):
                            square.switch_theme()
                        elif isinstance(square, Label):
                            square.config(bg=CURRENT_BG, fg=CURRENT_FG)


def show_highscores(_=None):
    logging.info('User requested highscores')
    highscore_data = load_highscore()

    if isinstance(highscore_data, dict):
        logging.info(f'Highscore data detected: {highscore_data}')
        data = [['Game Size', 'Seconds']]
        for key, value in highscore_data.items():
            data.append([key, str(round(value, 1))])

        new_window = Toplevel(window)
        new_window.title('Highscores')
        new_window.iconbitmap(LOGO)
        new_window.config(padx=50, pady=20)
        frame = Frame(new_window, bg='black')
        new_window.grid_columnconfigure(0, weight=1)
        new_window.grid_rowconfigure(0, weight=1)
        frame.grid(row=0, column=0)

        if dark_mode_state.get():
            new_window.config(bg=DARK_MODE_BG)
            dark_title_bar(new_window)
            bg_of_labels = DARK_MODE_BG
            fg_of_labels = DARK_MODE_FG
        else:
            bg_of_labels = DEFAULT_BG
            fg_of_labels = DEFAULT_FG

        for y, row in enumerate(data):
            Grid.rowconfigure(frame, y, weight=1)
            for x, item in enumerate(row):
                Grid.columnconfigure(frame, x, weight=1)
                Label(frame, text=str(item), bg=bg_of_labels, fg=fg_of_labels).grid(row=y, column=x, padx=1, pady=1, sticky='nsew')
        new_window.update()
    else:
        logging.info('No highscores found')
        messagebox.showinfo('Highscores', 'No highscores were found, play a game and win it to get some')


def do_nothing():
    pass


def quit_game():
    global window
    window.destroy()
    for code in after_cancel:
        window.after_cancel(code)
    window.setvar('button pressed', 39393)
    logging.info('Closing app...')
    del window
    sys.exit()


def change_mines():
    mines_counter.set(f'Your game will have {mines.get()} mines')
    logging.info(f'Setting custom mine count: {mines.get()}')


logging.info('Functions successfully defined, creating GUI')

window = Tk()
window.title('Game Loader')
window.iconbitmap(LOGO)
window.resizable(False, False)

after_cancel = []

Label(text='Select Difficulty').pack(pady=(25, 0))

# Variable to hold on to which radio button value is checked.
difficulty = Variable(window, (None, None))

Radiobutton(
    text="Easy", value=(10, 10), variable=difficulty, command=change_difficulty
).pack()

Radiobutton(
    text="Medium", value=(20, 20), variable=difficulty, command=change_difficulty
).pack()

Radiobutton(
    text='Hard', value=(30, 30), variable=difficulty, command=change_difficulty
).pack()

game_size = StringVar(window, f'You game size will be {difficulty.get()[0]} rows and {difficulty.get()[1]} columns')

Label(window, textvariable=game_size).pack()

cols = IntVar(window)
rows = IntVar(window)

Spinbox(window, from_=MIN_ROWS_AND_COLS, to=MAX_ROWS_AND_COLS, textvariable=rows, width=4, command=partial(change_difficulty, True)).pack()
Spinbox(window, from_=MIN_ROWS_AND_COLS, to=MAX_ROWS_AND_COLS, textvariable=cols, width=4, command=partial(change_difficulty, True)).pack()

mines = IntVar(window, -1)

mines_counter = StringVar(window, f'Your game will have {mines.get()} mines')

Label(window, textvariable=mines_counter).pack()
Label(window, text='-1 means it will generate a random number/use default').pack(padx=20)

Spinbox(window, textvariable=mines, width=4, from_= -1, to = 2000, command=change_mines).pack()

chord_state = BooleanVar(window)
dark_mode_state = BooleanVar(window)
dark_mode_state.trace('w', change_theme)  

Button(window, text='Play!', command=game).pack(pady=(0, 20))

# create a menubar
menubar = CustomMenuBar(window)
menubar.place(x=0, y=0)

# create the file_menu
file_menu = Menu(
    menubar,
    tearoff=0
)
file_menu.add_command(label='Open File', command=load_game, accelerator='Ctrl+O')
file_menu.add_command(label='Highscores', command=show_highscores, accelerator='Ctrl+H')
file_menu.add_separator()
file_menu.add_command(label='Exit', command=quit_game, accelerator='Ctrl+Q')

settings = Menu(menubar, tearoff=0)
settings.add_checkbutton(variable=chord_state, label='Enable Chording', accelerator='Ctrl+A')
settings.add_checkbutton(variable=dark_mode_state, label='Dark Mode', accelerator='Ctrl+D')
settings.add_separator()
settings.add_command(label='Check for Updates', command=partial(check_for_updates, __version__, window), accelerator='Ctrl+U')
settings.add_command(label='Version Info', command=partial(messagebox.showinfo, title='Version Info', message=f'Minesweeper Version: {__version__}'), accelerator='Ctrl+I')

advanced = Menu(settings, tearoff=0)
advanced.add_command(label='Console', command=console)
settings.add_cascade(label='Advanced', menu=advanced)

# Keyboard Shortcuts
window.bind_all('<Control-i>', lambda _: messagebox.showinfo(title='Version Info', message=f'Minesweeper Version: {__version__}'))
window.bind_all('<Control-u>', lambda _: check_for_updates(__version__, window))
window.bind_all('<Control-q>', lambda _: quit_game)
window.bind_all('<Control-o>', load_game)
window.bind_all('<space>', game)
window.bind_all('<Control-a>', lambda _: chord_state.set(not chord_state.get()))
window.bind_all('<Control-d>', lambda _: dark_mode_state.set(not dark_mode_state.get()))
window.bind_all('<Control-h>', show_highscores)

menubar.add_menu(menu=file_menu, title='File')
menubar.add_menu(menu=settings, title='Settings')
window.protocol('WM_DELETE_WINDOW', quit_game)

logging.info('GUI successfully created')
window.mainloop()
