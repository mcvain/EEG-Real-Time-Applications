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

MAX_FLASHES = 10000  # Maximum number of flashed images. Window will stop afterwards


class P300Window(object):

    def __init__(self, master: Tk):
        self.master = master
        master.title('P300 speller')

        #Parameters
        self.imagesize = 125
        self.images_folder_path = os.path.join(dirname, '../utils/images')  #use utils/char_generator to generate any image you want
        self.flash_image_path = os.path.join(dirname, '../utils/images/flash_images/einstein_1.jpg')
        self.number_of_rows = 6
        self.number_of_columns = 6  #make sure you have 6 x 6 amount of images in the images_folder_path
        self.lsl_streamname = 'P300_stream'
        self.flash_mode = 2  #single element  #1 for columns and rows; currently is NOT working yet; if I have time, will revisit
        self.flash_duration = 100  #soa
        self.break_duration = 250  #iti
        self.set_of_repetition = 12
        self.number_of_flashes_per_repetition = 10
        self.total_repetitions_per_trial = self.set_of_repetition * self.number_of_flashes_per_repetition  #30 repetitions per letters


        self.trials = 6 #number of letters
        self.delay = 2500 #interval between trial
        self.letter_idx = 0

        #did not include numbers yet!
        self.random_letter = random.choices(string.ascii_lowercase, k=self.trials)   #randomize [self.trials] number letters
        self.word = ''.join(self.random_letter)

        # Variables
        self.usable_images = []
        self.image_labels = []
        self.flash_sequence = []
        self.flash_image = None
        self.sequence_number = 0
        self.lsl_output = None
        
        self.running = 0  #for pause

        self.image_frame = Frame(self.master)
        self.image_frame.grid(row=0, column=0, rowspan=self.number_of_rows,
                              columnspan=self.number_of_columns)

        self.start_btn_text = StringVar()
        self.start_btn_text.set('Start')
        self.start_btn = Button(self.master, textvariable=self.start_btn_text, command=self.start)
        self.start_btn.grid(row=self.number_of_rows + 2, column=self.number_of_columns - 1)

        self.pause_btn = Button(self.master, text='Pause', command=self.pause)
        self.pause_btn.grid(row=self.number_of_rows + 2, column=self.number_of_columns - 4)  #-4 for center
        self.pause_btn.configure(state='disabled')

        self.close_btn = Button(self.master, text='Close', command=master.quit)
        self.close_btn.grid(row=self.number_of_rows + 2, column=0)

        self.show_highlight_letter(0)

        # Initialization
        self.show_images()
        self.create_flash_sequence()
        self.lsl_output = self.create_lsl_output()

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

        if self.usable_images == []:
            print('No images opened')
            return

        num_rows = self.number_of_rows
        num_cols = self.number_of_columns

        # Arrange images
        for r in range(0, num_rows):
            for c in range(0, num_cols):
                current_image = self.usable_images[r * num_cols + c]
                label = Label(self.image_frame, image=current_image)
                label.image = current_image
                label.grid(row=r, column=c)
                self.image_labels.append(label)

    def create_lsl_output(self):
        """Creates an LSL Stream outlet for markers"""
        info = StreamInfo(name=self.lsl_streamname, type='Markers',
                          channel_count=5, channel_format='string', nominal_srate=IRREGULAR_RATE,
                          source_id='marker_stream', handle=None)

        if self.flash_mode == 1:
            info.desc().append_child_value('flash_mode', 'Row and Column')
        elif self.flash_mode == 2:
            info.desc().append_child_value('flash_mode', 'Single Value')

        info.desc().append_child_value('num_rows', str(self.number_of_rows))
        info.desc().append_child_value('num_cols', str(self.number_of_columns))

        return StreamOutlet(info)

    def create_flash_sequence(self):
        self.flash_sequence = []
        num_rows = self.number_of_rows
        num_cols = self.number_of_columns

        if self.flash_mode == 1:
            print('CAUTION: Row and Column flash mode currently uses only random samples!')
            self.flash_sequence = np.random.randint(0, num_rows + num_cols, 3000) #3000 should be enough
        elif self.flash_mode == 2:
            maximum_number = num_rows * num_cols
            for i in range(len(self.word)):
                for j in range(self.set_of_repetition):  #generate three sets
                    seq = list(range(maximum_number))  #generate 0 to maximum_number
                    random.shuffle(seq)  #shuffle
      
                    index = string.ascii_lowercase.index(self.word[i])
                    allowed_values = list(range(0, maximum_number))
                    allowed_values.remove(index)  #reduce number of flashed by first excluding the actual letter
                    #print("Index: ", index)

                    while(len(seq) > self.number_of_flashes_per_repetition):  #cut down array until there is only 10 values
                        choice = random.choice(allowed_values)
                        if choice in seq:
                            seq.remove(choice)

                    #make sure no repeating element in consecutive order
                    #the consecutive happens when we combine the next array, thus we simply check the tail of seq and head of the array
                    try:
                        if seq[0] == flash_sequence[-1]:
                            seq[0], seq[-6] = seq[-6], seq[0]   #swap the consecutive to some other places, here i choose -6
                    except NameError:
                        flash_sequence = []
                    flash_sequence.extend(seq)

        self.flash_sequence = flash_sequence


    def start(self):
        self.running = 1
        letter = self.word[0]
        image_index = string.ascii_lowercase.index(letter)
        self.highlight_image(image_index)
        self.start_btn.configure(state='disabled')
        self.pause_btn.configure(state='normal')
        self.master.quit

    def pause(self):
        self.running = 0
        self.start_btn_text.set('Resume')
        self.start_btn.configure(state='normal')
        self.pause_btn.configure(state='disabled')


    def start_flashing(self):
        if self.sequence_number == len(self.flash_sequence):  #stop flashing if all generated sequence number runs out
            print('All elements had flashed - run out of juice')
            self.running = 0
            self.sequence_number = 0
            return

        if self.running == 0:
            print('Flashing paused at sequence number ' + str(self.sequence_number))
            return

        element_to_flash = self.flash_sequence[self.sequence_number]
        letter = self.word[self.letter_idx]
        image_index = string.ascii_lowercase.index(letter)

        #pushed markers to LSL stream
        timestamp = local_clock()
        if(element_to_flash == image_index):
            print("Pushed to the LSL: ", "Marker: ", [2], "; Timestamp: ", timestamp, "Seq: ", self.sequence_number, 
                "Target letter - [Letter#]: ",  self.letter_idx, " [Image index]: ", image_index, " [Character]: ", letter, "Flash element: ", element_to_flash)
            self.lsl_output.push_sample(['target', letter, str(self.letter_idx), str(image_index), str(element_to_flash)], timestamp)  #2 for targets
        else:
            #print("Pushed to the LSL: ", "Marker: ", [1], "; Timestamp: ", timestamp)
            self.lsl_output.push_sample(['non-target', letter, str(self.letter_idx), str(image_index), str(element_to_flash)], timestamp)  #1 for non-targets
            # target/nontarget, target letter that participant is trying to type, index of the current letter in the target word, 0-index of the target letter that participant is trying to type, 0-index of the letter being flashed.

        #flashing
        if self.flash_mode == 1:
            self.flash_row_or_col(element_to_flash)
        elif self.flash_mode == 2:
            self.flash_single_element(element_to_flash)


        if(self.letter_idx < len(self.word)):
            if((self.sequence_number + 1) % self.total_repetitions_per_trial == 0):  #every self.repetitions, change letter (0 - 29, 30 - 59, 60 - 89 etc.)
                self.letter_idx += 1
                if(self.letter_idx == len(self.word)):
                    return
                letter = self.word[self.letter_idx]
                image_index = string.ascii_lowercase.index(letter)
                self.master.after(self.break_duration, self.highlight_target, image_index)
            else:
                self.master.after(self.break_duration, self.start_flashing)

        self.sequence_number = self.sequence_number + 1  #change flash position


    def highlight_target(self, image_index):
        self.show_highlight_letter(self.letter_idx)
        self.highlight_image(image_index)

    def change_image(self, label, img):
        label.configure(image=img)
        label.image = img

    def highlight_image(self, element_no):
        self.change_image(self.image_labels[element_no], self.highlight_letter_images[element_no])
        self.master.after(self.delay, self.unhighlight_image, element_no)

    def unhighlight_image(self, element_no):
        self.change_image(self.image_labels[element_no], self.usable_images[element_no])
        self.master.after(self.flash_duration, self.start_flashing)


    def show_highlight_letter(self, pos):

        fontStyle = tkFont.Font(family="Courier", size=40)
        fontStyleBold = tkFont.Font(family="Courier bold", size=40)

        text = Text(root, height=1, font=fontStyle)
        text.tag_configure("bold", font=fontStyleBold)
        text.tag_configure("center", justify='center')

        for i in range(0, len(self.word)):
            if(i != pos):
                text.insert("end", self.word[i])
            else:
                text.insert("end", self.word[i], "bold")

        text.configure(state="disabled", width=10)
        text.tag_add("center", "1.0", "end")

        text.grid(row=self.number_of_rows + 1, column=self.number_of_columns - 4)

    def flash_row_or_col(self, rc_number):
        num_rows = self.number_of_rows
        num_cols = self.number_of_columns

        if rc_number < num_rows:
            for c in range(0, num_cols):  #flash row
                cur_idx = rc_number * num_cols + c
                self.change_image(self.image_labels[cur_idx], self.flash_image)
        else:
            current_column = rc_number - num_rows
            for r in range(0, num_rows):  #flash column
                cur_idx = current_column + r * num_cols
                self.change_image(self.image_labels[cur_idx], self.flash_image)

        self.master.after(self.flash_duration, self.unflash_row_or_col, rc_number)

    def unflash_row_or_col(self, rc_number):
        num_rows = self.number_of_rows
        num_cols = self.number_of_columns
        if rc_number < num_rows:
            for c in range(0, num_cols):   #flash row
                cur_idx = rc_number * num_cols + c
                self.change_image(self.image_labels[cur_idx], self.usable_images[cur_idx])
        else:
            current_column = rc_number - num_rows
            for r in range(0, num_rows):   #flash column
                cur_idx = current_column + r * num_cols
                self.change_image(self.image_labels[cur_idx], self.usable_images[cur_idx])

    def flash_single_element(self, element_no):
        self.change_image(self.image_labels[element_no], self.flash_image)
        self.master.after(self.flash_duration, self.unflash_single_element, element_no)

    def unflash_single_element(self, element_no):
        self.change_image(self.image_labels[element_no], self.usable_images[element_no])


root = Tk()
main_window = P300Window(root)
root.mainloop()