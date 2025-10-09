import numpy as np


def test_numpy():
    a = np.array([1, 2, 3])
    b = np.array([4, 5, 6])
    c = a + b
    assert np.array_equal(c, np.array([5, 7, 9]))
    
if __name__ == "__main__":
    test_numpy()
    print("Numpy test passed!")