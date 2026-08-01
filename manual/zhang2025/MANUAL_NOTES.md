## A brain-wide map of neural activity during complex behaviour

The IBL loading interface is a bit complicated - but it should be the following steps: 

- Set up the cache with the correct release tag
```python
one.load_cache(tag='Brainwidemap')
```

- Search for the set of sessions
```python
eids, info = one.search(query_type='local', details=True)
```

- Filter by some criterion

```python
required = ['spikes.times.npy', 'spikes.clusters.npy',      # ephys
            '_ibl_trials.table.pqt',                        # task
            '_ibl_wheel.position.npy', '_ibl_wheel.timestamps.npy']

keep = set(one.search(query_type='local', datasets=required))
```

- We also filter out trials outside of a RT range (min = 0.08, max = 2) based on the paper
- We filter out the no reponse trials 


*Behavioral Variables*
- There is a small trap in the IBL choice encoding where -1 is right and +1 is left
- IBL uses a consistent clock, so alignment between datastream is straightfoward
- Two camera both have ME data, but the paper method prefers the left one if it is aviliable

*Neural Varibles*
- Apply quality filter
```python 
good = np.flatnonzero(clusters['label'] >= 1)
keep = np.isin(spikes['clusters'], good)
```