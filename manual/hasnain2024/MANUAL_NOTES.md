## Separating cognitive and motor processes in the behaving mouse

### Step 2: Dataset Exploration

- Use the session list provided by the authors, since there some sessions that are exlcluded from the analysis
- Load the data from the Ephys_behavior and RandomizedDelay_Ephys_Behavior

## Behavioral variables
- Outcome can be {incorrect = 0, correct = 1, and no reponse}. Can choose to filter out the no reponse trial, or record them as a seperate category outcome.
- Filter out the early lick trials and stimulation trials, following the steps in the paper.

*Camera*
- We use a 5 ms temporal resolution/binning, consistent with the paper 
- The video does not run on the behavior clock, so the offset between the two has to be found first
- Trial start is marked by a bitcode pulse recorded in both streams. The offset is where that pulse sits in the recording file (sglx.bitcode.bitstart / sglx.fs) minus where it sits on the behavior clock (bp.ev.bitStart). Take the mode of each, so there is one offset per session
- Time from go cue for the camera is then frameTimes - offset - goCue of that trial

*Velocity computation*
- Both the tounge and paw has two independent view of tracking data (x, y)
- We compute a guassian smoothing over the tracked postion, and compute velocity independently in each camera view
- For *tongue velcocity*, we normalize the velocity by the 90th percentile; and average the two camera stream, before computing the discretization threshold
- For *paw velocity*, we will only use top paw since it looks much more reliable.

- Motion energy is the simply - align and extra, no additional processing.
- The files use a couple of different layout/format that the loader needs to deal with properly

## Neural data
- Apply quality control filter based on the string comments
- Already aligned to the behavioral time
- Binned spike rate + Gaussian filter
