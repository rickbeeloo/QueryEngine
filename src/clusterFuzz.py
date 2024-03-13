from tqdm import tqdm
from numba import jit, prange
import numpy as np
import sys 
import rapidfuzz
import time 
import argparse

def _read_file_as_numpy(file, buffer_size):
    python_vector = []
    with open(file, "r") as in_file:
        for line in in_file:
            buffer = np.zeros(buffer_size, dtype=np.uint8)
            encoded = line.strip().encode('utf-8')
            if len(encoded) > buffer_size:
                sys.exit("increase buffer size")
            buffer[:len(encoded)] = np.frombuffer(encoded, dtype=np.uint8)
            python_vector.append(buffer)
    return np.array(python_vector)

@jit(nopython=True, parallel=True)
def _calculate_coverage(queries, refs):
    # Initialize an empty array to store coverage values
    coverage = np.zeros((len(refs), len(queries)))
    # Iterate over references
    for i in prange(len(refs)):
        # Convert reference to a set for faster lookup
        r_set = set(refs[i])
        # Iterate over queries
        for j in range(len(queries)):
            # Count matches between reference and query
            c = 0
            for number in queries[j]:
                if number != 0 and number in r_set:
                    c += 1
            coverage[i, j] = c / len(queries[j])
    return coverage # Columns = refs, queries = rows

@jit(nopython=True, parallel=True)
def _calculate_lengths(query_lens, ref_lens):
    lens = np.zeros((len(ref_lens), len(query_lens)))
    for i in prange(len(ref_lens)):
        for j in range(len(query_lens)):
            lens[i, j] = query_lens[j] - ref_lens[i]
    return lens
            
@jit(nopython=True, parallel=True)
def _get_length_array(arr):
    # Note we filled the buffer with zeros so we just have to 
    # count the non zero bytes
    len_arr = np.zeros(len(arr), dtype=np.int16)
    for i in prange(len(arr)):
        len_arr[i] = np.count_nonzero(arr[i])
    return len_arr 
        
def _topK_pass(cov_matrix, len_matrix, top_k):
    _, n_cols = cov_matrix.shape
    top_indices_arr = np.zeros((top_k, n_cols), dtype=np.int64)
    for j in range(n_cols):
        cov_column = cov_matrix[:, j]
        len_column = len_matrix[:, j]
        sorted_indices = np.lexsort((len_column, cov_column)) # First sort on Cov then len
        cut = len(sorted_indices) if len(sorted_indices) < top_k else top_k
        top_indices_arr[:cut, j] = sorted_indices[-cut:][::-1]
    return top_indices_arr

def _as_string(np_uint8):
    nonzero_index = np.nonzero(np_uint8)[0]
    return np_uint8[nonzero_index].tobytes().decode()

def _rapid_fuzz_pass(topK_indices, queries, refs, fuzz_socre):
    n_rows, n_cols = topK_indices.shape
    best_matches = np.empty(n_cols, dtype=object)
    total, mapped = 0, 0
    for i in tqdm(range(n_cols)):
        # Don't like converting back to strings again... but lets rely on RapidFuzz for now
        q = _as_string(queries[i])
        total +=1
        r = [_as_string(r) for r in refs[topK_indices[: , i]]]
        # Note we now again switch the queries and refs
        score_matrix = rapidfuzz.process.cdist(r, [q],
                        processor=str.lower, 
                        scorer=rapidfuzz.fuzz.partial_ratio,
                        dtype=np.uint8,  
                        workers=-1,  # All cores
                        score_cutoff=fuzz_socre,
                        )
        score_vector = score_matrix[:,0]
        if np.all(score_vector==0):
            best_matches[i] = "NA"
        else:
            max_value = np.argmax(score_vector)
            best_matches[i] = r[max_value]
            mapped +=1
    r = round(mapped / total * 100,2)
    print(f"\tMap ratio: {r}% ({mapped} / {total})")
    return best_matches

def _dump_to_file(queries, matches, output_file):
    with open(output_file, "w") as out:
        out.write(f"query\tmatch\n")
        for q, m in zip(queries, matches):
            query_string = _as_string(q)
            out.write(f"{query_string}\t{m}\n")

def run(query_file, ref_file, topK, fuzz_socre, buffer_size, output_file):
    s = time.time()
    print("[STEP1] Reading strings as uint8 vectors...")
    print("\tQueries...")
    query_vectors = _read_file_as_numpy(query_file, buffer_size)
    print(f"\t#Queries: {len(query_vectors)}")
    print("\tRefs...")
    ref_vectors = _read_file_as_numpy(ref_file, buffer_size)
    print(f"\t#Refs: {len(ref_vectors)}")
    print("[STEP2] Calculating query and ref lengths...")
    print("\tQueries...")
    query_lens = _get_length_array(query_vectors)
    print("\tRefs...")
    ref_lens = _get_length_array(ref_vectors)
    print("[STEP3] Building coverage matrix..")
    cov_matrix = _calculate_coverage(query_vectors, ref_vectors)
    print("\tMatrix shape: ", cov_matrix.shape)
    print("[STEP4] Building Length matrix...")
    len_matrix = _calculate_lengths(query_lens, ref_lens)
    print("[STEP5] Running topK selection...")
    top_results = _topK_pass(cov_matrix, len_matrix, topK)
    print(top_results)
    print("[STEP6] Running RapidFuzz..")
    best_matches = _rapid_fuzz_pass(top_results, query_vectors, ref_vectors, fuzz_socre)
    print("[STEP6] Writing output file...")
    _dump_to_file(query_vectors, best_matches, output_file)
    took = round( (time.time() - s) / 60, 2)
    print(f"DONE! Took: {took} minutes")
    
def main():
    parser = argparse.ArgumentParser(description='Process query and reference files.')
    parser.add_argument('-q', '--query', type=str, required=True, help='Path to the query file')
    parser.add_argument('-r', '--reference', type=str, required=True, help='Path to the reference file')
    parser.add_argument('-o', '--OutputFile', type=str,  required=True, help='Mapping output file')
    parser.add_argument('-n', '--topN', type=int, default=10, help='Number of top results to retrieve (default: 10)')
    parser.add_argument('-s', '--scoreCutOff', type=int, default=90, help='Minimum fuzz score threshold (default: 0)')
    parser.add_argument('-b', '--bufferSize', type=int, default=500, help='Uint8 buffer size')
    
    args = parser.parse_args()

    # Accessing the arguments
    query_file = args.query
    reference_file = args.reference
    topN = args.topN
    scoreCutOff = args.scoreCutOff
    buffer_size = args.bufferSize
    output_file = args.OutputFile
    
    # Run code
    run(query_file, reference_file, topN, scoreCutOff, buffer_size, output_file)

if __name__ == "__main__":
    main()
    

