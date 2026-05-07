import numpy as np 


#  Numpy simple functions for practice.
a = np.array([1,2,22,3,4,5,4,4,6,7,8,8,8,99])
# Lists 2D ^ 3D V
b = np.array ([[9,8,6],
			   [3,5,6]])

zeros = np.zeros((3,4)) # Zeros
print("Zeros: \n", zeros)

ones = np.ones((2,3)) # Ones
print("Ones: \n", ones)

empty = np.empty((2,3)) # Garbage values (Empty)
print("empty:\n", empty) 

print("arange:\n")
print(np.arange(2,5))

linspace = np.linspace(1,3,7)
print("linspace:\n",linspace)

arr = np.array([ [[1,2,3], 
				  [4,5,6],
				  [7,8,9]],

				 [[10, 11, 12],
				  [13, 14, 15],
				  [16, 17, 18]]
				  ])
print("Shape:", arr.shape)
print("Dimensions", arr.ndim)
print("Size:", arr.size)
print("Data Type:", arr.dtype)
print("Array:\n", arr)

floats = np.array([1,23,24], dtype=np.float32)
print("Float array:", floats) # Float array, notice how it is dots instead of commas.

integers = floats.astype(np.int16)
print("Converted:", integers) # Integer. Notice how it doesn't have anything in between.

print("First element:", arr[0])
print("Last element", arr[-1])
print("Slice [0][0][1:7]:", arr[0][0][1:7])
print()
print("Slice [0]\n", arr[0])			# Multidimensional Slicing
print("Slice [0][0]\n", arr[0][0])
print("Slice [0][0][0]\n", arr[0][0][0])

matrix = np.array([[1,2,3],  # Coordinates instead of indexing
				   [4,5,6],
				   [7,8,9]])

print("Element at (1,2:)", matrix[1,2])
print("First row:", matrix[0])          

arr = np.array([1,3,4,5,6,7,8])

mask = arr > 3
print("Mask:", mask)

print("Values > 3:", arr[mask])  # Masking (conditional filter)

print("Even values:", arr[arr % 2 == 0])

a = np.array([[1,2,2],		# Arithmatic on numpy lists
			  [3,4,5]])

b = np.array ([[9,8,6],			 
			   [3,5,6]])

print("Add:", a+b)

arr = np.array([[1,2,3],		
	            [4,5,6]])

print("Add 10:\n", arr + 10)

row_add = np.array([100,200,300])
print("Add row:\n", arr + row_add)

arr = np.array([[1,2,3],
			    [4,5,6]])

print("Sum:", arr.sum())		# Statistics
print("Mean:", arr.mean())
print("Std Dev:", arr.std())
print("Min:", arr.min())
print("Max:", arr.max())

uniform = np.random.rand(3,3) # Random distributions
print("Uniform:\n", uniform)

normal = np.random.randn(1000)
print(normal)

print("Normal mean:", normal.mean(), "std;", normal.std())

choices = np.random.choice(['1','2', '3'], size = 20)
print("Random choices:", choices)
