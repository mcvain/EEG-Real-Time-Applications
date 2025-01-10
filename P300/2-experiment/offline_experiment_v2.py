import glob
import os
from collections import deque
from tkinter import Tk, Toplevel, IntVar, W, EW, Text, StringVar, Radiobutton, filedialog
from tkinter.ttk import Label, Button, Entry, Frame
import tkinter.font as tkFont
import os
dirname = os.path.dirname(__file__)
import numpy as np
from PIL import ImageTk, Image
from pylsl import StreamInfo, StreamOutlet, local_clock, IRREGULAR_RATE
import random
import string
import time
from wonderwords import RandomWord

r = RandomWord()

class P300Window(object):
    def __init__(self, master: Tk):
        self.master = master
        master.title('P300 speller')

        # Parameters
        self.imagesize = 125
        self.images_folder_path = os.path.join(dirname, '../utils/images')
        self.flash_image_path = os.path.join(dirname, '../utils/images/flash_images/einstein_1.jpg')
        self.number_of_rows = 6
        self.number_of_columns = 6
        self.lsl_streamname = 'P300_stream'
        self.flash_duration = 60  # 60ms flash duration
        self.rounds_per_character = 10
        self.total_characters = self.number_of_rows * self.number_of_columns
        self.delay = 2500  # interval between trials

        self.word = r.word(word_min_length=8, word_max_length=8).lower()
        self.letter_idx = 0

        # Variables
        self.usable_images = []
        self.image_labels = []
        self.flash_sequence = []
        self.flash_image = None
        self.sequence_number = 0
        self.lsl_output = None
        self.running = 0

        # UI Setup
        self.setup_ui()

        # Initialization
        self.show_images()
        self.create_flash_sequence()
        self.lsl_output = self.create_lsl_output()

    def setup_ui(self):
        # Configure weights for the main window
        self.master.grid_rowconfigure(0, weight=1)
        self.master.grid_rowconfigure(self.number_of_rows + 1, weight=1)
        self.master.grid_columnconfigure(0, weight=1)
        self.master.grid_columnconfigure(self.number_of_columns - 1, weight=1)

        # Create a main frame to hold all elements
        self.main_frame = Frame(self.master)
        self.main_frame.grid(row=1, column=1, sticky='nsew')

        # Configure the main frame's grid weights
        for i in range(self.number_of_rows + 3):
            self.main_frame.grid_rowconfigure(i, weight=1)
        for i in range(self.number_of_columns):
            self.main_frame.grid_columnconfigure(i, weight=1)

        # Image frame
        self.image_frame = Frame(self.main_frame)
        self.image_frame.grid(row=0, column=0, rowspan=self.number_of_rows,
                              columnspan=self.number_of_columns, sticky='nsew')

        # Buttons frame
        self.button_frame = Frame(self.main_frame)
        self.button_frame.grid(row=self.number_of_rows + 2, column=0,
                               columnspan=self.number_of_columns, sticky='nsew')

        # Configure button frame weights
        self.button_frame.grid_columnconfigure(0, weight=1)
        self.button_frame.grid_columnconfigure(2, weight=1)
        self.button_frame.grid_columnconfigure(4, weight=1)
        self.button_frame.grid_columnconfigure(6, weight=1)

        # Create buttons in the button frame
        self.start_btn_text = StringVar()
        self.start_btn_text.set('Start')
        self.start_btn = Button(self.button_frame, textvariable=self.start_btn_text, command=self.start)
        self.start_btn.grid(row=0, column=5)

        self.pause_btn = Button(self.button_frame, text='Pause', command=self.pause)
        self.pause_btn.grid(row=0, column=3)
        self.pause_btn.configure(state='disabled')

        self.close_btn = Button(self.button_frame, text='Close', command=self.master.quit)
        self.close_btn.grid(row=0, column=1)

        self.show_target_word(0)

    def open_images(self):
        self.usable_images = []
        self.highlight_letter_images = []

        letter_images = sorted(glob.glob(os.path.join(self.images_folder_path, 'letter_images/*.png')))

        #currently, still did not flash number yet!
        number_images = sorted(glob.glob(os.path.join(self.images_folder_path, 'number_images/*.png')))

        letter_highlight_images = sorted(glob.glob(os.path.join(self.images_folder_path, 'letter_highlight_images/*.png')))
        number_highlight_images = sorted(glob.glob(os.path.join(self.images_folder_path, 'number_highlight_images/*.png')))

        for number_image in number_images:
            letter_images.append(number_image)
        #print("Paths: ", letter_images)
        min_number_of_images = self.number_of_columns * self.number_of_rows
        if len(letter_images) < min_number_of_images:
            print('To few images in folder: ' + self.images_folder_path)
            return

        # Convert and resize images
        for image_path in letter_images:
            image = Image.open(image_path)
            resized = image.resize((self.imagesize, self.imagesize), Image.BICUBIC)
            Tkimage = ImageTk.PhotoImage(resized)
            self.usable_images.append(Tkimage)

        # Convert and resize images
        for image_path in letter_highlight_images:
            image = Image.open(image_path)
            resized = image.resize((self.imagesize, self.imagesize), Image.BICUBIC)
            Tkimage = ImageTk.PhotoImage(resized)
            self.highlight_letter_images.append(Tkimage)

        flash_img = Image.open(self.flash_image_path)
        flash_img_res = flash_img.resize((self.imagesize, self.imagesize), Image.BICUBIC)
        self.flash_image = ImageTk.PhotoImage(flash_img_res)

    def show_images(self):
        self.open_images()
        if not self.usable_images:
            print('No images opened')
            return

        num_rows = self.number_of_rows
        num_cols = self.number_of_columns

        for r in range(num_rows):
            for c in range(num_cols):
                current_image = self.usable_images[r * num_cols + c]
                label = Label(self.image_frame, image=current_image)
                label.image = current_image
                label.grid(row=r, column=c)
                self.image_labels.append(label)

    def create_lsl_output(self):
        info = StreamInfo(name=self.lsl_streamname, type='Markers',
                          channel_count=5, channel_format='string',
                          nominal_srate=IRREGULAR_RATE,
                          source_id='marker_stream')
        info.desc().append_child_value('flash_mode', 'Single Value')
        info.desc().append_child_value('num_rows', str(self.number_of_rows))
        info.desc().append_child_value('num_cols', str(self.number_of_columns))
        return StreamOutlet(info)

    def create_flash_sequence(self):
        self.flash_sequence = []
        for _ in range(len(self.word)):
            character_sequence = []
            for _ in range(self.rounds_per_character):
                round_sequence = list(range(self.total_characters))
                random.shuffle(round_sequence)
                if character_sequence and round_sequence[0] == character_sequence[-1]:
                    round_sequence[0], round_sequence[-1] = round_sequence[-1], round_sequence[0]
                character_sequence.extend(round_sequence)
            self.flash_sequence.extend(character_sequence)

    def start(self):
        self.running = 1
        self.start_btn.configure(state='disabled')
        self.pause_btn.configure(state='normal')
        self.letter_idx = 0
        # self.show_highlight_letter(self.letter_idx)
        self.master.after(1000, self.start_flashing)

    def pause(self):
        self.running = 0
        self.start_btn_text.set('Resume')
        self.start_btn.configure(state='normal')
        self.pause_btn.configure(state='disabled')

    def start_flashing(self):
        if self.letter_idx >= len(self.word):
            print('Experiment complete')
            self.running = 0
            self.start_btn.configure(state='normal')
            return

        if not self.running:
            return
        
        self.show_highlight_letter(string.ascii_lowercase.index(self.word[self.letter_idx]))

        current_sequence = self.flash_sequence[self.letter_idx * self.total_characters * self.rounds_per_character:
                                               (self.letter_idx + 1) * self.total_characters * self.rounds_per_character]
        # self.flash_character_sequence(current_sequence, 0)

    def flash_character_sequence(self, sequence, index):
        if index >= len(sequence):
            self.letter_idx += 1
            self.show_target_word(self.letter_idx)
            self.master.after(self.delay, self.start_flashing)
            return

        if not self.running:
            return

        element_to_flash = sequence[index]
        self.flash_single_element(element_to_flash)

        timestamp = local_clock()
        target_letter = self.word[self.letter_idx]
        target_index = string.ascii_lowercase.index(target_letter)

        if element_to_flash == target_index:
            print(target_letter, self.letter_idx, target_index, element_to_flash, timestamp)
            self.lsl_output.push_sample(['target', target_letter, str(self.letter_idx), str(target_index), str(element_to_flash)], timestamp)
        else:
            self.lsl_output.push_sample(['non-target', target_letter, str(self.letter_idx), str(target_index), str(element_to_flash)], timestamp)

        self.master.after(self.flash_duration, self.unflash_single_element, element_to_flash)
        self.master.after(self.flash_duration, lambda: self.flash_character_sequence(sequence, index + 1))

    def flash_single_element(self, element_no):
        self.change_image(self.image_labels[element_no], self.flash_image)

    def unflash_single_element(self, element_no):
        self.change_image(self.image_labels[element_no], self.usable_images[element_no])

    def change_image(self, label, img):
        label.configure(image=img)
        label.image = img

    def show_target_word(self, pos):
        fontStyle = tkFont.Font(family="Courier", size=40)
        fontStyleBold = tkFont.Font(family="Courier bold", size=40)
        text = Text(self.master, height=1, font=fontStyle)
        text.tag_configure("bold", font=fontStyleBold)
        text.tag_configure("center", justify='center')
        for i in range(len(self.word)):
            if i != pos:
                text.insert("end", self.word[i].upper())
            else:
                text.insert("end", self.word[i].upper(), "bold")
        text.configure(state="disabled", width=10)
        text.tag_add("center", "1.0", "end")
        text.grid(row=self.number_of_rows + 1, column=self.number_of_columns - 4)

    # def show_highlight_letter(self, pos):
    #     print(pos)
    #     self.flash_single_element(pos)
    #     self.master.after(self.delay, self.unflash_single_element, pos)

    def show_highlight_letter(self, element_no):
        self.change_image(self.image_labels[element_no], self.highlight_letter_images[element_no])
        self.master.after(self.delay, self.unhighlight_image, element_no)

    def unhighlight_image(self, element_no):
        self.change_image(self.image_labels[element_no], self.usable_images[element_no])
        current_sequence = self.flash_sequence[self.letter_idx * self.total_characters * self.rounds_per_character:
                                               (self.letter_idx + 1) * self.total_characters * self.rounds_per_character]
        
        self.master.after(self.flash_duration, self.flash_character_sequence, current_sequence, 0)

root = Tk()
main_window = P300Window(root)
root.mainloop()
