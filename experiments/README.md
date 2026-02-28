# Experiments

Alternative implementations and stress testing tools.

## Files

- **admission_control.py** - Redis-based admission control implementation
- **fixed_booking_system.py** - Queue-based booking system
- **mock_stress_test.py** - Standalone stress test (no backend needed)
- **production_stress_test.py** - Full system stress test
- **stress_test.py** - Basic concurrency test
- **run_stress_tests.sh** - Test runner script
- **verify_no_overbooking.sh** - SQL verification script

## Usage

```bash
# Quick test (no backend)
python3 mock_stress_test.py

# Full system test
python3 production_stress_test.py

# Run all tests
./run_stress_tests.sh
```
