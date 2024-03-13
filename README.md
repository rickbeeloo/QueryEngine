  

# HeuristicFuzz

Lets say you have a query set of terms, `q` and a reference database `r`. You want to associate all in `q` with `r` but lets say `q` is of low quality having for example incorrect names, concatenations etc.

  

<h2> The heuristic approach </h2>

We could fuzzy search every term in `q` in `r` but having partial or bad matches does not mean a bad mapping, it might simply be a bad formatted query. For example lets say we have a query like "A yellow banana from the store" and want to match it to a taxonomy database having "banana". A fuzzy search will say "A yellow banana from the store" is only a `~6/20` match with "banana". We can solve this using a partial ratio match, this would say "A yellow _banana_ from the store" is is `100/100` match with "banana". However, partial ratio mapping will be infeasibly slow for big datasets.
Since partial mapping is too slow, and length is relevant we can come up with a heuristic. We first simply count the number of shared letters between all `r x q` and divide this by the length of `q`. Then we get an estimation of "coverage', lets call it `cov_matrix`. Just coverage is not enough. For example, "yellow banana" and "banana" are both 100% coverage but differ by their match length. To account for that we also compare the length of `r x q`, calling it `l_matrix`. The best potential matches for our fuzz later are then those having the highest coverage in `cov_matrix` followed by closest length in `l_matrix`. For example, if we have query = `test` and references `[test1, test123]` both will have the same coverage (`test`) but `test1` will have a closer length match. So we sort on coverage and then length and select the `topK` matches, by default top 20. Now, for each query, we have a `topK` possible matches - drastically reducing the search space. To then select the best match for our query we do a partial fuzz of all `topK` against our query. If multiple matches have the same score we select the longest one.

 <h2> Parameters explained </h2>
 The parameters `-q, -r, and -o` are self-explanatory and are the query, reference and output file. The other three parameters are `-n, -s, -b`:
 

 - `-n`, `topN`, The number of matches to keep from the heuristic search
 - `-s`, `scoreCutOff`, the partial ratio score, see [here](https://github.com/rapidfuzz/RapidFuzz?tab=readme-ov-file#partial-ratio)
 - `-b`, `bufferSize`, the buffer to use to convert strings to `uint8` vectors. This should be at least the longest string size in the query and reference file. This will simply crash if too short, then just increase it.
 
 <h2> An example </h2>
 We have this query file (`example\test_query.txt`):

    test 
    a yellow banana from the store
    vanilla
    peanutbutter
    
and this reference file (`example\test_refs.txt`)

    test1
    test123
    estt
    testing
    tester
    vanilla 
    banana
    yellow banna
We can then run `python heurFuzz.py -q example/test_query.txt -r example/test_refs.txt -n 5 -o example/output.txt -s 90` 

(or use the `.exe` file)


<h2> Some speedups </h2>

For fuzzing I use [`rapidFuzz`](https://github.com/rapidfuzz/RapidFuzz) which is optimized already. For the heuristic approach we convert all strings to `uint8` numpy vectors which we can then readily process, especially accelerated using [Numba](https://github.com/numba/numba). Quite some improvements left, like converting the `uint8` vectors back to strings for RapidFuzz is a bit messy. 

