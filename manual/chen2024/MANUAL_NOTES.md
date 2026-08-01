## Brain-wide neural activity underlying memory-guided movement

### Step 2: Dataset Exploration

One session has to be dropped due to all units being "NaN".
Also filter out 
- the "free-water" trials
- trials where recording hasn't started

*Behavioral Variables*
- Each file correspond to one session from one subject in NWB format
- Each trial is associted with a go time, but potentially multiple sample and delay onset due to uninstructed licking
- To define the time axis, we find the go cue, go backwards to find the last sample onset time
- Choice needs to be defined from instruction x outcome variable; There is also a third category for choice which is when outcome == 'ignore' (we use an additional category == 2)
- Tongue is invisible most of the time during the trial (tracking conf is either 0 or 1, and it's 0 most of the time). We will only treat the values for conf == 1 as valid
- The final tongue y position category label is generated with an "3" label for "not visible".

*Neural Data*
- Use 'classification' = 'good' as defined in the methods paper
- Spike time recorded in aligned temporal axis, so simply compute spike counts -> rate within each binned window
