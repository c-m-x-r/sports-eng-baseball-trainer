"""
Unit tests for backend sensor processing
Run with: python test_backend.py
"""
import json
import time
from datetime import datetime
import sys

def generate_test_payload(num_samples=100):
    """Generate realistic sensor data for testing"""
    payload = []
    base_time = time.time_ns()

    for i in range(num_samples):
        timestamp = base_time + (i * 10_000_000)  # 10ms intervals

        # Simulate accelerometer
        payload.append({
            "time": timestamp,
            "name": "accelerometer",
            "values": {"x": 0.1 * i, "y": 0.2 * i, "z": 9.8 + 0.1 * i}
        })

        # Simulate gyroscope
        payload.append({
            "time": timestamp,
            "name": "gyroscope",
            "values": {"x": 0.5 * i, "y": 0.1 * i, "z": 0.05 * i}
        })

        # Simulate uncalibrated accelerometer
        payload.append({
            "time": timestamp,
            "name": "accelerometeruncalibrated",
            "values": {"x": 0.12 * i, "y": 0.22 * i, "z": 9.9 + 0.12 * i}
        })

    return payload


def test_processing_speed():
    """Test how fast we can process sensor data"""
    from backend import process_sensor_data

    print("=" * 60)
    print("PROCESSING SPEED TEST")
    print("=" * 60)

    # Test with different payload sizes
    for size in [10, 50, 100, 500]:
        payload = generate_test_payload(size)

        start = time.perf_counter()
        process_sensor_data(payload)
        elapsed = (time.perf_counter() - start) * 1000  # Convert to ms

        print(f"Payload size: {size * 3:4d} messages | Processing time: {elapsed:6.2f} ms")


def test_analysis_accuracy():
    """Test that analysis produces correct results"""
    from backend import analyze_recording, calculate_magnitude

    print("\n" + "=" * 60)
    print("ANALYSIS ACCURACY TEST")
    print("=" * 60)

    # Create test recording with known peaks
    test_rec = {
        'time': [datetime.fromtimestamp(1000000000 + i) for i in range(10)],
        'gyro_x': [0, 1, 2, 5, 3, 1, 0, -1, -2, -1],  # Peak at index 3
        'gyro_y': [0] * 10,
        'gyro_z': [0] * 10,
        'accel_x': [0, 1, 2, 3, 4, 3, 2, 1, 0, 0],  # Peak at index 4
        'accel_y': [0] * 10,
        'accel_z': [9.8] * 10,
        'accel_uncal_x': [0, 1, 2, 3, 5, 3, 2, 1, 0, 0],  # Peak at index 4
        'accel_uncal_y': [0] * 10,
        'accel_uncal_z': [10.0] * 10
    }

    analyze_recording(test_rec)
    metrics = test_rec['metrics']

    # Verify results
    assert metrics['peak_gyro_x_value'] == 5, f"Expected peak gyro 5, got {metrics['peak_gyro_x_value']}"
    assert metrics['gyro_direction'] == "RIGHT", f"Expected RIGHT, got {metrics['gyro_direction']}"
    print("✓ Peak gyro detection: PASSED")

    # Test magnitude calculation
    mag = calculate_magnitude([3], [4], [0])
    assert abs(mag[0] - 5.0) < 0.01, f"Expected magnitude 5.0, got {mag[0]}"
    print("✓ Magnitude calculation: PASSED")

    print("\nAll accuracy tests PASSED!")


def benchmark_comparison(func1, func2, name1, name2, *args):
    """Compare performance of two functions"""
    print(f"\n{'=' * 60}")
    print(f"BENCHMARK: {name1} vs {name2}")
    print(f"{'=' * 60}")

    # Warmup
    func1(*args)
    func2(*args)

    # Benchmark func1
    iterations = 100
    start = time.perf_counter()
    for _ in range(iterations):
        func1(*args)
    time1 = (time.perf_counter() - start) / iterations * 1000

    # Benchmark func2
    start = time.perf_counter()
    for _ in range(iterations):
        func2(*args)
    time2 = (time.perf_counter() - start) / iterations * 1000

    speedup = time1 / time2
    print(f"{name1}: {time1:.3f} ms/call")
    print(f"{name2}: {time2:.3f} ms/call")
    print(f"Speedup: {speedup:.2f}x {'faster' if speedup > 1 else 'slower'}")

    return speedup


def test_numpy_speedup():
    """Test speedup from using numpy vs pure Python"""
    from backend import analyze_recording, calculate_magnitude
    import math

    print("\n" + "=" * 60)
    print("NUMPY SPEEDUP TEST")
    print("=" * 60)

    # Create large test recording
    n = 1000
    test_rec = {
        'time': [datetime.fromtimestamp(1000000000 + i * 0.01) for i in range(n)],
        'gyro_x': list(range(n)),
        'gyro_y': [0] * n,
        'gyro_z': [0] * n,
        'accel_x': list(range(n)),
        'accel_y': list(range(n)),
        'accel_z': [9.8] * n,
        'accel_uncal_x': list(range(n)),
        'accel_uncal_y': list(range(n)),
        'accel_uncal_z': [10.0] * n
    }

    # Test numpy magnitude calculation
    iterations = 1000
    x, y, z = test_rec['accel_x'], test_rec['accel_y'], test_rec['accel_z']

    # Numpy version
    start = time.perf_counter()
    for _ in range(iterations):
        result = calculate_magnitude(x, y, z)
    numpy_time = (time.perf_counter() - start) / iterations * 1000

    # Pure Python version (for comparison)
    def calculate_magnitude_python(x_arr, y_arr, z_arr):
        return [math.sqrt(x_arr[i]**2 + y_arr[i]**2 + z_arr[i]**2) for i in range(len(x_arr))]

    start = time.perf_counter()
    for _ in range(iterations):
        result = calculate_magnitude_python(x, y, z)
    python_time = (time.perf_counter() - start) / iterations * 1000

    print(f"Magnitude calculation ({n} points, {iterations} iterations):")
    print(f"  Python loops: {python_time:.3f} ms/call")
    print(f"  Numpy:        {numpy_time:.3f} ms/call")
    print(f"  Speedup:      {python_time/numpy_time:.1f}x faster")

    # Test analyze_recording
    print(f"\nAnalysis ({n} samples):")
    start = time.perf_counter()
    analyze_recording(test_rec)
    analysis_time = (time.perf_counter() - start) * 1000
    print(f"  Analysis time: {analysis_time:.3f} ms")


if __name__ == "__main__":
    print("\n🧪 RUNNING BACKEND TESTS\n")

    try:
        test_processing_speed()
        test_analysis_accuracy()
        test_numpy_speedup()
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60 + "\n")
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
