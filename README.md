# BCI @ AIT (modified)

## About

Hardware:
- any sensor connected to lsl

Software:
- Python [tested on 3.11.5]

Things need to take precaution:
- To get a clean signal, it is important to **stay at a location free of electric artifacts**.  When you look at your brain signals using LSL Viewer, it should be around low frequency, around -10 or less.  If it is more, try make sure your feet/hand is touching the ground and see whether the volts changes.  Also, if your bluetooth receiver is near the power outlet, it can also increase the frequency significantly.  Try move to different locations that are free of power influences.  Last, even your feet/hand is grounded, make sure no electricity is on the ground!, e.g., leaving some plugs on the ground

## How to run

1. **SSVEP (Offline)**
   0. Change monitor frequency to a value closest to 60.0 Hz (On Windows, search "View advanced display info" on the start menu and choose a value under "Choose a refresh rate"). Try to note this value down
   1. Get the recording device up and running on LSL (e.g. LiveAmp LSL Connector, OpenBCI, custom apps, etc.)
   2. Start LabRecorder
   3. Run <code>python SSVEP/2-experiment/offline_experiment.py</code>. Force-quit once using the Escape key to let LabRecorder find SSVEP_stream.
   4. Update stream list on LabRecorder and find all required streams (SSVEP_stream and whatever stream from the recording device)
   5. Start recording
   6. Restart the experiment by running <code>python SSVEP/2-experiment/offline_experiment.py</code>
2. **P300 (Offline)**
   1. Get the recording device up and running on LSL (e.g. LiveAmp LSL Connector, OpenBCI, custom apps, etc.)
   2. Start LabRecorder
   3. Run <code>python P300/2-experiment/offline_experiment.py</code> and maximize the window.
   4. Update stream list on LabRecorder and find all required streams (SSVEP_stream and whatever stream from the recording device)
   5. Start recording
3. **SSVEP/P300 (Online)** (TBD)
4. **MI** (TBD)
5. **Real-time Emotion Recognition** (TBD)
6. **Past-recollection** (TBD)
