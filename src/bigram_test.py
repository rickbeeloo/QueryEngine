import numpy as np

def generate_bigrams(uint8_array):
    # Find the index of the last non-zero element
    last_non_zero_index = np.flatnonzero(uint8_array)[-1]

    # Extract the portion of the array without trailing zero uint8s
    trimmed_array = uint8_array[:last_non_zero_index + 1]

    n = len(trimmed_array)
    # Preallocate bigram array
    bigrams = np.empty((n - 1, 2), dtype=np.uint8)
    
    # Iterate over the trimmed array with a sliding window
    for i in range(n - 1):
        bigrams[i] = trimmed_array[i:i+2]
    
    return bigrams

# Example uint8 array with trailing zero uint8s
uint8_array = np.array([1, 2, 3, 4, 5, 0, 0, 0], dtype=np.uint8)

# Generate bigrams
result = generate_bigrams(uint8_array)
print(result)