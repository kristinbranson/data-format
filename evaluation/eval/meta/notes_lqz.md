## random notes

Agent are good (sometimes too good) at reading large codebase, understand data structure etc.
- Minor details in processing steps, data filtering, etc IF the details are clearly and explicitly written in the methods/code, the agent is good at finding them

LLM judges are better at details that human may sometime overlook

Randomness:
- Agent will mostly make correct, consistent decision, but it's not 100%, will make random mistakes or inconsisent decisions on REPEATED runs
- Esepcially for open-ended decision like parameters and choices for data preprocessing
- Use float.16, float.32, and float.64 across many runs, sometime casting within the same script for no apperant reason
- One way to reduce this problem is to have code reference for the preprocessing pipeline and parameters aviliable, and try to force the agent to follow the exact procedure.

Defensive coding - AI more willing to make assumptions

Robust code:
- Agent tend to make more assumptions (e.g., based on the variable names)

Code efficiency

LLM judges are not *realible* enough
Tends to be too rigid and literal
Good at catching *mistakes* in code (but also inconsistent, don't flag the same thing across different runs)

LLM judge can't eval open-ended decision well (e.g., when many valid solutions exist)

## Thoughts on showing conclusion
Plot histogram on
    - ratings on different type of decision (data loading vs. preprocessing)
    Agent being good at some type but not other

    - human vs. judge rating distribution, show differences between judges, etc

Show variability of agents across many runs (trial varibility)

Breakdown of the different type of errors 
this will rely more on observational data
(some flow chart / tree diagram)


AI Judge *SNR*: do a classifier evaluation (calculate correct rate), esp combining two judgets
(intuition: AI (combined) usually will not miss a mistakes, but tends to be too literal / rigid in their judgement)

#### summarize the pattern of errors in the agent solution 

## How do we use them? 
- short leash, "supervise" the decision to the agents
- help "guide" the agents' attention towrads things that are likely to go wrong, and implement checks and defensive code
pay extra attention to details in data preprocessing, temporal alignment, and anything in the data that go against "convetion" (the agent will make assumptions)  

- agent is very good at helping the user (scientist) explore the dataset, understand the data structure, and handles the details of reading files, index into the dictionary etc.