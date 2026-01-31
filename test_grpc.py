"""Test client for gRPC health service."""

import sys
import time
from pathlib import Path

import grpc

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from generated import health_pb2, health_pb2_grpc


def test_health_check(host: str = "localhost", port: int = 50051):
    """Test overall health check endpoint."""
    print(f"\n{'='*60}")
    print("Testing Overall Health Check")
    print(f"{'='*60}")

    try:
        # Create channel
        channel = grpc.insecure_channel(f"{host}:{port}")
        stub = health_pb2_grpc.HealthStub(channel)

        # Create request
        request = health_pb2.Empty()

        # Make RPC call
        print(f"Calling Health.Check() on {host}:{port}...")
        response = stub.Check(request)

        # Display response
        print(f"✓ Status: {response.status}")
        print(f"✓ Version: {response.version}")
        print(f"✓ Timestamp: {response.timestamp} ({time.ctime(response.timestamp)})")

        channel.close()
        return True

    except grpc.RpcError as e:
        print(f"✗ RPC Error: {e.code()}")
        print(f"  Details: {e.details()}")
        return False

    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False


def test_service_health_check(service_name: str, host: str = "localhost", port: int = 50051):
    """Test service-specific health check endpoint."""
    print(f"\n{'='*60}")
    print(f"Testing {service_name.upper()} Service Health Check")
    print(f"{'='*60}")

    try:
        # Create channel
        channel = grpc.insecure_channel(f"{host}:{port}")
        stub = health_pb2_grpc.HealthStub(channel)

        # Create request
        request = health_pb2.ServiceRequest(service_name=service_name)

        # Make RPC call
        print(f"Calling Health.CheckService(service_name='{service_name}')...")
        response = stub.CheckService(request)

        # Display response
        print(f"✓ Status: {response.status}")
        print(f"✓ Database Connected: {response.database_connected}")
        print(f"✓ Message: {response.message}")

        channel.close()
        return True

    except grpc.RpcError as e:
        print(f"✗ RPC Error: {e.code()}")
        print(f"  Details: {e.details()}")
        return False

    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False


def main():
    """Run all gRPC tests."""
    print("\n" + "="*60)
    print("LifeHubAI gRPC Health Service Test Suite")
    print("="*60)

    host = "localhost"
    port = 50051

    # Test 1: Overall health check
    success1 = test_health_check(host, port)

    # Test 2: Code generation service health check
    success2 = test_service_health_check("code_generation", host, port)

    # Test 3: TTS service health check
    success3 = test_service_health_check("tts", host, port)

    # Test 4: Database service health check
    success4 = test_service_health_check("database", host, port)

    # Test 5: Invalid service (should return NOT_FOUND error)
    print(f"\n{'='*60}")
    print("Testing Invalid Service (Error Handling)")
    print(f"{'='*60}")
    print(f"Calling Health.CheckService(service_name='invalid_service')...")
    success5 = not test_service_health_check("invalid_service", host, port)
    if success5:
        print("✓ Error handling works correctly")

    # Summary
    print(f"\n{'='*60}")
    print("Test Summary")
    print(f"{'='*60}")
    tests = [
        ("Overall Health Check", success1),
        ("Code Generation Service", success2),
        ("TTS Service", success3),
        ("Database Service", success4),
        ("Error Handling", success5),
    ]

    for test_name, success in tests:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status}: {test_name}")

    all_passed = all(success for _, success in tests)
    print(f"\n{'='*60}")
    if all_passed:
        print("All tests passed!")
        return 0
    else:
        print("Some tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
